import base64

from cryptography.fernet import Fernet

from backend.app.core.config import settings


def _get_fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY.encode()
    if len(key) != 32:
        raise ValueError(
            f"ENCRYPTION_KEY must be exactly 32 bytes when UTF-8 encoded; "
            f"got {len(key)} bytes. Set a valid 32-byte key in your environment."
        )
    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key)


def encrypt_value(plaintext: str) -> str:
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()
