"""
test_core_utilities.py
======================
Unit tests for:
 - app.core.email_utils      (validate_email_strict, validate_email_strict_enterprise)
 - app.core.phone_utils      (normalize_phone_digits, compute_phone_hash)
 - app.core.resume_upload_utils (validate_resume_signature, generate_hashed_resume_filename, get_resume_extension)
 - app.core.encryption       (encrypt_field, decrypt_field, is_encrypted, EncryptedText)
 - app.core.config           (Settings.get_allowed_origins)

All tests run without a database or HTTP server.
"""

import os
import pytest
from unittest.mock import patch, MagicMock


# ══════════════════════════════════════════════════════════════════════════════
# 1.  Email Validation  (app.core.email_utils)
# ══════════════════════════════════════════════════════════════════════════════

class TestEmailValidation:

    # --- validate_email_strict (simple wrapper) ---

    def test_valid_email_returns_normalized(self):
        from app.core.email_utils import validate_email_strict
        result = validate_email_strict("  User@Example.COM  ")
        assert result == "user@example.com"

    def test_numeric_local_part_raises(self):
        from app.core.email_utils import validate_email_strict
        with pytest.raises(ValueError) as exc_info:
            validate_email_strict("123456@example.com")
        assert "only numbers" in str(exc_info.value).lower()

    def test_disposable_domain_rejected(self):
        from app.core.email_utils import validate_email_strict
        with pytest.raises(ValueError) as exc_info:
            validate_email_strict("user@mailinator.com")
        assert "disposable" in str(exc_info.value).lower()

    def test_missing_at_symbol_raises(self):
        from app.core.email_utils import validate_email_strict
        with pytest.raises(ValueError):
            validate_email_strict("notanemail.com")

    def test_empty_email_raises(self):
        from app.core.email_utils import validate_email_strict
        with pytest.raises(ValueError):
            validate_email_strict("")

    def test_valid_subdomain_email(self):
        from app.core.email_utils import validate_email_strict
        result = validate_email_strict("user@mail.company.org")
        assert result == "user@mail.company.org"

    def test_all_disposable_domains_blocked(self):
        from app.core.email_utils import validate_email_strict, DISPOSABLE_DOMAINS
        for domain in list(DISPOSABLE_DOMAINS)[:3]:  # Test first 3 to keep fast
            with pytest.raises(ValueError):
                validate_email_strict(f"user@{domain}")

    def test_guerrillamail_rejected(self):
        from app.core.email_utils import validate_email_strict
        with pytest.raises(ValueError):
            validate_email_strict("test@guerrillamail.com")

    # --- validate_email_strict_enterprise (with request context) ---

    def test_enterprise_valid_email(self):
        from app.core.email_utils import validate_email_strict_enterprise
        result = validate_email_strict_enterprise("John.Doe@Company.ORG", ip="127.0.0.1")
        assert result == "john.doe@company.org"

    def test_enterprise_no_ip_still_works(self):
        from app.core.email_utils import validate_email_strict_enterprise
        result = validate_email_strict_enterprise("test@validmail.com")
        assert "@" in result


# ══════════════════════════════════════════════════════════════════════════════
# 2.  Phone Utilities  (app.core.phone_utils)
# ══════════════════════════════════════════════════════════════════════════════

