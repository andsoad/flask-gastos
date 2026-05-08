"""
Auth utilities usando solo stdlib de Python.
JWT simplificado con hmac + hashlib (sin dependencias externas).
"""
import hmac
import hashlib
import base64
import json
import time


# ── Password hashing (pbkdf2 — stdlib) ────────────────────────────────────────

def hash_password(password: str) -> str:
    import os
    salt = base64.b64encode(os.urandom(16)).decode()
    dk   = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 260000)
    return f"pbkdf2:sha256:260000:{salt}:{base64.b64encode(dk).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, algo, iters, salt, hashed = stored.split(':')
        dk = hashlib.pbkdf2_hmac(algo, password.encode(), salt.encode(), int(iters))
        return hmac.compare_digest(base64.b64encode(dk).decode(), hashed)
    except Exception:
        return False


# ── Token (HMAC-SHA256, sin librerías externas) ───────────────────────────────

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def _b64url_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + '=' * (pad % 4))


def create_token(payload: dict, secret: str, expires_in: int = 60 * 60 * 24 * 7) -> str:
    """Crea un token HMAC-SHA256. expires_in en segundos (default 7 días)."""
    header  = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = dict(payload)
    payload['exp'] = int(time.time()) + expires_in
    body    = _b64url_encode(json.dumps(payload).encode())
    sig     = _b64url_encode(
        hmac.new(secret.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
    )
    return f"{header}.{body}.{sig}"


def decode_token(token: str, secret: str) -> dict | None:
    """Verifica y decodifica el token. Retorna None si es inválido o expirado."""
    try:
        header, body, sig = token.split('.')
        expected = _b64url_encode(
            hmac.new(secret.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(_b64url_decode(body))
        if payload.get('exp', 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None
