"""Phone number normalization utilities.

Handles common Argentine formats using the `phonenumbers` library:

  +54 9 11 1234-5678   → +5491112345678  (international + mobile indicator)
  +5491112345678       → +5491112345678  (already E.164)
  +54 11 4123-4567     → +541141234567   (Buenos Aires landline)
  0221-456-7890        → +5422145678900  (La Plata with area code)
  1112345678           → +5491112345678  (mobile, inferred AR)

Pattern: Strategy — the default_region parameter lets callers inject
a different parsing strategy without touching this module.
"""

import re

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat

def normalize_phone(raw: str, default_region: str = "AR") -> str | None:
    """Normalize a raw phone string to E.164 format.

    Args:
        raw: Any phone string (spaces, dashes, country code optional).
        default_region: ISO 3166-1 alpha-2 fallback region for parsing.

    Returns:
        E.164 string (e.g. "+5491112345678") if valid, else None.
    """
    if not raw or not raw.strip():
        return None

    cleaned = _clean_raw(raw)

    for candidate in (cleaned, f"+{cleaned.lstrip('+')}"):
        try:
            parsed = phonenumbers.parse(candidate, default_region)
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
        except NumberParseException:
            continue

    return None

def is_valid_phone(raw: str, default_region: str = "AR") -> bool:
    """Return True if the raw string produces a valid, normalizable phone."""
    return normalize_phone(raw, default_region) is not None

def _clean_raw(raw: str) -> str:
    """Strip whitespace and formatting chars; keep only digits and leading +."""
    return re.sub(r"[^\d+]", "", raw.strip())
