from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.roles import ADMIN, PRIVILEGED_ROLES, ROLES
from app.core.security import get_current_user, get_optional_user, require_roles
from app.database.connection import get_db
from app.models.email_otp import EmailOTP
from app.models.auth_token import AuthToken
from app.models.user import User
from app.schemas.auth import (
    CurrentUserResponse,
    EmailLinkConfirmRequest,
    EmailLinkRequest,
    EmailRegisterRequest,
    LoginResponse,
    GoogleLoginRequest,
    GoogleLoginResponse,
    GoogleLinkRequest,
    GoogleRegisterRequest,
    GoogleVerifyRequest,
    GoogleVerifyResponse,
    PasswordResetRequest,
    PasswordLinkResetRequest,
    SendOTPRequest,
    TwoFactorSettingsRequest,
    TwoFactorVerifyRequest,
    TokenResponse,
    VerifyOTPRequest,
    VerifyOTPResponse,
)
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.services.email_service import email_service
from app.services.google_auth_service import GoogleAuthError, google_auth_service
from app.services.notification_service import create_pending_approval_notification

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_otp(email: str, otp: str) -> str:
    combined = f"{email.lower().strip()}:{otp.strip()}:{settings.jwt_secret}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def _create_ephemeral_token(data: dict, expires_minutes: int = 15) -> str:
    payload = data.copy()
    payload["exp"] = _utc_now() + timedelta(minutes=expires_minutes)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _decode_ephemeral_token(token: str, expected_purpose: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("purpose") != expected_purpose:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token purpose",
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired or is invalid",
        )


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _issue_auth_link(email: str, purpose: str, db: Session) -> bool:
    now = _utc_now()
    recent = (
        db.query(AuthToken)
        .filter(
            AuthToken.email == email,
            AuthToken.purpose == purpose,
            AuthToken.created_at >= now - timedelta(seconds=settings.otp_cooldown_seconds),
            AuthToken.used_at.is_(None),
        )
        .first()
    )
    if recent:
        return True

    token = secrets.token_urlsafe(32)
    db.query(AuthToken).filter(
        AuthToken.email == email,
        AuthToken.purpose == purpose,
        AuthToken.used_at.is_(None),
    ).update({"used_at": now})
    db.add(
        AuthToken(
            email=email,
            purpose=purpose,
            token_hash=_token_digest(token),
            expires_at=now + timedelta(minutes=settings.auth_link_ttl_minutes),
        )
    )
    db.commit()
    delivered = email_service.send_auth_link_email(email, token, purpose)
    if not delivered:
        db.query(AuthToken).filter(AuthToken.token_hash == _token_digest(token)).update(
            {"used_at": _utc_now()}
        )
        db.commit()
    return delivered


def _consume_auth_link(token: str, purpose: str, db: Session) -> AuthToken:
    now = _utc_now()
    record = (
        db.query(AuthToken)
        .filter(
            AuthToken.token_hash == _token_digest(token),
            AuthToken.purpose == purpose,
            AuthToken.used_at.is_(None),
            AuthToken.expires_at > now,
        )
        .with_for_update()
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This link has expired or is invalid. Request a new one.",
        )
    record.used_at = now
    db.commit()
    return record


def _send_otp_code(email: str, purpose: str, db: Session) -> None:
    now = _utc_now()
    recent = (
        db.query(EmailOTP)
        .filter(
            EmailOTP.email == email,
            EmailOTP.purpose == purpose,
            EmailOTP.created_at >= now - timedelta(seconds=settings.otp_cooldown_seconds),
        )
        .first()
    )
    if recent:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Please wait before requesting another verification code.",
        )
    count = (
        db.query(EmailOTP)
        .filter(
            EmailOTP.email == email,
            EmailOTP.purpose == purpose,
            EmailOTP.created_at >= now - timedelta(hours=1),
        )
        .count()
    )
    if count >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification attempts. Please try again later.",
        )
    db.query(EmailOTP).filter(
        EmailOTP.email == email,
        EmailOTP.purpose == purpose,
        EmailOTP.is_used.is_(False),
    ).update({"is_used": True})

    code = f"{secrets.randbelow(900000) + 100000}"
    record = EmailOTP(
        email=email,
        otp_hash=_hash_otp(email, code),
        purpose=purpose,
        attempts=0,
        is_used=False,
        expires_at=now + timedelta(minutes=settings.otp_ttl_minutes),
    )
    db.add(record)
    db.commit()
    if not email_service.send_otp_email(email, code, purpose):
        record.is_used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to deliver verification email. Please try again later.",
        )


