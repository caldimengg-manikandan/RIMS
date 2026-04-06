import hashlib
import re
from typing import Optional, Tuple


def normalize_phone_digits(raw_phone: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Normalize phone input into digits-only representation.
    Returns (normalized_digits_or_empty, error_reason_or_none).

    Non-breaking: error messages are handled by API layer to preserve HTTP behavior.
    """
    if raw_phone is None:
        return None, None
    raw_phone = str(raw_phone).strip()
    if not raw_phone:
        return "", None

    # Reject any letters.
    if re.search(r"[A-Za-z]", raw_phone):
        return None, "letters_present"

    # Allow digits with separators + leading '+' only.
    if re.search(r"[^0-9+\s()-]", raw_phone):
        return None, "invalid_characters"

    digits = re.sub(r"\D", "", raw_phone)
    if not digits or len(digits) < 10 or len(digits) > 15:
        return None, "invalid_length"

    return digits, None


def compute_phone_hash(normalized_digits: Optional[str]) -> Optional[str]:
    """Deterministic sha256 hash of normalized digits (for dedupe/indexing)."""
    if not normalized_digits:
        return None
    return hashlib.sha256(normalized_digits.encode("utf-8")).hexdigest()

