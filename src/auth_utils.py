"""
Auth usando solo stdlib — sin python-jose ni passlib.
Mucho más ligero para el startup de Workers.
"""
import hmac
import hashlib
import base64
import json
import time
import os


# ── Password (pbkdf2 stdlib) ───────────────────────────────────────────────────

def hash_password(password: str) -> str:
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


# ── Token (HMAC-SHA256 stdlib) ─────────────────────────────────────────────────

def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

def _b64ud(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))

def create_token(payload: dict, secret: str, expires: int = 604800) -> str:
    hdr  = _b64u(json.dumps({"alg":"HS256","typ":"JWT"}).encode())
    p    = dict(payload)
    p['exp'] = int(time.time()) + expires
    body = _b64u(json.dumps(p).encode())
    sig  = _b64u(hmac.new(secret.encode(), f"{hdr}.{body}".encode(), hashlib.sha256).digest())
    return f"{hdr}.{body}.{sig}"

def decode_token(token: str, secret: str):
    try:
        hdr, body, sig = token.split('.')
        exp_sig = _b64u(hmac.new(secret.encode(), f"{hdr}.{body}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, exp_sig):
            return None
        p = json.loads(_b64ud(body))
        return None if p.get('exp', 0) < int(time.time()) else p
    except Exception:
        return None
