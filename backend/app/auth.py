"""Authentification : mots de passe hachés (PBKDF2) et jetons signés (HMAC-SHA256).

Uniquement la bibliothèque standard : pas de dépendance crypto supplémentaire.
Le jeton est `base64(payload).base64(signature)`, envoyé en `Authorization: Bearer …`.
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import User

log = logging.getLogger("cloudtalent")

ROLES = ("admin", "consultant")
TOKEN_TTL = int(os.getenv("TOKEN_TTL_SECONDS", str(12 * 3600)))

_secret = os.getenv("SECRET_KEY")
if not _secret:
    # Sans SECRET_KEY, les jetons sont invalidés à chaque redémarrage : acceptable en dev seulement.
    log.warning("SECRET_KEY non défini : clé aléatoire générée pour ce processus")
    _secret = secrets.token_urlsafe(32)
SECRET_KEY = _secret.encode()

_PBKDF2_ITER = 260_000


# --- Mots de passe ---------------------------------------------------------

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITER)
    return f"pbkdf2_sha256${_PBKDF2_ITER}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt, digest = stored.split("$")
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
    return hmac.compare_digest(candidate.hex(), digest)


# --- Jetons ----------------------------------------------------------------

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def create_token(user: User) -> str:
    payload = _b64(json.dumps({"sub": user.id, "exp": int(time.time()) + TOKEN_TTL}).encode())
    sig = _b64(hmac.new(SECRET_KEY, payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def decode_token(token: str) -> int | None:
    """Renvoie l'id utilisateur, ou None si le jeton est invalide ou expiré."""
    try:
        payload, sig = token.split(".")
        expected = _b64(hmac.new(SECRET_KEY, payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        data = json.loads(_unb64(payload))
        if data["exp"] < time.time():
            return None
        return int(data["sub"])
    except (ValueError, KeyError, TypeError):
        return None


# --- Dépendances FastAPI ---------------------------------------------------

_bearer = HTTPBearer(auto_error=False)


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    user_id = decode_token(creds.credentials) if creds else None
    user = db.get(User, user_id) if user_id is not None else None
    if user is None or not user.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    return user


# --- Amorçage --------------------------------------------------------------

def ensure_admin(db: Session) -> None:
    """Crée le compte admin défini par ADMIN_EMAIL / ADMIN_PASSWORD s'il n'existe aucun admin."""
    email, password = os.getenv("ADMIN_EMAIL"), os.getenv("ADMIN_PASSWORD")
    if not email or not password:
        return
    if db.scalar(select(User.id).where(User.role == "admin").limit(1)) is not None:
        return
    db.add(User(email=email.strip().lower(), password_hash=hash_password(password), role="admin"))
    db.commit()
    log.info("Compte administrateur %s créé", email)