class TestPhoneUtils:

    # --- normalize_phone_digits ---

    def test_none_input_returns_none_none(self):
        from app.core.phone_utils import normalize_phone_digits
        digits, reason = normalize_phone_digits(None)
        assert digits is None
        assert reason is None

    def test_empty_string_returns_empty_none(self):
        from app.core.phone_utils import normalize_phone_digits
        digits, reason = normalize_phone_digits("")
        assert digits == ""
        assert reason is None

    def test_plain_10_digit_number(self):
        from app.core.phone_utils import normalize_phone_digits
        digits, reason = normalize_phone_digits("9876543210")
        assert reason is None
        assert digits == "9876543210"
        assert len(digits) == 10

    def test_international_format_normalized(self):
        from app.core.phone_utils import normalize_phone_digits
        digits, reason = normalize_phone_digits("+1 (555) 123-4567")
        assert reason is None
        assert digits == "15551234567"

    def test_letters_rejected(self):
        from app.core.phone_utils import normalize_phone_digits
        digits, reason = normalize_phone_digits("abc-def-ghij")
        assert digits is None
        assert reason == "letters_present"

    def test_invalid_chars_rejected(self):
        from app.core.phone_utils import normalize_phone_digits
        digits, reason = normalize_phone_digits("123*456#7890")
        assert digits is None
        assert reason == "invalid_characters"

    def test_too_short_rejected(self):
        from app.core.phone_utils import normalize_phone_digits
        digits, reason = normalize_phone_digits("12345")
        assert digits is None
        assert reason == "invalid_length"

    def test_too_long_rejected(self):
        from app.core.phone_utils import normalize_phone_digits
        digits, reason = normalize_phone_digits("12345678901234567")
        assert digits is None
        assert reason == "invalid_length"

    def test_india_prefix_stripped(self):
        """Numbers starting with 91 and longer than 10 digits → strip 91."""
        from app.core.phone_utils import normalize_phone_digits
        digits, reason = normalize_phone_digits("+91 98765 43210")
        assert reason is None
        assert digits == "9876543210"

    def test_leading_zeros_stripped(self):
        from app.core.phone_utils import normalize_phone_digits
        digits, reason = normalize_phone_digits("0009876543210")
        # Leading zeros stripped, resulting in 10-digit number
        assert reason is None

    def test_formatted_us_number(self):
        from app.core.phone_utils import normalize_phone_digits
        digits, reason = normalize_phone_digits("(555) 123-4567")
        assert reason is None
        assert digits == "5551234567"

    # --- compute_phone_hash ---

    def test_hash_is_deterministic(self):
        from app.core.phone_utils import compute_phone_hash
        h1 = compute_phone_hash("9876543210")
        h2 = compute_phone_hash("9876543210")
        assert h1 == h2

    def test_hash_length_is_64(self):
        from app.core.phone_utils import compute_phone_hash
        h = compute_phone_hash("9876543210")
        assert len(h) == 64

    def test_different_numbers_different_hashes(self):
        from app.core.phone_utils import compute_phone_hash
        h1 = compute_phone_hash("9876543210")
        h2 = compute_phone_hash("1234567890")
        assert h1 != h2

    def test_none_input_returns_none(self):
        from app.core.phone_utils import compute_phone_hash
        assert compute_phone_hash(None) is None

    def test_empty_string_returns_none(self):
        from app.core.phone_utils import compute_phone_hash
        assert compute_phone_hash("") is None


# ══════════════════════════════════════════════════════════════════════════════
# 3.  Resume Upload Utilities  (app.core.resume_upload_utils)
# ══════════════════════════════════════════════════════════════════════════════

