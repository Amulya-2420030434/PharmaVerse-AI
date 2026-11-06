"""Secure one-time CLI bootstrap command for creating the initial PharmaVerse AI Administrator.

Enforces strict one-time execution: refuses to run if an administrator already exists.
Never hardcodes or prints passwords/secrets.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.roles import ADMIN
from app.database.connection import SessionLocal
from app.models.user import User
from app.services.auth_service import hash_password
from sqlalchemy.orm import Session


def bootstrap_admin(
    username: str,
    email: str,
    password: str,
    organization: str | None = None,
    db: Session | None = None,
) -> bool:
    clean_username = username.strip()
    clean_email = email.lower().strip()

    if len(clean_username) < 3:
        print("Error: Username must be at least 3 characters long.", file=sys.stderr)
        return False

    if "@" not in clean_email or "." not in clean_email:
        print("Error: Invalid email address format.", file=sys.stderr)
        return False

    if len(password) < 8:
        print("Error: Password must be at least 8 characters long.", file=sys.stderr)
        return False

    def _execute(session: Session) -> bool:
        # 1. Enforce strict one-time execution: refuse if an ADMIN already exists
        existing_admin = session.query(User).filter(User.role == ADMIN).first()
        if existing_admin:
            print(
                "Security Error: An administrator account already exists. "
                "The one-time bootstrap command cannot be reused. "
                "Use the administrative portal to manage users.",
                file=sys.stderr,
            )
            return False

        # 2. Check for username or email collisions
        collision = (
            session.query(User)
            .filter((User.email == clean_email) | (User.username == clean_username))
            .first()
        )
        if collision:
            print(
                f"Error: A user account with this username or email already exists.",
                file=sys.stderr,
            )
            return False

        # 3. Create the initial administrator
        admin = User(
            username=clean_username,
            email=clean_email,
            password_hash=hash_password(password),
            role=ADMIN,
            organization=organization.strip() if organization else "PharmaVerse Administration",
            status="APPROVED",
            auth_provider="local",
            is_active=True,
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)

        print(
            f"Success: Initial administrator '{admin.username}' ({admin.email}) created successfully with role ADMIN."
        )
        return True

    if db is not None:
        return _execute(db)

    with SessionLocal() as session:
        return _execute(session)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-time CLI bootstrap for initial PharmaVerse AI Administrator."
    )
    parser.add_argument(
        "--username",
        required=True,
        help="Administrator username",
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Administrator email address",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Administrator password (if omitted, prompts securely without echoing)",
    )
    parser.add_argument(
        "--organization",
        default="PharmaVerse Administration",
        help="Organization name",
    )

    args = parser.parse_args()

    password = args.password
    if not password:
        password = getpass.getpass("Enter password for initial administrator: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Error: Passwords do not match.", file=sys.stderr)
            sys.exit(1)

    ok = bootstrap_admin(
        username=args.username,
        email=args.email,
        password=password,
        organization=args.organization,
    )
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()

