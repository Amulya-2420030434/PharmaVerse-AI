"""Google OAuth identity verification service.

Validates Google ID tokens securely against Google's tokeninfo endpoint.
Keeps credentials in environment variables and never exposes tokens in logs.
"""

import logging
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
VALID_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


class GoogleAuthError(Exception):
    pass


class GoogleAuthService:
    def __init__(self, client_id: Optional[str] = None):
        self.client_id = client_id or settings.google_client_id

    def verify_id_token(self, id_token: str) -> Dict[str, Any]:
        """Verify a Google ID token and return user identity details.

        Returns a dictionary with:
          - google_id (sub)
          - email
          - name
          - email_verified
        """
        if not id_token or not id_token.strip():
            raise GoogleAuthError("Google ID token is required")

        if not self.client_id or not self.client_id.strip():
            raise GoogleAuthError("Google Sign-In is not configured")

        try:
            with httpx.Client(timeout=8.0) as client:
                response = client.get(
                    GOOGLE_TOKENINFO_URL,
                    params={"id_token": id_token.strip()},
                )
        except httpx.HTTPError as exc:
            logger.error("Failed to reach Google tokeninfo endpoint: %s", exc.__class__.__name__)
            raise GoogleAuthError("Unable to reach Google authentication service") from exc

        if response.status_code != 200:
            logger.warning("Google tokeninfo returned status %s", response.status_code)
            raise GoogleAuthError("Invalid or expired Google token")

        try:
            data = response.json()
        except ValueError as exc:
            raise GoogleAuthError("Google authentication service returned an invalid response") from exc
        if not isinstance(data, dict):
            raise GoogleAuthError("Google authentication service returned an invalid response")

        # Validate issuer
        iss = data.get("iss")
        if iss not in VALID_ISSUERS:
            raise GoogleAuthError("Invalid token issuer")

        # Validate audience if client ID is configured
        if self.client_id and self.client_id.strip():
            aud = data.get("aud")
            if aud != self.client_id.strip():
                raise GoogleAuthError("Google token was not issued for this application")

        # Ensure email is verified
        email_verified = data.get("email_verified")
        is_verified = (
            email_verified is True
            or str(email_verified).lower() in ("true", "1", "yes")
        )
        if not is_verified:
            raise GoogleAuthError("Google account email address is not verified")

        email = data.get("email")
        subject = data.get("sub")
        if not email or not subject:
            raise GoogleAuthError("Google token does not contain a verified identity")

        return {
            "google_id": subject,
            "email": email.strip().lower(),
            "name": data.get("name") or email.split("@")[0],
            "email_verified": True,
        }


google_auth_service = GoogleAuthService()
