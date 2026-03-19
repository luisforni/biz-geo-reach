"""Unit tests for the phone number normalizer."""

import pytest

from app.domain.phone.normalizer import is_valid_phone, normalize_phone

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("+5491112345678", "+5491112345678"),
        ("+54 9 11 1234-5678", "+5491112345678"),
        ("+54 11 4123-4567", "+541141234567"),
        ("  +5491112345678  ", "+5491112345678"),
        ("+54-9-11-1234-5678", "+5491112345678"),
    ],
)
def test_normalize_valid_phones(raw: str, expected: str):
    assert normalize_phone(raw) == expected

@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "abc",
        "0000000",
        "123",
        "not-a-phone",
    ],
)
def test_normalize_invalid_phones_return_none(raw: str):
    assert normalize_phone(raw) is None

def test_normalize_none_input():
    assert normalize_phone("") is None

def test_is_valid_phone_true():
    assert is_valid_phone("+5491112345678")

def test_is_valid_phone_false():
    assert not is_valid_phone("invalid")
    assert not is_valid_phone("")
    assert not is_valid_phone("000")

def test_different_default_region():
    assert normalize_phone("+34 91 123 45 67", default_region="ES") is not None
