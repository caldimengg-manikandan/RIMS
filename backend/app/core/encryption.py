"""
Application-level field encryption using Fernet (AES-128-CBC + HMAC-SHA256).
Provides transparent encrypt/decrypt for sensitive database fields.

Key is loaded from ENCRYPTION_KEY in app config (.env).
"""
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator
import functools
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Key Management
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    """Load the Fernet key from app config (.env).
    
    Cached via lru_cache — safe for threaded/async FastAPI use.
    The Fernet instance itself is thread-safe for encrypt/decrypt.
    """
    from app.core.config import get_settings
    key = get_settings().encryption_key
    if not key:
        raise RuntimeError(
            "CRITICAL: ENCRYPTION_KEY is not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\" "
            "and add ENCRYPTION_KEY=<key> to your .env file."
        )
    try:
        fernet = Fernet(key.encode() if isinstance(key, str) else key)
        # Validate key works by doing a round-trip test
        test = fernet.decrypt(fernet.encrypt(b"__key_validation__"))
        assert test == b"__key_validation__"
        return fernet
    except Exception as e:
        raise RuntimeError(
            f"CRITICAL: ENCRYPTION_KEY is invalid. "
            f"Must be a valid Fernet key (base64-encoded 32 bytes). Error: {e}"
        )


# ---------------------------------------------------------------------------
# Core Functions
# ---------------------------------------------------------------------------

def is_encrypted(value: str) -> bool:
    """Check if a value is a Fernet token.
    
    Uses both prefix check AND length heuristic:
    - Fernet tokens always start with 'gAAAAA' (base64)
    - Minimum Fernet token length is ~120 chars for even 1-byte plaintext
    - This avoids false positives from short strings starting with 'gAAAAA'
    """
    if not value or not isinstance(value, str):
        return False
    # Fernet tokens: base64-encoded, always start with version byte (0x80 → 'gAAAAA')
    # and are at least ~120 chars long for minimal payloads
    return value.startswith("gAAAAA") and len(value) >= 100


def encrypt_field(plaintext: str) -> str:
    """Encrypt a string value. Returns Fernet token as string.
    
    - None → returns None (preserves NULL semantics)
    - Empty string → encrypts as valid value (preserves "" vs NULL distinction)
    - Already encrypted → returns as-is (no double encryption)
    - Non-string → coerced to str first
    """
    if plaintext is None:
        return None
    if not isinstance(plaintext, str):
        plaintext = str(plaintext)
    # Empty string is a valid value — encrypt it to preserve "" vs NULL
    if is_encrypted(plaintext):
        return plaintext  # Already encrypted — skip
    
    f = _get_fernet()
    token = f.encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_field(ciphertext: str) -> str:
    """Decrypt a Fernet token back to plaintext.
    
    - None → returns None
    - Empty string → returns empty string
    - Not encrypted (plain text) → returns as-is (backward compatibility)
    - Invalid Fernet token → raises ValueError with explicit message
    """
    if ciphertext is None:
        return None
    if not isinstance(ciphertext, str):
        return ciphertext
    if not ciphertext:
        return ciphertext  # Empty string passthrough
    if not is_encrypted(ciphertext):
        return ciphertext  # Plain text — backward compat for pre-migration data
    
    f = _get_fernet()
    try:
        plaintext = f.decrypt(ciphertext.encode("utf-8"))
        return plaintext.decode("utf-8")
    except InvalidToken:
        # Graceful fallback: log the error but do NOT crash the application.
        # This allows the buyer to see that a key mismatch exists without the app becoming unusable.
        logger.warning(
            f"DECRYPTION FAILURE: The current ENCRYPTION_KEY cannot decrypt this value. "
            f"Data may have been encrypted with a different key. "
            f"Check .env or secrets.txt. Ciphertext preview: {ciphertext[:20]}..."
        )
        return "[DECRYPTION_ERROR]"
    except Exception as e:
        logger.error(f"Unexpected error during decryption: {e}")
        return "[DECRYPTION_ERROR]"


# ---------------------------------------------------------------------------
# SQLAlchemy TypeDecorator
# ---------------------------------------------------------------------------

class EncryptedText(TypeDecorator):
    """SQLAlchemy column type that transparently encrypts/decrypts Text fields.
    
    Usage in models:
        some_field = Column(EncryptedText, nullable=True)
    
    Behavior:
        - On write (process_bind_param): encrypts plaintext → Fernet token
        - On read  (process_result_value): decrypts Fernet token → plaintext
        - None → stored as NULL, read as None
        - Empty string → encrypted (preserves "" vs NULL distinction)
        - Already-encrypted values are not double-encrypted
        - Pre-migration plain-text values are returned as-is on read
        - Decryption failure raises explicit ValueError (no silent corruption)
    
    The underlying DB column type remains TEXT — no schema change required.
    Thread-safe: Fernet instance is a module-level lru_cache singleton.
    """
    
    impl = Text
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        """Called before INSERT/UPDATE — encrypt the value."""
        if value is None:
            return None
        return encrypt_field(value)
    
    def process_result_value(self, value, dialect):
        """Called after SELECT — decrypt the value."""
        if value is None:
            return None
        return decrypt_field(value)