# ============================================================================ #
# OTP Verification Endpoints                                                   #
# ============================================================================ #

@router.post("/email-verification/send")
def send_email_verification_link(
    request: EmailLinkRequest,
    db: Session = Depends(get_db),
):
    if not email_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Configure Gmail SMTP to send verification links.",
        )
    email = request.email.lower().strip()
    if not db.query(User).filter(User.email == email).first():
        if not _issue_auth_link(email, "email_verification", db):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Email delivery is unavailable. Please try again later.",
            )
    return {
        "success": True,
        "message": "If this address can be registered, a verification link has been sent.",
    }


@router.post("/email-verification/confirm")
def confirm_email_verification(
    request: EmailLinkConfirmRequest,
    db: Session = Depends(get_db),
):
    record = _consume_auth_link(request.token, "email_verification", db)
    if db.query(User).filter(User.email == record.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )
    return {
        "success": True,
        "email": record.email,
        "verification_token": _create_ephemeral_token(
            {"sub": record.email, "purpose": "email_verified"},
            expires_minutes=settings.auth_link_ttl_minutes,
        ),
    }


@router.post("/forgot-password")
def forgot_password(request: EmailLinkRequest, db: Session = Depends(get_db)):
    if not email_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Configure Gmail SMTP to send password reset links.",
        )
    email = request.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if user and not _issue_auth_link(email, "password_reset", db):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email delivery is unavailable. Please try again later.",
        )
    return {
        "success": True,
        "message": "If an account exists for this address, a password reset link has been sent.",
    }


@router.post("/reset-password")
def reset_password_with_link(
    data: PasswordLinkResetRequest,
    db: Session = Depends(get_db),
):
    if data.new_password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Passwords do not match.",
        )
    record = _consume_auth_link(data.token, "password_reset", db)
    user = db.query(User).filter(User.email == record.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This link has expired or is invalid. Request a new one.",
        )
    user.password_hash = hash_password(data.new_password)
    db.query(EmailOTP).filter(
        EmailOTP.email == user.email,
        EmailOTP.purpose == "password_reset",
        EmailOTP.is_used.is_(False),
    ).update({"is_used": True})
    db.commit()
    return {"success": True, "message": "Password reset successfully. You can now sign in."}


@router.post("/otp/send")
def send_otp(request: SendOTPRequest, db: Session = Depends(get_db)):
    email = request.email.lower().strip()
    purpose = request.purpose.strip().lower()

    if purpose not in ("registration", "password_reset"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP purpose. Must be 'registration' or 'password_reset'",
        )

    # For registration, verify email is not already taken
    existing_user = db.query(User).filter(User.email == email).first()
    if purpose == "registration" and existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists. Please sign in.",
        )

    # For password reset, email must belong to an existing user
    if purpose == "password_reset" and not existing_user:
        # Return generic success to avoid email enumeration
        return {
            "success": True,
            "message": "If an account exists with this email, a verification code has been sent.",
        }

    now = _utc_now()

    # Rate limiting: Cooldown between requests
    recent_otp = (
        db.query(EmailOTP)
        .filter(
            EmailOTP.email == email,
            EmailOTP.purpose == purpose,
            EmailOTP.created_at >= now - timedelta(seconds=settings.otp_cooldown_seconds),
        )
        .first()
    )
    if recent_otp:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Please wait {settings.otp_cooldown_seconds} seconds before "
                "requesting another verification code."
            ),
        )

    # Rate limiting: Maximum 5 requests per hour
    hourly_count = (
        db.query(EmailOTP)
        .filter(
            EmailOTP.email == email,
            EmailOTP.created_at >= now - timedelta(hours=1),
        )
        .count()
    )
    if hourly_count >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification attempts. Please try again later.",
        )

    # Invalidate previous unused OTPs for this email and purpose
    db.query(EmailOTP).filter(
        EmailOTP.email == email,
        EmailOTP.purpose == purpose,
        EmailOTP.is_used.is_(False),
    ).update({"is_used": True})

    # Generate 6-digit cryptographic OTP
    otp_code = f"{secrets.randbelow(900000) + 100000}"
    otp_hash = _hash_otp(email, otp_code)
    expires_at = now + timedelta(minutes=settings.otp_ttl_minutes)

    otp_record = EmailOTP(
        email=email,
        otp_hash=otp_hash,
        purpose=purpose,
        attempts=0,
        is_used=False,
        expires_at=expires_at,
    )
    db.add(otp_record)
    db.commit()

    # Send real email via SMTP
    delivery_ok = email_service.send_otp_email(
        recipient_email=email,
        otp=otp_code,
        purpose=purpose,
    )
    if not delivery_ok:
        otp_record.is_used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to deliver verification email. Please try again later.",
        )

    return {
        "success": True,
        "message": "Verification code has been sent to your email address.",
    }


