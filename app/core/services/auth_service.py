import os
import hmac
import hashlib
import base64
import json
import time
import secrets
from typing import Optional, Dict, Any, Tuple
from app.core.config import settings

def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def _base64url_decode(data: str) -> bytes:
    padding = '=' * (4 - (len(data) % 4)) if len(data) % 4 != 0 else ''
    return base64.urlsafe_b64decode((data + padding).encode('utf-8'))

class AuthService:
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = (secret_key or settings.SECRET_KEY or "mystic-explorers-secret-key-fallback").encode('utf-8')
        self.algorithm = settings.JWT_ALGORITHM
        self.default_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES

    def hash_password(self, password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Hashes a password using PBKDF2 HMAC-SHA256 with 100,000 iterations.
        Returns a tuple of (password_hash, salt).
        """
        if not salt:
            salt = secrets.token_hex(16)
        salt_bytes = bytes.fromhex(salt)
        derived = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt_bytes, 100000)
        password_hash = derived.hex()
        return password_hash, salt

    def verify_password(self, password: str, salt: str, expected_hash: str) -> bool:
        """
        Verifies a plaintext password against a stored salt and hash using constant-time comparison.
        """
        calculated_hash, _ = self.hash_password(password, salt)
        return hmac.compare_digest(calculated_hash, expected_hash)

    def create_token(self, player_id: str, player_name: str, expires_in_seconds: Optional[int] = None) -> str:
        """
        Generates a signed JWT token with player claims.
        """
        header = {"alg": self.algorithm, "typ": "JWT"}
        now = int(time.time())
        exp = now + (expires_in_seconds if expires_in_seconds is not None else self.default_expire_minutes * 60)
        payload = {
            "sub": player_id,
            "name": player_name,
            "iat": now,
            "exp": exp
        }

        header_b64 = _base64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
        payload_b64 = _base64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
        
        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
        signature = hmac.new(self.secret_key, signing_input, hashlib.sha256).digest()
        signature_b64 = _base64url_encode(signature)

        return f"{header_b64}.{payload_b64}.{signature_b64}"

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decodes and verifies a JWT token. Returns payload dict if valid and unexpired, else None.
        """
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            header_b64, payload_b64, signature_b64 = parts
            signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
            expected_signature = hmac.new(self.secret_key, signing_input, hashlib.sha256).digest()
            actual_signature = _base64url_decode(signature_b64)

            if not hmac.compare_digest(expected_signature, actual_signature):
                return None

            header = json.loads(_base64url_decode(header_b64).decode('utf-8'))
            if header.get("alg") != self.algorithm:
                return None

            payload = json.loads(_base64url_decode(payload_b64).decode('utf-8'))
            exp = payload.get("exp")
            if exp and int(time.time()) > exp:
                return None # Expired

            return payload
        except Exception:
            return None

auth_service = AuthService()
