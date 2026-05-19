import pytest
from pydantic import ValidationError
from app.domain.schemas import UserRegister, ResetPasswordRequest

def test_password_validation_valid():
    # A robust, valid password should validate correctly
    data = {
        "email": "valid_user@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test User"
    }
    schema = UserRegister(**data)
    assert schema.password == "SecurePassword123!"

def test_password_validation_too_short():
    # Passwords must be at least 8 characters long
    data = {
        "email": "valid_user@example.com",
        "password": "Sec1!",
        "full_name": "Test User"
    }
    with pytest.raises(ValidationError) as excinfo:
        UserRegister(**data)
    assert "Password must be at least 8 characters long" in str(excinfo.value)

def test_password_validation_missing_upper():
    # Passwords must contain an uppercase letter
    data = {
        "email": "valid_user@example.com",
        "password": "securepassword123!",
        "full_name": "Test User"
    }
    with pytest.raises(ValidationError) as excinfo:
        UserRegister(**data)
    assert "Password must contain at least one uppercase letter" in str(excinfo.value)

def test_password_validation_missing_lower():
    # Passwords must contain a lowercase letter
    data = {
        "email": "valid_user@example.com",
        "password": "SECUREPASSWORD123!",
        "full_name": "Test User"
    }
    with pytest.raises(ValidationError) as excinfo:
        UserRegister(**data)
    assert "Password must contain at least one lowercase letter" in str(excinfo.value)

def test_password_validation_missing_digit():
    # Passwords must contain a digit
    data = {
        "email": "valid_user@example.com",
        "password": "SecurePassword!",
        "full_name": "Test User"
    }
    with pytest.raises(ValidationError) as excinfo:
        UserRegister(**data)
    assert "Password must contain at least one digit" in str(excinfo.value)

def test_password_validation_missing_special():
    # Passwords must contain a special character
    data = {
        "email": "valid_user@example.com",
        "password": "SecurePassword123",
        "full_name": "Test User"
    }
    with pytest.raises(ValidationError) as excinfo:
        UserRegister(**data)
    assert "Password must contain at least one special character" in str(excinfo.value)

def test_reset_password_validation():
    # The new password field in ResetPasswordRequest should follow the same rules
    data = {
        "email": "valid_user@example.com",
        "otp": "123456",
        "new_password": "weak"
    }
    with pytest.raises(ValidationError) as excinfo:
        ResetPasswordRequest(**data)
    assert "Password must be at least 8 characters long" in str(excinfo.value)