@router.post("/otp/verify", response_model=VerifyOTPResponse)
def verify_otp(request: VerifyOTPRequest, db: Session = Depends(get_db)):
    email = request.email.lower().strip()
    otp_code = request.otp.strip()
    purpose = request.purpose.strip().lower()
    if purpose != "registration":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP purpose. Only registration verification is supported here.",
        )
    now = _utc_now()

    record = (
        db.query(EmailOTP)
        .filter(
            EmailOTP.email == email,
            EmailOTP.purpose == purpose,
            EmailOTP.is_used.is_(False),
            EmailOTP.expires_at > now,
        )
        .order_by(EmailOTP.created_at.desc())
        .first()
    )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired or is invalid. Please request a new code.",
        )

    if record.attempts >= settings.otp_max_attempts:
        record.is_used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed verification attempts. Please request a new code.",
        )

    record.attempts += 1
    expected_hash = _hash_otp(email, otp_code)

    if not hmac.compare_digest(record.otp_hash, expected_hash):
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code. Please check the code and try again.",
        )

    # Valid OTP: Mark as used
    record.is_used = True
    db.commit()

    # Create signed verification token
    verification_token = _create_ephemeral_token(
        {"sub": email, "purpose": "email_verified"},
        expires_minutes=15,
    )

    return VerifyOTPResponse(
        success=True,
        verification_token=verification_token,
        message="Email address verified successfully.",
    )


# ============================================================================ #
# Option 1: Email Registration                                                 #
# ============================================================================ #

@router.post("/register/email", status_code=status.HTTP_201_CREATED)
def register_email(
    data: EmailRegisterRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    # Verify token
    payload = _decode_ephemeral_token(data.verification_token, "email_verified")
    verified_email = payload.get("sub", "").lower().strip()

    if data.password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Passwords do not match.",
        )

    requested_role = data.requested_role.strip().upper()
    if requested_role not in ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="role must be one of: " + ", ".join(ROLES),
        )

    # Public self-registration cannot request privileged roles (ADMIN, REGULATOR).
    if requested_role in PRIVILEGED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Public registration cannot request privileged roles (ADMIN, REGULATOR). "
                "Please select an operational supply-chain role."
            ),
        )

    # Uniqueness checks
    if db.query(User).filter(User.email == verified_email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    clean_username = data.username.strip()
    if db.query(User).filter(User.username == clean_username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken. Please choose another username.",
        )

    user = User(
        username=clean_username,
        email=verified_email,
        full_name=data.full_name.strip() if data.full_name else None,
        password_hash=hash_password(data.password),
        role=requested_role,
        organization=data.organization.strip() if data.organization else None,
        status="PENDING",
        auth_provider="local",
        is_active=True,
    )

    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists.",
        )
    db.refresh(user)

    # Persist notification for administrator approval
    create_pending_approval_notification(db, user)

    return {
        "success": True,
        "message": (
            "Registration submitted successfully. Your account is pending "
            "administrator approval. You will be able to sign in once approved."
        ),
        "user_id": str(user.id),
        "status": user.status,
    }


# ============================================================================ #
# Option 2: Google Registration                                                #
# ============================================================================ #

