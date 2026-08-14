from datetime import datetime, timedelta, timezone

import jwt
from jwt import PyJWTError as JWTError

from app.config import ALGORITHM, SECRET_KEY

# Short-lived tokens minted by POST /api/files/{short_code}/unlock and consumed
# by GET /f/{short_code}?token=... to grant access to a password-protected
# shared file/image without exposing an external "redirect_url" (unlike link
# unlock, our own backend streams the blob — there's nowhere else to redirect to).
FILE_ACCESS_TOKEN_EXPIRE_MINUTES = 10

# Distinct audience (in addition to the "purpose" claim below) so a real login
# access token — minted with aud="shrt-api" by app.services.auth — can never
# be replayed here, and vice versa.
FILE_ACCESS_AUDIENCE = "shrt-file-access"


def create_file_access_token(short_code: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": short_code,
        "purpose": "file-access",
        "iat": now,
        "exp": now + timedelta(minutes=FILE_ACCESS_TOKEN_EXPIRE_MINUTES),
        "iss": "shrt",
        "aud": FILE_ACCESS_AUDIENCE,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_file_access_token(token: str, short_code: str) -> bool:
    """True only if `token` is a valid, unexpired file-access token minted for
    this exact short_code. Any decode failure (bad signature, expired, wrong
    audience/issuer) or a token minted for a different file returns False
    rather than raising — callers treat this as a plain access-denied check."""
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=FILE_ACCESS_AUDIENCE,
            issuer="shrt",
        )
    except JWTError:
        return False
    return payload.get("purpose") == "file-access" and payload.get("sub") == short_code
