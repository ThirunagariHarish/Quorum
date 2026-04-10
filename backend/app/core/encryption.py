import base64

from cryptography.fernet import Fernet

from backend.app.core.config import settings


def _get_fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY.encode()
    # Pad or hash to 32 bytes then base64-encode for Fernet compatibility
    key_bytes = key.ljust(32, b"\0")[:32]
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_value(plaintext: str) -> str:
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()