@router.post("/google/login", response_model=GoogleLoginResponse)
def login_with_google(
    data: GoogleLoginRequest,
    db: Session = Depends(get_db),
):
    try:
        identity = google_auth_service.verify_id_token(data.id_token)
    except GoogleAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    email = identity["email"].lower().strip()
    google_id = identity["google_id"]
    name = identity["name"]

    # Google identities are matched only by Google's verified subject.
    user = db.query(User).filter(User.google_id == google_id).first()
    if not user:
        existing_email_user = db.query(User).filter(User.email == email).first()
        if existing_email_user:
            if existing_email_user.auth_provider == "local" or not existing_email_user.google_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "An account with this email address already exists using email and password. "
                        "Please sign in using your email and password."
                    ),
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "This email already belongs to an account. Sign in with that "
                        "account's existing authentication method."
                    ),
                )

    # 3. If user exists, enforce status guards and issue JWT
    if user:
        if user.status == "PENDING":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Your account is pending administrator approval. "
                    "You will receive access once approved by an administrator."
                ),
            )
        if user.status == "REJECTED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account registration request was rejected by an administrator.",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive.",
            )

        if user.two_factor_enabled:
            _send_otp_code(user.email, "login_2fa", db)
            return GoogleLoginResponse(
                success=True,
                two_factor_required=True,
                existing_user=True,
                status=user.status,
                email=user.email,
                name=user.full_name or user.username,
                message="A verification code has been sent to your email.",
            )

        access_token = create_access_token(
            user_id=str(user.id),
            role=user.role,
        )
        return GoogleLoginResponse(
            success=True,
            access_token=access_token,
            token_type="bearer",
            existing_user=True,
            status=user.status,
            email=user.email,
            name=user.full_name or user.username,
            role=user.role,
            user_id=str(user.id),
            message="Sign-in successful.",
        )

    # 4. User does not exist: issue registration token for role selection
    reg_token = _create_ephemeral_token(
        {
            "sub": google_id,
            "email": email,
            "name": name,
            "purpose": "google_verified",
        },
        expires_minutes=15,
    )
    return GoogleLoginResponse(
        success=False,
        access_token=None,
        token_type="bearer",
        existing_user=False,
        status="UNREGISTERED",
        email=email,
        name=name,
        registration_token=reg_token,
        message="No account found with this Google identity. Please complete registration to choose your supply-chain role.",
    )

@router.post("/google/verify", response_model=GoogleVerifyResponse)
def verify_google_identity(
    data: GoogleVerifyRequest,
    db: Session = Depends(get_db),
):
    try:
        identity = google_auth_service.verify_id_token(data.id_token)
    except GoogleAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    email = identity["email"]
    google_id = identity["google_id"]
    name = identity["name"]

    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == email) | (User.google_id == google_id)
    ).first()

    if existing_user:
        return GoogleVerifyResponse(
            success=True,
            email=existing_user.email,
            name=existing_user.full_name or existing_user.username,
            registration_token="",
            existing_user=True,
            status=existing_user.status,
            auth_provider=existing_user.auth_provider,
        )

    # New user: issue registration token
    registration_token = _create_ephemeral_token(
        {
            "sub": google_id,
            "email": email,
            "name": name,
            "purpose": "google_verified",
        },
        expires_minutes=15,
    )

    return GoogleVerifyResponse(
        success=True,
        email=email,
        name=name,
        registration_token=registration_token,
        existing_user=False,
    )


@router.post("/register/google", status_code=status.HTTP_201_CREATED)
def register_google(
    data: GoogleRegisterRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    payload = _decode_ephemeral_token(data.registration_token, "google_verified")
    google_id = payload.get("sub")
    verified_email = payload.get("email", "").lower().strip()
    google_name = payload.get("name")
    if not google_id or not verified_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google registration token is invalid.",
        )

    requested_role = data.requested_role.strip().upper()
    if requested_role not in ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="role must be one of: " + ", ".join(ROLES),
        )

    # Privileged role restriction: Google registration must never request ADMIN or REGULATOR
    if requested_role in PRIVILEGED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public Google registration cannot request privileged roles (ADMIN, REGULATOR).",
        )

    # Uniqueness checks
    existing_user = db.query(User).filter(
        (User.email == verified_email) | (User.google_id == google_id)
    ).first()
    if existing_user:
        if existing_user.auth_provider == "local" or not existing_user.google_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "An account with this email address already exists using email and password. "
                    "Please sign in using your email and password."
                ),
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    clean_username = data.username.strip()
    if db.query(User).filter(User.username == clean_username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken. Please choose another username.",
        )

    user = User(
        username=clean_username,
        email=verified_email,
        full_name=data.full_name.strip() if data.full_name else google_name,
        password_hash=hash_password(data.password or secrets.token_urlsafe(32)),
        role=requested_role,
        organization=data.organization.strip() if data.organization else None,
        status="PENDING",
        auth_provider="google",
        google_id=google_id,
        is_active=True,
    )

    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists.",
        )
    db.refresh(user)

    # Persist notification for administrator approval
    create_pending_approval_notification(db, user)

    return {
        "success": True,
        "message": (
            "Google registration submitted successfully. Your account is pending "
            "administrator approval. Once approved, you can sign in using your "
            "email and password."
        ),
        "user_id": str(user.id),
        "status": user.status,
    }


