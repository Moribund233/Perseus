"""
后端国际化

根据 `Accept-Language` 请求头将业务错误消息翻译为对应语言。
默认语言为中文 (zh)，次选英文 (en)。

错误消息通过稳定的 `error_code`（如 `room_not_found`）与语言关联；
未携带 `error_code` 的异常沿用其原始 `detail`，保证向后兼容。
"""
from typing import Optional

# 默认语言与支持语言
LOCALE_ZH = "zh"
LOCALE_EN = "en"
DEFAULT_LOCALE = LOCALE_ZH
SUPPORTED_LOCALES = {LOCALE_ZH, LOCALE_EN}

# 错误码 → 各语言消息映射
ERROR_MESSAGES: dict[str, dict[str, str]] = {
    # 实时协作 / 聊天
    "room_not_found": {
        LOCALE_ZH: "房间不存在",
        LOCALE_EN: "Room not found",
    },
    "room_closed": {
        LOCALE_ZH: "房间已关闭",
        LOCALE_EN: "Room has been closed",
    },
    "room_not_member": {
        LOCALE_ZH: "你不是该房间的成员",
        LOCALE_EN: "You are not a member of this room",
    },
    "message_content_required": {
        LOCALE_ZH: "消息内容不能为空",
        LOCALE_EN: "Message content cannot be empty",
    },
    "message_not_found": {
        LOCALE_ZH: "消息不存在",
        LOCALE_EN: "Message not found",
    },
    "message_edit_own_only": {
        LOCALE_ZH: "只能编辑自己的消息",
        LOCALE_EN: "Only your own messages can be edited",
    },
    "message_delete_forbidden": {
        LOCALE_ZH: "没有权限删除此消息",
        LOCALE_EN: "You do not have permission to delete this message",
    },
    "message_room_membership": {
        LOCALE_ZH: "你不是该房间的成员",
        LOCALE_EN: "You are not a member of this room",
    },
    "invalid_emoji": {
        LOCALE_ZH: "表情不合法",
        LOCALE_EN: "Invalid emoji",
    },
    "reaction_duplicate": {
        LOCALE_ZH: "你已回应过该表情",
        LOCALE_EN: "You have already reacted with this emoji",
    },
}


def get_error_message(
    error_code: Optional[str],
    locale: str,
    default: Optional[str] = None,
) -> str:
    """
    根据错误码与语言返回本地化错误消息.

    Args:
        error_code: 稳定错误码（不存在时为 None）
        locale: 请求目标语言（已归一化，如 "zh"、"en"）
        default: 未命中错误码时的回退消息（对应原 detail）

    Returns:
        str: 本地化错误消息
    """
    if error_code:
        mapping = ERROR_MESSAGES.get(error_code)
        if mapping:
            return mapping.get(locale, mapping.get(DEFAULT_LOCALE, ""))
    return default or ""


def normalize_locale(accept_language: Optional[str]) -> str:
    """
    从 `Accept-Language` 头解析目标语言（zh/en）.

    Args:
        accept_language: 请求头值，如 "zh-CN,zh;q=0.9,en;q=0.8"

    Returns:
        str: 归一化语言，默认 "zh"
    """
    if not accept_language:
        return DEFAULT_LOCALE

    candidates = [part.split(";")[0].strip().lower() for part in accept_language.split(",")]
    for candidate in candidates:
        base = candidate.split("-")[0]
        if base in SUPPORTED_LOCALES:
            return base
    return DEFAULT_LOCALE