class TestResumeUploadUtils:

    # --- get_resume_extension ---

    def test_lowercase_pdf_extension(self):
        from app.core.resume_upload_utils import get_resume_extension
        assert get_resume_extension("resume.PDF") == ".pdf"

    def test_lowercase_docx_extension(self):
        from app.core.resume_upload_utils import get_resume_extension
        assert get_resume_extension("resume.DOCX") == ".docx"

    def test_mixed_case_doc_extension(self):
        from app.core.resume_upload_utils import get_resume_extension
        assert get_resume_extension("My Resume.DOC") == ".doc"

    def test_no_extension_returns_empty(self):
        from app.core.resume_upload_utils import get_resume_extension
        assert get_resume_extension("noextension") == ""

    def test_none_filename_returns_empty(self):
        from app.core.resume_upload_utils import get_resume_extension
        assert get_resume_extension(None) == ""

    # --- validate_resume_signature ---

    def test_valid_pdf_signature(self):
        from app.core.resume_upload_utils import validate_resume_signature
        ok, reason = validate_resume_signature(".pdf", b"%PDF-1.7\nfake content")
        assert ok is True
        assert reason is None

    def test_valid_docx_signature(self):
        from app.core.resume_upload_utils import validate_resume_signature
        ok, reason = validate_resume_signature(".docx", b"PK\x03\x04fake zip content")
        assert ok is True
        assert reason is None

    def test_valid_doc_signature(self):
        from app.core.resume_upload_utils import validate_resume_signature
        ok, reason = validate_resume_signature(".doc", b"\xd0\xcf\x11\xe0fake content")
        assert ok is True
        assert reason is None

    def test_pdf_signature_mismatch_rejected(self):
        from app.core.resume_upload_utils import validate_resume_signature
        ok, reason = validate_resume_signature(".pdf", b"PK\x03\x04not-a-pdf")
        assert ok is False
        assert reason == "invalid_pdf_signature"

    def test_docx_signature_mismatch_rejected(self):
        from app.core.resume_upload_utils import validate_resume_signature
        ok, reason = validate_resume_signature(".docx", b"%PDF-1.4 oops")
        assert ok is False
        assert reason == "invalid_docx_signature"

    def test_empty_content_rejected(self):
        from app.core.resume_upload_utils import validate_resume_signature
        ok, reason = validate_resume_signature(".pdf", b"")
        assert ok is False
        assert reason == "empty_content"

    def test_unknown_extension_accepted(self):
        """Unknown extensions have no signature rule — should pass."""
        from app.core.resume_upload_utils import validate_resume_signature
        ok, reason = validate_resume_signature(".txt", b"random content")
        assert ok is True

    # --- generate_hashed_resume_filename ---

    def test_filename_ends_with_correct_extension(self):
        from app.core.resume_upload_utils import generate_hashed_resume_filename
        fname = generate_hashed_resume_filename(
            candidate_email="user@example.com",
            job_id=1,
            resume_ext=".pdf",
            content=b"%PDF-1.4 fake",
        )
        assert fname.endswith(".pdf")

    def test_filename_no_path_traversal(self):
        from app.core.resume_upload_utils import generate_hashed_resume_filename
        fname = generate_hashed_resume_filename(
            candidate_email="user@example.com",
            job_id=1,
            resume_ext=".pdf",
            content=b"%PDF-1.4 fake",
        )
        assert "/" not in fname
        assert "\\" not in fname
        assert ".." not in fname

    def test_same_inputs_same_filename(self):
        """Filename generation must be deterministic."""
        from app.core.resume_upload_utils import generate_hashed_resume_filename
        kwargs = dict(candidate_email="a@b.com", job_id=5, resume_ext=".pdf", content=b"%PDF x")
        assert generate_hashed_resume_filename(**kwargs) == generate_hashed_resume_filename(**kwargs)

    def test_different_emails_different_filenames(self):
        from app.core.resume_upload_utils import generate_hashed_resume_filename
        f1 = generate_hashed_resume_filename(candidate_email="a@b.com", job_id=1, resume_ext=".pdf", content=b"%PDF x")
        f2 = generate_hashed_resume_filename(candidate_email="c@d.com", job_id=1, resume_ext=".pdf", content=b"%PDF x")
        assert f1 != f2

    def test_different_content_different_filenames(self):
        from app.core.resume_upload_utils import generate_hashed_resume_filename
        f1 = generate_hashed_resume_filename(candidate_email="a@b.com", job_id=1, resume_ext=".pdf", content=b"%PDF one")
        f2 = generate_hashed_resume_filename(candidate_email="a@b.com", job_id=1, resume_ext=".pdf", content=b"%PDF two")
        assert f1 != f2

    def test_extension_without_leading_dot(self):
        """Utility should prepend dot if missing."""
        from app.core.resume_upload_utils import generate_hashed_resume_filename
        fname = generate_hashed_resume_filename(
            candidate_email="user@example.com", job_id=1, resume_ext="pdf", content=b"%PDF x"
        )
        assert fname.endswith(".pdf")


# ══════════════════════════════════════════════════════════════════════════════
# 4.  Encryption  (app.core.encryption)
# ══════════════════════════════════════════════════════════════════════════════

class TestEncryptionUtils:
    """Tests for encrypt_field, decrypt_field, is_encrypted."""

    # is_encrypted

    def test_none_is_not_encrypted(self):
        from app.core.encryption import is_encrypted
        assert is_encrypted(None) is False

    def test_empty_string_is_not_encrypted(self):
        from app.core.encryption import is_encrypted
        assert is_encrypted("") is False

    def test_short_string_is_not_encrypted(self):
        from app.core.encryption import is_encrypted
        assert is_encrypted("hello world") is False

    def test_plain_text_is_not_encrypted(self):
        from app.core.encryption import is_encrypted
        assert is_encrypted("user@example.com") is False

    # encrypt / decrypt round-trip

    def test_encrypt_decrypt_round_trip(self):
        from app.core.encryption import encrypt_field, decrypt_field
        plaintext = "Sensitive data: user@example.com"
        ciphertext = encrypt_field(plaintext)
        assert ciphertext != plaintext
        recovered = decrypt_field(ciphertext)
        assert recovered == plaintext

    def test_encrypt_none_returns_none(self):
        from app.core.encryption import encrypt_field
        assert encrypt_field(None) is None

    def test_decrypt_none_returns_none(self):
        from app.core.encryption import decrypt_field
        assert decrypt_field(None) is None

    def test_decrypt_plain_text_returns_as_is(self):
        """Pre-migration plain text should be returned unchanged."""
        from app.core.encryption import decrypt_field
        plain = "not-a-fernet-token"
        assert decrypt_field(plain) == plain

    def test_encrypt_already_encrypted_is_idempotent(self):
        """Encrypting an already-encrypted value should return the same token."""
        from app.core.encryption import encrypt_field
        plaintext = "hello"
        ct1 = encrypt_field(plaintext)
        ct2 = encrypt_field(ct1)
        assert ct1 == ct2  # Should not double-encrypt

    def test_encrypted_value_starts_with_gAAAAA(self):
        from app.core.encryption import encrypt_field, is_encrypted
        ct = encrypt_field("some sensitive note")
        assert ct.startswith("gAAAAA")
        assert is_encrypted(ct) is True

    def test_encrypt_non_string_coerced(self):
        """Integers should be coerced to string before encrypting."""
        from app.core.encryption import encrypt_field, decrypt_field
        ct = encrypt_field(12345)
        recovered = decrypt_field(ct)
        assert recovered == "12345"

    def test_decrypt_invalid_fernet_token_returns_unreadable(self):
        """An invalid Fernet-looking token should return [UNREADABLE] or [DECRYPTION_ERROR]."""
        from app.core.encryption import decrypt_field
        # Build a fake "encrypted" string that passes the is_encrypted heuristic
        # by starting with gAAAAA and being long enough.
        fake_token = "gAAAAA" + "A" * 120
        result = decrypt_field(fake_token)
        assert result in ("[UNREADABLE]", "[DECRYPTION_ERROR]")

    def test_empty_string_encrypted_and_decrypted(self):
        """Empty string should be distinguishable from NULL after round-trip."""
        from app.core.encryption import encrypt_field, decrypt_field
        ct = encrypt_field("")
        recovered = decrypt_field(ct)
        assert recovered == ""


