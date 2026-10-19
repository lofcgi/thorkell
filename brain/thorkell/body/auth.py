"""Bridge handshake MAC: HMAC-SHA256(bytes.fromhex(token), "nonce|role|session"), hex encoded.

Must stay identical to plugin/Thorkell.Wire/Auth.cs (checked by protocol/v1/hmac_vectors.json).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets


def new_hex(nbytes: int) -> str:
    return secrets.token_hex(nbytes)


def mac(token_hex: str, nonce: str, role: str, session: str) -> str:
    message = f"{nonce}|{role}|{session}".encode()
    return hmac.new(bytes.fromhex(token_hex), message, hashlib.sha256).hexdigest()


def verify(token_hex: str, nonce: str, role: str, session: str, candidate: str) -> bool:
    return hmac.compare_digest(mac(token_hex, nonce, role, session), candidate.lower())
