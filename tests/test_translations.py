"""Test that all translation keys are present in EN and DE."""

import json
from pathlib import Path

import pytest

INTEGRATION_DIR = (
    Path(__file__).resolve().parent.parent / "custom_components" / "oraclecloud"
)
STRINGS_FILE = INTEGRATION_DIR / "strings.json"
TRANSLATIONS_DIR = INTEGRATION_DIR / "translations"
REQUIRED_LANGUAGES = ["en", "de"]


def _flatten_keys(data: dict, prefix: str = "") -> set[str]:
    """Recursively flatten JSON keys into dot-separated paths."""
    keys: set[str] = set()
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys.update(_flatten_keys(value, full_key))
        else:
            keys.add(full_key)
    return keys


def test_strings_json_exists() -> None:
    """Verify strings.json exists."""
    assert STRINGS_FILE.exists(), f"strings.json not found at {STRINGS_FILE}"


@pytest.mark.parametrize("lang", REQUIRED_LANGUAGES)
def test_translation_file_exists(lang: str) -> None:
    """Verify required translation files exist."""
    path = TRANSLATIONS_DIR / f"{lang}.json"
    assert path.exists(), f"Translation file {lang}.json is missing at {path}"


def test_translation_files_parity() -> None:
    """Ensure every key in strings.json, en.json, and de.json matches exactly."""
    with open(STRINGS_FILE, encoding="utf-8") as f:
        strings_data = json.load(f)
    strings_keys = _flatten_keys(strings_data)

    for lang in REQUIRED_LANGUAGES:
        translation_file = TRANSLATIONS_DIR / f"{lang}.json"
        with open(translation_file, encoding="utf-8") as f:
            translation_data = json.load(f)
        translation_keys = _flatten_keys(translation_data)

        # Check for keys in strings.json but missing in translation
        missing_in_translation = strings_keys - translation_keys
        assert (
            not missing_in_translation
        ), f"Keys in strings.json missing in {lang}.json: {sorted(missing_in_translation)}"

        # Check for extra keys in translation not in strings.json
        extra_in_translation = translation_keys - strings_keys
        assert (
            not extra_in_translation
        ), f"Extra keys in {lang}.json not in strings.json: {sorted(extra_in_translation)}"


def test_translation_values_not_empty() -> None:
    """Ensure no translation value is empty or remains as a placeholder."""
    for lang in [*REQUIRED_LANGUAGES, "strings"]:
        if lang == "strings":
            file_path = STRINGS_FILE
        else:
            file_path = TRANSLATIONS_DIR / f"{lang}.json"

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        def _check_values(data: dict, prefix: str = "") -> list[str]:
            invalid: list[str] = []
            for key, value in data.items():
                full_key = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    invalid.extend(_check_values(value, full_key))
                elif isinstance(value, str):
                    if not value.strip():
                        invalid.append(f"{full_key} (empty)")
                else:
                    invalid.append(f"{full_key} (not a string/dict)")
            return invalid

        invalid_keys = _check_values(data)
        assert (
            not invalid_keys
        ), f"Invalid translation values in {file_path.name}: {sorted(invalid_keys)}"