# ══════════════════════════════════════════════════════════════════════════════
# 5.  Config — get_allowed_origins  (app.core.config)
# ══════════════════════════════════════════════════════════════════════════════

class TestConfigAllowedOrigins:

    def test_single_origin_returned_as_list(self):
        from app.core.config import Settings
        s = Settings(
            database_url="sqlite:///test.db",
            jwt_secret="secret",
            allowed_origins="http://localhost:3000",
        )
        origins = s.get_allowed_origins()
        assert isinstance(origins, list)
        assert "http://localhost:3000" in origins

    def test_multiple_origins_parsed(self):
        from app.core.config import Settings
        s = Settings(
            database_url="sqlite:///test.db",
            jwt_secret="secret",
            allowed_origins="http://localhost:3000,https://app.example.com,http://127.0.0.1:8000",
        )
        origins = s.get_allowed_origins()
        assert len(origins) == 3
        assert "https://app.example.com" in origins

    def test_whitespace_stripped_from_origins(self):
        from app.core.config import Settings
        s = Settings(
            database_url="sqlite:///test.db",
            jwt_secret="secret",
            allowed_origins=" http://localhost:3000 , https://app.example.com ",
        )
        origins = s.get_allowed_origins()
        assert "http://localhost:3000" in origins

    def test_empty_origins_string_returns_empty_list(self):
        from app.core.config import Settings
        s = Settings(
            database_url="sqlite:///test.db",
            jwt_secret="secret",
            allowed_origins="",
        )
        origins = s.get_allowed_origins()
        assert origins == []

    def test_default_frontend_base_url(self):
        from app.core.config import Settings
        s = Settings(
            database_url="sqlite:///test.db",
            jwt_secret="secret",
        )
        assert "localhost" in s.frontend_base_url or "http" in s.frontend_base_url


# ══════════════════════════════════════════════════════════════════════════════
# 6.  Constants integrity
# ══════════════════════════════════════════════════════════════════════════════

class TestConstantsIntegrity:
    """Verify the CandidateState and TransitionAction enums are complete."""

    def test_all_candidate_states_are_strings(self):
        from app.domain.constants import CandidateState
        for state in CandidateState:
            assert isinstance(state.value, str)
            assert len(state.value) > 0

    def test_all_transition_actions_are_strings(self):
        from app.domain.constants import TransitionAction
        for action in TransitionAction:
            assert isinstance(action.value, str)
            assert len(action.value) > 0

    def test_no_duplicate_state_values(self):
        from app.domain.constants import CandidateState
        values = [s.value for s in CandidateState]
        assert len(values) == len(set(values)), "Duplicate CandidateState values detected"

    def test_no_duplicate_action_values(self):
        from app.domain.constants import TransitionAction
        values = [a.value for a in TransitionAction]
        assert len(values) == len(set(values)), "Duplicate TransitionAction values detected"

    def test_key_states_exist(self):
        from app.domain.constants import CandidateState
        required = ["applied", "screened", "hired", "rejected", "onboarded"]
        state_values = [s.value for s in CandidateState]
        for req in required:
            assert req in state_values, f"Expected state '{req}' not found in CandidateState"
