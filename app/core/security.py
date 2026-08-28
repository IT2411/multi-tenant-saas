import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

# Initialize Argon2id password hasher
ph = PasswordHasher(
    time_cost=3,  # 3 iterations
    memory_cost=65536,  # 64 MB memory
    parallelism=4,  # 4 threads
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hashes plain text password using Argon2id."""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies plain password against Argon2id hash in constant time."""
    try:
        return ph.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def create_jwt_token(
    subject: str | uuid.UUID,
    token_type: str,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, str, datetime]:
    """Generates a signed JWT with a unique token ID (jti) and expiration timestamp."""
    jti = str(uuid.uuid4())
    expire = datetime.now(UTC) + expires_delta
    payload: dict[str, Any] = {
        "sub": str(subject),
        "jti": jti,
        "type": token_type,
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    if extra_claims:
        payload.update(extra_claims)

    encoded_jwt = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    return encoded_jwt, jti, expire


def decode_jwt_token(token: str) -> dict[str, Any]:
    """Decodes and validates token signature and expiration."""
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=["HS256"],
        options={"require": ["exp", "sub", "jti", "type"]},
    )
