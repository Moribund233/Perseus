import pytest

from core.i18n import (
    get_error_message,
    normalize_locale,
    ERROR_MESSAGES,
    LOCALE_ZH,
    LOCALE_EN,
)


def test_normalize_locale_zh():
    assert normalize_locale("zh-CN,zh;q=0.9,en;q=0.8") == "zh"


def test_normalize_locale_en():
    assert normalize_locale("en-US,en;q=0.9,zh;q=0.8") == "en"


def test_normalize_locale_missing_defaults_to_zh():
    assert normalize_locale(None) == "zh"
    assert normalize_locale("") == "zh"


def test_normalize_locale_unsupported_falls_back_to_zh():
    assert normalize_locale("ja-JP") == "zh"


def test_normalize_locale_prefers_first_supported():
    assert normalize_locale("fr-FR,en;q=0.9") == "en"


def test_get_error_message_zh():
    assert get_error_message("room_not_found", LOCALE_ZH) == "房间不存在"


def test_get_error_message_en():
    assert get_error_message("room_not_found", LOCALE_EN) == "Room not found"


def test_get_error_message_unknown_code_uses_default():
    assert get_error_message("no_such_code", LOCALE_ZH, default="fallback") == "fallback"


def test_get_error_message_none_code_returns_default():
    assert get_error_message(None, LOCALE_ZH, default="raw") == "raw"


def test_error_catalog_has_both_languages():
    for code, mapping in ERROR_MESSAGES.items():
        assert LOCALE_ZH in mapping, f"{code} missing zh"
        assert LOCALE_EN in mapping, f"{code} missing en"
