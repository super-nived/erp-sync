from typing import Dict

import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from fastapi import Header
from pydantic import BaseModel

from app.core.exceptions import UnauthorizedException
from app.core.logging import get_logger
from app.core.settings import settings

logger = get_logger(__name__)


class JWTClaims(BaseModel):
    """JWT token claims model."""

    user_name: str | None = None
    sub: str | None = None
    exp: int | None = None
    iat: int | None = None
    nbf: int | None = None


# Load and parse the RSA public key
def _load_public_key():
    """Load the RSA public key for JWT verification."""
    if not settings.public_key:
        logger.error("PUBLIC_KEY environment variable is not set")
        raise ValueError("PUBLIC_KEY is not configured")

    try:
        public_key_pem = f"""-----BEGIN PUBLIC KEY-----
{settings.public_key}
-----END PUBLIC KEY-----"""

        clean_key = public_key_pem.strip()
        public_key_obj = serialization.load_pem_public_key(
            clean_key.encode("utf-8"), backend=default_backend()
        )
        logger.info("Public key loaded successfully")
        return public_key_obj
    except ValueError as e:
        logger.fatal(f"Failed to parse public key: {e}")
        raise ValueError(f"Failed to parse public key: {e}")


# Initialize public key at module load
try:
    PUBLIC_KEY_OBJ = _load_public_key()
except ValueError:
    # Allow startup without key for non-auth routes, but will fail on protected routes
    PUBLIC_KEY_OBJ = None
    logger.warning("Running without public key - authentication will fail")


def verify_token(authorization: str = Header(None)) -> Dict:
    """
    Verify JWT token from Authorization header.

    This function is used as a FastAPI dependency to protect routes.

    Args:
        authorization: Authorization header value (injected by FastAPI)

    Returns:
        Dict: Decoded JWT claims

    Raises:
        UnauthorizedException: If token is missing, invalid, or expired
    """
    if not authorization:
        logger.warning("No Authorization header found")
        raise UnauthorizedException(message="Missing Authorization header")

    if not authorization.startswith("Bearer "):
        logger.warning(f"Invalid Authorization header format: {authorization}")
        raise UnauthorizedException(message="Invalid Authorization header format")

    token = authorization.split(" ")[1]

    if not PUBLIC_KEY_OBJ:
        logger.error("Public key not loaded")
        raise UnauthorizedException(message="Authentication not configured")

    try:
        claims = jwt.decode(
            token,
            PUBLIC_KEY_OBJ,
            algorithms=["RS256"],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
                "verify_aud": False,
                "verify_iss": False,
            },
        )
        logger.debug(f"Token verified successfully for user: {claims.get('user_name')}")
        return claims

    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise UnauthorizedException(message="Token has expired")

    except jwt.InvalidSignatureError:
        logger.warning("Invalid token signature")
        raise UnauthorizedException(message="Invalid token signature")

    except jwt.DecodeError as e:
        logger.warning(f"Token decode error: {e}")
        raise UnauthorizedException(message=f"Token decode error: {str(e)}")

    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise UnauthorizedException(message=str(e))

    except Exception as e:
        logger.error(f"Unexpected error during JWT validation: {e}")
        raise UnauthorizedException(message="Authentication failed")


def get_current_user(claims: Dict = None) -> JWTClaims:
    """
    Extract user information from JWT claims.

    Args:
        claims: Decoded JWT claims from verify_token

    Returns:
        JWTClaims: Parsed user claims
    """
    if not claims:
        return JWTClaims()
    return JWTClaims(**claims)


def get_user_name(claims: Dict) -> str | None:
    """
    Get user_name from JWT claims.

    Args:
        claims: Decoded JWT claims

    Returns:
        str | None: Username if present in claims
    """
    return claims.get("user_name")
