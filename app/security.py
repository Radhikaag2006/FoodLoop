import hashlib
import hmac
import re
import secrets
import time
from collections import defaultdict, deque

from fastapi import HTTPException

from .config import SECRET_KEY

# ---------- passwords ----------
_N, _R, _P = 2 ** 14, 8, 1


def hash_pw(pw: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=_N, r=_R, p=_P)
    return f"scrypt${salt.hex()}${h.hex()}"


def check_pw(pw: str, stored: str) -> bool:
    try:
        _, salt, h = stored.split("$")
        calc = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt),
                              n=_N, r=_R, p=_P)
        return hmac.compare_digest(calc.hex(), h)
    except Exception:
        return False


def check_strength(pw: str):
    if len(pw) < 8 or not re.search(r"[A-Za-z]", pw) \
            or not re.search(r"\d", pw):
        raise HTTPException(
            422, "Use at least 8 characters with a letter and a number.")


# ---------- identifiers ----------
def norm_phone(v: str) -> str:
    d = re.sub(r"\D", "", v or "")
    if d.startswith("91") and len(d) == 12:
        d = d[2:]
    if d.startswith("0") and len(d) == 11:
        d = d[1:]
    if not re.fullmatch(r"[6-9]\d{9}", d):
        raise HTTPException(422, "Enter a valid 10-digit mobile number.")
    return d


def norm_email(v: str) -> str:
    v = (v or "").strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v) or len(v) > 120:
        raise HTTPException(422, "Enter a valid email address.")
    return v


def norm_flat(v: str) -> str:
    v = re.sub(r"\s+", "", (v or "").upper())
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9\-/]{0,17}", v):
        raise HTTPException(
            422, "Enter your flat number, for example A-101.")
    return v


def clean(v: str, n: int, field="Text") -> str:
    v = re.sub(r"\s+", " ", (v or "")).strip()
    if not v:
        raise HTTPException(422, f"{field} is required.")
    return v[:n]


_ALPHA = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def make_code(n=6) -> str:
    return "".join(secrets.choice(_ALPHA) for _ in range(n))


def hash_code(code: str) -> str:
    return hashlib.sha256((SECRET_KEY + code).encode()).hexdigest()


# ---------- resident QR token (rotates, signed) ----------
def _sig(flat_id: int, ts: int) -> str:
    msg = f"{flat_id}.{ts}".encode()
    return hmac.new(SECRET_KEY.encode(), msg,
                    hashlib.sha256).hexdigest()[:20]


def qr_token(flat_id: int) -> str:
    ts = int(time.time())
    return f"FL1.{flat_id}.{ts}.{_sig(flat_id, ts)}"


def read_qr(token: str, max_age: int):
    """Return flat_id from a valid, fresh token or raise 422."""
    try:
        tag, fid, ts, sig = token.strip().split(".")
        fid, ts = int(fid), int(ts)
        ok = tag == "FL1" and hmac.compare_digest(sig, _sig(fid, ts))
    except Exception:
        ok = False
    if not ok:
        raise HTTPException(422, "Not a FoodLoop QR code.")
    if time.time() - ts > max_age:
        raise HTTPException(
            422, "This QR has expired. Ask the resident to reopen it.")
    return fid


# ---------- simple in-memory rate limiter ----------
_hits = defaultdict(deque)


def rate_limit(key: str, limit: int, window: int):
    """Allow `limit` hits per `window` seconds per key. For several
    server processes, move this to Redis."""
    q = _hits[key]
    t = time.time()
    while q and t - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(
            429, "Too many attempts. Please wait a few minutes.")
    q.append(t)
