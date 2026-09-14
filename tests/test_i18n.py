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


def test_error_catalog_all_messages_nonempty():
    for code, mapping in ERROR_MESSAGES.items():
        assert mapping[LOCALE_ZH].strip() != "", f"{code} has empty zh message"
        assert mapping[LOCALE_EN].strip() != "", f"{code} has empty en message"


def test_error_catalog_biz_domains_covered():
    for code in (
        "repository_not_found",
        "repository_path_already_exists",
        "branch_not_found",
        "commit_not_found",
        "issue_not_found",
        "pr_not_found",
        "label_not_found",
        "member_not_found",
        "webhook_not_found",
        "webhook_invalid_url",
        "build_not_found",
        "release_not_found",
        "ssh_key_not_found",
        "notification_not_found",
        "user_not_found",
        "invalid_credentials",
        "invalid_refresh_token",
        "repository_access_denied",
        "pr_merge_conflict",
        "collab_invalid_dockey",
    ):
        assert code in ERROR_MESSAGES, f"{code} missing from error catalog"
        assert ERROR_MESSAGES[code][LOCALE_ZH]
        assert ERROR_MESSAGES[code][LOCALE_EN]


def test_get_error_message_domain_samples():
    samples = {
        ("repository_not_found", "zh"): "仓库不存在",
        ("repository_not_found", "en"): "Repository not found",
        ("webhook_invalid_url", "zh"): "无效的 URL",
        ("webhook_invalid_url", "en"): "Invalid URL",
        ("pr_not_found", "zh"): "Pull Request 不存在",
        ("pr_not_found", "en"): "Pull request not found",
        ("attachment_content_empty", "zh"): "附件内容为空",
        ("attachment_content_empty", "en"): "Attachment content is empty",
    }
    for (code, locale), expected in samples.items():
        assert get_error_message(code, locale) == expected, f"{code}/{locale}"


def test_exception_carries_error_code_for_translation():
    from core.exception import (
        NotFoundException,
        AuthorizationException,
        ConflictException,
        AuthenticationException,
        InvalidPathException,
        RepositoryNotFoundException,
        PathNotFoundException,
    )

    exception_types = [
        NotFoundException("仓库不存在", error_code="repository_not_found"),
        AuthorizationException("Permission Denied", error_code="repository_access_denied"),
        ConflictException("冲突", error_code="repository_path_already_exists"),
        AuthenticationException("auth failed", error_code="invalid_credentials"),
        InvalidPathException("invalid path", error_code="path_required"),
        RepositoryNotFoundException("not found", error_code="repository_not_found"),
        PathNotFoundException("not found", error_code="path_not_found"),
    ]
    for exc in exception_types:
        assert exc.error_code is not None
