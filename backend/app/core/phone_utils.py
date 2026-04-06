import hashlib
import re
from typing import Optional, Tuple


def normalize_phone_digits(raw_phone: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Normalize phone input into digits-only representation.
    Returns (normalized_digits_or_empty, error_reason_or_none).
    
    CRITICAL FIX: Strips leading zeros and common prefixes (+91, etc.) 
    to ensure 9876543210 matches +91 98765 43210.
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

    # 1. Remove all non-digit characters.
    digits = re.sub(r"\D", "", raw_phone)
    
    # 2. Aggressive normalization (Point 1):
    # Remove leading zeros.
    digits = digits.lstrip("0")
    
    # 3. Country Code Fix (Point 4):
    # Only remove if starts with 91 AND total length > 10.
    if digits.startswith("91") and len(digits) > 10:
        digits = digits[2:]
    
    if not digits:
        return None, None
        
    if len(digits) < 10 or len(digits) > 15:
        return None, "invalid_length"

    return digits, None


def compute_phone_hash(normalized_digits: Optional[str]) -> Optional[str]:
    """Deterministic sha256 hash of normalized digits (for dedupe/indexing)."""
    if not normalized_digits:
        return None
    return hashlib.sha256(normalized_digits.encode("utf-8")).hexdigest()