@router.post("/google/link")
def link_google_account(
    data: GoogleLinkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        identity = google_auth_service.verify_id_token(data.id_token)
    except GoogleAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    google_email = identity["email"].lower().strip()
    google_id = identity["google_id"]

    if google_email != current_user.email.lower().strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The Google account email does not match your PharmaVerse account email.",
        )

    existing_link = (
        db.query(User)
        .filter(User.google_id == google_id, User.id != current_user.id)
        .first()
    )
    if existing_link:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This Google account is already linked to another PharmaVerse account.",
        )

    current_user.google_id = google_id
    db.commit()
    db.refresh(current_user)

    return {
        "success": True,
        "message": "Google account successfully linked to your PharmaVerse account. You can now sign in using Google.",
    }


# ============================================================================ #
# Forgot Password Flow                                                         #
# ============================================================================ #

@router.post("/password-reset")
def reset_password(data: PasswordResetRequest, db: Session = Depends(get_db)):
    email = data.email.lower().strip()
    otp_code = data.otp.strip()

    if data.new_password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Passwords do not match.",
        )

    now = _utc_now()
    record = (
        db.query(EmailOTP)
        .filter(
            EmailOTP.email == email,
            EmailOTP.purpose == "password_reset",
            EmailOTP.is_used.is_(False),
            EmailOTP.expires_at > now,
        )
        .order_by(EmailOTP.created_at.desc())
        .first()
    )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset code has expired or is invalid.",
        )

    if record.attempts >= settings.otp_max_attempts:
        record.is_used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed reset attempts. Please request a new code.",
        )

    record.attempts += 1
    expected_hash = _hash_otp(email, otp_code)

    if not hmac.compare_digest(record.otp_hash, expected_hash):
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code.",
        )

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email address.",
        )

    # Update password and mark OTP used
    record.is_used = True
    user.password_hash = hash_password(data.new_password)
    db.commit()

    return {
        "success": True,
        "message": "Password reset successfully. You can now sign in with your new password.",
    }


# ============================================================================ #
# Sign In Endpoint (Email + Password Only)                                      #
# ============================================================================ #

@router.post("/login", response_model=LoginResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    identifier = form_data.username.strip()
    user = db.query(User).filter(
        (User.email == identifier.lower()) | (User.username == identifier)
    ).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check registration approval status
    if user.status == "PENDING":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Your account is pending administrator approval. "
                "You will receive access once approved by an administrator."
            ),
        )
    if user.status == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account registration request was rejected by an administrator.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    if user.two_factor_enabled:
        _send_otp_code(user.email, "login_2fa", db)
        return LoginResponse(
            two_factor_required=True,
            email=user.email,
        )

    access_token = create_access_token(
        user_id=str(user.id),
        role=user.role,
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
    )


@router.post("/2fa/verify", response_model=TokenResponse)
def verify_two_factor(
    request: TwoFactorVerifyRequest,
    db: Session = Depends(get_db),
):
    email = request.email.lower().strip()
    now = _utc_now()
    record = (
        db.query(EmailOTP)
        .filter(
            EmailOTP.email == email,
            EmailOTP.purpose == "login_2fa",
            EmailOTP.is_used.is_(False),
            EmailOTP.expires_at > now,
        )
        .order_by(EmailOTP.created_at.desc())
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired or is invalid.",
        )
    if record.attempts >= settings.otp_max_attempts:
        record.is_used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed verification attempts. Please sign in again.",
        )
    record.attempts += 1
    expected_hash = _hash_otp(email, request.otp)
    if not hmac.compare_digest(record.otp_hash, expected_hash):
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code.",
        )

    user = db.query(User).filter(User.email == email).first()
    if not user or not user.two_factor_enabled or user.status != "APPROVED" or not user.is_active:
        record.is_used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not permitted to sign in.",
        )
    record.is_used = True
    db.commit()
    return TokenResponse(
        access_token=create_access_token(user_id=str(user.id), role=user.role),
        token_type="bearer",
    )


@router.patch("/2fa")
def update_two_factor_settings(
    request: TwoFactorSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if request.enabled and not email_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Configure Gmail SMTP before enabling email two-factor authentication.",
        )
    current_user.two_factor_enabled = request.enabled
    db.commit()
    return {
        "success": True,
        "two_factor_enabled": current_user.two_factor_enabled,
    }


# ============================================================================ #
# Legacy Direct Registration (Preserved for tests & bootstrap)                 #
# ============================================================================ #

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(ADMIN)),
):

    existing_user = db.query(User).filter(
        (User.email == user_data.email)
        | (User.username == user_data.username)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        )

    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=user_data.role,
        organization=user_data.organization,
        status="APPROVED",
        auth_provider="local",
        is_active=True,
    )

    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        )
    db.refresh(user)

    return user


@router.get("/me", response_model=CurrentUserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
