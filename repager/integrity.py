"""Local evidence integrity, not protection against an owner controlling the host/key."""
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path
from .store import atomic_write


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _key(root, create=False):
    path = Path(root) / ".integrity-key"
    if create and not path.exists():
        try:
            atomic_write(path, secrets.token_bytes(32), overwrite=False)
        except FileExistsError:
            pass
    if path.is_symlink():
        raise ValueError("Evidence integrity key must not be a symlink")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        if os.fstat(stream.fileno()).st_mode & 0o077:
            raise ValueError("Evidence integrity key permissions must be owner-only")
        value = stream.read(33)
    if len(value) != 32:
        raise ValueError("Evidence integrity key is missing or corrupt")
    return value


def sign(root, value):
    body = {k: v for k, v in value.items() if k != "signature"}
    return hmac.new(_key(root, create=True), digest(body).encode(), hashlib.sha256).hexdigest()


def validate(root, value):
    signature = value.get("signature") if isinstance(value, dict) else None
    if not isinstance(signature, str):
        raise ValueError("Evidence manifest is unsigned; recapture or reverify this pre-integrity review")
    body = {k: v for k, v in value.items() if k != "signature"}
    expected = hmac.new(_key(root), digest(body).encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise ValueError("Evidence manifest signature does not match")
