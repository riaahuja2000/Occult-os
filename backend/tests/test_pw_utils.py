import pytest
import os
import sys

# Mock env vars needed to import server.py before importing it
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

# Ensure backend directory is in the path so we can import from server
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server import hash_pw, verify_pw

def test_hash_pw_returns_non_empty_string():
    password = "my_secure_password"
    hashed = hash_pw(password)

    assert isinstance(hashed, str)
    assert len(hashed) > 0
    assert hashed != password

def test_verify_pw_correct_password():
    password = "my_secure_password"
    hashed = hash_pw(password)

    assert verify_pw(password, hashed) is True

def test_verify_pw_incorrect_password():
    password = "my_secure_password"
    hashed = hash_pw(password)

    assert verify_pw("wrong_password", hashed) is False

def test_verify_pw_invalid_hash():
    password = "my_secure_password"
    invalid_hash = "not_a_valid_bcrypt_hash"

    # Should not raise an exception, but return False according to verify_pw implementation
    assert verify_pw(password, invalid_hash) is False

def test_hash_and_verify_long_password():
    # Passwords longer than 72 bytes should be sliced properly by [:72] in both functions
    # Generate a password that is 100 characters long
    long_password = "a" * 100

    hashed = hash_pw(long_password)
    assert verify_pw(long_password, hashed) is True

    # Verify that it only checks the first 72 characters
    # (Since it truncates at 72, a password matching up to the 72nd char but different after will verify as True)
    another_long_password = "a" * 72 + "b" * 28
    assert verify_pw(another_long_password, hashed) is True

    # But one that differs within the first 72 characters should fail
    differing_early = "b" + "a" * 99
    assert verify_pw(differing_early, hashed) is False
