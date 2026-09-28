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
    # =========================================================
    # 实时协作 / 聊天
    # =========================================================
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
    "room_already_exists": {
        LOCALE_ZH: "该仓库已有关联房间",
        LOCALE_EN: "Room already exists for this repository",
    },
    "room_invalid_role": {
        LOCALE_ZH: "无效的角色",
        LOCALE_EN: "Invalid role",
    },
    "room_member_not_found": {
        LOCALE_ZH: "成员不存在",
        LOCALE_EN: "Member not found",
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

    # =========================================================
    # 应用管理 / 配置
    # =========================================================
    "app_admin_or_debug_required": {
        LOCALE_ZH: "该操作需要管理员权限或调试模式",
        LOCALE_EN: "This operation requires admin privileges or debug mode",
    },
    "app_local_auth_required": {
        LOCALE_ZH: "该操作需要本地认证或调试模式",
        LOCALE_EN: "This operation requires local authentication or debug mode",
    },
    "app_invalid_date_format": {
        LOCALE_ZH: "日期格式无效，应为 YYYY-MM-DD",
        LOCALE_EN: "Invalid date format. Expected YYYY-MM-DD",
    },
    "app_invalid_retention_days": {
        LOCALE_ZH: "保留天数必须大于等于 1",
        LOCALE_EN: "Retention days must be at least 1",
    },
    "app_restart_failed": {
        LOCALE_ZH: "重启失败",
        LOCALE_EN: "Failed to restart the application",
    },
    "app_log_read_failed": {
        LOCALE_ZH: "读取日志文件失败",
        LOCALE_EN: "Failed to read log files",
    },
    "config_debug_or_admin_required": {
        LOCALE_ZH: "该操作需要调试模式或管理员权限",
        LOCALE_EN: "This operation requires debug mode or admin privileges",
    },
    "config_validation_failed": {
        LOCALE_ZH: "配置验证失败",
        LOCALE_EN: "Configuration validation failed",
    },

    # =========================================================
    # 用户 / 认证 / OAuth / 通知
    # =========================================================
    "user_not_found": {
        LOCALE_ZH: "用户不存在",
        LOCALE_EN: "User not found",
    },
    "user_not_found_inactive": {
        LOCALE_ZH: "用户不存在或已禁用",
        LOCALE_EN: "User not found or inactive",
    },
    "user_update_forbidden": {
        LOCALE_ZH: "没有权限更新该用户",
        LOCALE_EN: "You don't have permission to update this user",
    },
    "user_credentials_required": {
        LOCALE_ZH: "用户名与密码不能为空",
        LOCALE_EN: "Username and password are required",
    },
    "user_passwords_required": {
        LOCALE_ZH: "旧密码与新密码不能为空",
        LOCALE_EN: "Old password and new password are required",
    },
    "user_password_too_short": {
        LOCALE_ZH: "新密码长度不能少于 6 个字符",
        LOCALE_EN: "New password must be at least 6 characters",
    },
    "avatar_not_found": {
        LOCALE_ZH: "头像不存在",
        LOCALE_EN: "Avatar not found",
    },
    "avatar_invalid_format": {
        LOCALE_ZH: "头像图片格式不支持",
        LOCALE_EN: "Invalid image format",
    },
    "avatar_too_large": {
        LOCALE_ZH: "头像文件过大",
        LOCALE_EN: "Avatar file is too large",
    },
    "username_already_exists": {
        LOCALE_ZH: "用户名已存在",
        LOCALE_EN: "Username already exists",
    },
    "email_already_exists": {
        LOCALE_ZH: "邮箱已被使用",
        LOCALE_EN: "Email already exists",
    },
    "invalid_credentials": {
        LOCALE_ZH: "用户名或密码错误",
        LOCALE_EN: "Invalid username or password",
    },
    "invalid_old_password": {
        LOCALE_ZH: "原密码错误",
        LOCALE_EN: "Invalid old password",
    },
    "invalid_refresh_token": {
        LOCALE_ZH: "刷新令牌无效或已过期",
        LOCALE_EN: "Invalid or expired refresh token",
    },
    "oauth_invalid_state": {
        LOCALE_ZH: "OAuth 状态无效或已过期",
        LOCALE_EN: "Invalid or expired OAuth state",
    },
    "oauth_no_matching_user": {
        LOCALE_ZH: "关联的 OAuth 账号没有匹配的用户",
        LOCALE_EN: "Linked OAuth account has no matching user",
    },
    "oauth_account_not_found": {
        LOCALE_ZH: "未找到关联的第三方账号",
        LOCALE_EN: "Linked account not found",
    },
    "notification_not_found": {
        LOCALE_ZH: "通知不存在",
        LOCALE_EN: "Notification not found",
    },

    # =========================================================
    # 仓库 / 分支 / 提交 / 文件浏览
    # =========================================================
    "repository_not_found": {
        LOCALE_ZH: "仓库不存在",
        LOCALE_EN: "Repository not found",
    },
    "repository_not_found_on_disk": {
        LOCALE_ZH: "仓库物理目录不存在",
        LOCALE_EN: "Repository not found on disk",
    },
    "repository_open_failed": {
        LOCALE_ZH: "打开仓库失败",
        LOCALE_EN: "Failed to open repository",
    },
    "repository_access_denied": {
        LOCALE_ZH: "没有该仓库的访问权限",
        LOCALE_EN: "You do not have access to this repository",
    },
    "repository_required_fields": {
        LOCALE_ZH: "名称、路径和所有者不能为空",
        LOCALE_EN: "Name, path and owner_id are required",
    },
    "repository_path_already_exists": {
        LOCALE_ZH: "仓库路径已存在",
        LOCALE_EN: "Repository path already exists",
    },
    "repository_already_starred": {
        LOCALE_ZH: "仓库已被标星",
        LOCALE_EN: "Repository already starred",
    },
    "repository_not_starred": {
        LOCALE_ZH: "仓库未被标星",
        LOCALE_EN: "Repository is not starred",
    },
    "source_repository_not_found": {
        LOCALE_ZH: "源仓库不存在",
        LOCALE_EN: "Source repository not found",
    },
    "repo_not_a_fork": {
        LOCALE_ZH: "该仓库不是 Fork 仓库",
        LOCALE_EN: "This repository is not a fork",
    },
    "fork_not_authorized": {
        LOCALE_ZH: "没有权限 Fork 该仓库",
        LOCALE_EN: "Not authorized to fork this repository",
    },
    "fork_already_exists": {
        LOCALE_ZH: "您已将该仓库 Fork 到其他位置",
        LOCALE_EN: "You have already forked this repository",
    },
    "fork_failed": {
        LOCALE_ZH: "Fork 仓库失败",
        LOCALE_EN: "Failed to fork repository",
    },
    "fork_sync_not_authorized": {
        LOCALE_ZH: "没有权限同步该仓库",
        LOCALE_EN: "Not authorized to sync this repository",
    },
    "fork_sync_failed": {
        LOCALE_ZH: "同步 Fork 仓库失败",
        LOCALE_EN: "Failed to sync forked repository",
    },
    "repo_has_no_commits": {
        LOCALE_ZH: "该仓库没有提交记录",
        LOCALE_EN: "No commits found in this repository",
    },
    "branch_not_found": {
        LOCALE_ZH: "分支不存在",
        LOCALE_EN: "Branch not found",
    },
    "branch_name_required": {
        LOCALE_ZH: "分支名称不能为空",
        LOCALE_EN: "Branch name is required",
    },
    "branch_already_exists": {
        LOCALE_ZH: "分支已存在",
        LOCALE_EN: "Branch already exists",
    },
    "branch_delete_default_forbidden": {
        LOCALE_ZH: "不能删除默认分支",
        LOCALE_EN: "Cannot delete the default branch",
    },
    "branch_repo_mismatch": {
        LOCALE_ZH: "该分支不属于此仓库",
        LOCALE_EN: "Branch does not belong to this repository",
    },
    "default_branch_not_found": {
        LOCALE_ZH: "默认分支不存在",
        LOCALE_EN: "Default branch not found",
    },
    "branch_ref_not_found": {
        LOCALE_ZH: "分支引用不存在",
        LOCALE_EN: "Branch ref not found",
    },
    "branch_has_no_commits": {
        LOCALE_ZH: "该分支没有提交记录",
        LOCALE_EN: "No commits found in this branch",
    },
    "commit_not_found": {
        LOCALE_ZH: "提交不存在",
        LOCALE_EN: "Commit not found",
    },
    "commit_field_required": {
        LOCALE_ZH: "字段不能为空",
        LOCALE_EN: "Field is required",
    },
    "commit_hash_already_exists": {
        LOCALE_ZH: "提交哈希已存在",
        LOCALE_EN: "Commit hash already exists",
    },
    "path_required": {
        LOCALE_ZH: "路径不能为空",
        LOCALE_EN: "Path is required",
    },
    "path_not_found": {
        LOCALE_ZH: "路径不存在",
        LOCALE_EN: "Path not found",
    },
    "path_is_directory": {
        LOCALE_ZH: "该路径是目录而非文件",
        LOCALE_EN: "The path is a directory, not a file",
    },
    "path_not_directory": {
        LOCALE_ZH: "该路径不是目录",
        LOCALE_EN: "The path is not a directory",
    },
    "file_invalid": {
        LOCALE_ZH: "不是有效的文件",
        LOCALE_EN: "Not a valid file",
    },
    "file_not_found": {
        LOCALE_ZH: "文件不存在",
        LOCALE_EN: "File not found",
    },
    "head_commit_required": {
        LOCALE_ZH: "需要提供 HEAD 提交",
        LOCALE_EN: "Head commit is required",
    },
    "base_ref_not_found": {
        LOCALE_ZH: "基础引用不存在",
        LOCALE_EN: "Base ref not found",
    },

    # =========================================================
    # 成员 / 标签 / SSH 密钥
    # =========================================================
    "member_not_found": {
        LOCALE_ZH: "仓库中不存在该成员",
        LOCALE_EN: "Member not found in this repository",
    },
    "member_user_id_required": {
        LOCALE_ZH: "用户 ID 不能为空",
        LOCALE_EN: "User ID is required",
    },
    "member_already_exists": {
        LOCALE_ZH: "该用户已是仓库成员",
        LOCALE_EN: "User is already a member of this repository",
    },
    "member_invalid_role": {
        LOCALE_ZH: "角色无效",
        LOCALE_EN: "Invalid role",
    },
    "member_remove_owner_forbidden": {
        LOCALE_ZH: "不能移除仓库所有者",
        LOCALE_EN: "Cannot remove the repository owner",
    },
    "member_deactivate_owner_forbidden": {
        LOCALE_ZH: "不能停用仓库所有者",
        LOCALE_EN: "Cannot deactivate the repository owner",
    },
    "label_not_found": {
        LOCALE_ZH: "标签不存在",
        LOCALE_EN: "Label not found",
    },
    "label_name_required": {
        LOCALE_ZH: "标签名称不能为空",
        LOCALE_EN: "Label name is required",
    },
    "label_invalid_color": {
        LOCALE_ZH: "无效的颜色格式",
        LOCALE_EN: "Invalid color format",
    },
    "label_already_exists": {
        LOCALE_ZH: "标签已存在",
        LOCALE_EN: "Label already exists",
    },
    "label_already_added": {
        LOCALE_ZH: "标签已添加到该 Issue",
        LOCALE_EN: "Label already added to this issue",
    },
    "label_not_in_issue": {
        LOCALE_ZH: "该 Issue 中不存在此标签",
        LOCALE_EN: "Label not found in this issue",
    },
    "ssh_key_not_found": {
        LOCALE_ZH: "SSH 密钥不存在",
        LOCALE_EN: "SSH key not found",
    },
    "ssh_key_invalid_format": {
        LOCALE_ZH: "无效的 SSH 密钥格式",
        LOCALE_EN: "Invalid SSH key format",
    },
    "ssh_key_already_exists": {
        LOCALE_ZH: "SSH 密钥已存在",
        LOCALE_EN: "SSH key already exists",
    },
    "ssh_key_delete_forbidden": {
        LOCALE_ZH: "没有权限删除该 SSH 密钥",
        LOCALE_EN: "You don't have permission to delete this key",
    },

    # =========================================================
    # Issue / Pull Request
    # =========================================================
    "issue_not_found": {
        LOCALE_ZH: "Issue 不存在",
        LOCALE_EN: "Issue not found",
    },
    "issue_title_required": {
        LOCALE_ZH: "标题不能为空",
        LOCALE_EN: "Title is required",
    },
    "issue_invalid_priority": {
        LOCALE_ZH: "无效的优先级",
        LOCALE_EN: "Invalid priority",
    },
    "issue_already_closed": {
        LOCALE_ZH: "Issue 已关闭",
        LOCALE_EN: "Issue is already closed",
    },
    "issue_already_open": {
        LOCALE_ZH: "Issue 已打开",
        LOCALE_EN: "Issue is already open",
    },
    "issue_comment_required": {
        LOCALE_ZH: "评论内容不能为空",
        LOCALE_EN: "Comment content is required",
    },
    "pr_not_found": {
        LOCALE_ZH: "Pull Request 不存在",
        LOCALE_EN: "Pull request not found",
    },
    "pr_title_required": {
        LOCALE_ZH: "标题不能为空",
        LOCALE_EN: "Title is required",
    },
    "pr_branches_same": {
        LOCALE_ZH: "源分支与目标分支不能相同",
        LOCALE_EN: "Source and target branches cannot be the same",
    },
    "pr_not_draft": {
        LOCALE_ZH: "该 Pull Request 不是草稿",
        LOCALE_EN: "Pull request is not a draft",
    },
    "pr_invalid_status": {
        LOCALE_ZH: "Pull Request 已处于该状态",
        LOCALE_EN: "Pull request is already in this status",
    },
    "pr_invalid_status_for_update": {
        LOCALE_ZH: "当前状态的 Pull Request 不能更新",
        LOCALE_EN: "Cannot update pull request in its current status",
    },
    "pr_invalid_status_for_merge": {
        LOCALE_ZH: "当前状态的 Pull Request 不能合并",
        LOCALE_EN: "Cannot merge pull request in its current status",
    },
    "pr_merger_not_found": {
        LOCALE_ZH: "合并用户不存在",
        LOCALE_EN: "Merger not found",
    },
    "pr_merge_forbidden": {
        LOCALE_ZH: "没有权限合并该 Pull Request",
        LOCALE_EN: "You don't have permission to merge this pull request",
    },
    "pr_merge_conflict": {
        LOCALE_ZH: "存在合并冲突，请先解决冲突后再合并",
        LOCALE_EN: "Merge conflicts detected. Resolve conflicts before merging",
    },
    "pr_invalid_merge_method": {
        LOCALE_ZH: "无效的合并方式",
        LOCALE_EN: "Invalid merge method",
    },
    "pr_merge_failed": {
        LOCALE_ZH: "合并操作失败",
        LOCALE_EN: "Merge operation failed",
    },
    "pr_comment_required": {
        LOCALE_ZH: "评论内容不能为空",
        LOCALE_EN: "Comment content is required",
    },
    "pr_invalid_parent_comment": {
        LOCALE_ZH: "无效的父评论",
        LOCALE_EN: "Invalid parent comment",
    },
    "pr_invalid_review_status": {
        LOCALE_ZH: "无效的评审状态",
        LOCALE_EN: "Invalid review status",
    },
    "pr_diff_failed": {
        LOCALE_ZH: "获取 PR 差异失败",
        LOCALE_EN: "Failed to get PR diff",
    },
    "pr_base_branch_not_found": {
        LOCALE_ZH: "PR 目标分支不存在",
        LOCALE_EN: "PR base branch not found",
    },
    "pr_source_branch_not_found": {
        LOCALE_ZH: "PR 源分支不存在",
        LOCALE_EN: "PR source branch not found",
    },
    "pr_file_diff_failed": {
        LOCALE_ZH: "获取文件差异失败",
        LOCALE_EN: "Failed to get file diff",
    },

    # =========================================================
    # Release / 附件（聊天 / Release）
    # =========================================================
    "release_not_found": {
        LOCALE_ZH: "Release 不存在",
        LOCALE_EN: "Release not found",
    },
    "release_tag_not_found": {
        LOCALE_ZH: "该标签的 Release 不存在",
        LOCALE_EN: "Release with this tag not found",
    },
    "release_tag_already_exists": {
        LOCALE_ZH: "该标签的 Release 已存在",
        LOCALE_EN: "Release with this tag already exists",
    },
    "release_head_commit_failed": {
        LOCALE_ZH: "获取 HEAD 提交哈希失败",
        LOCALE_EN: "Failed to get HEAD commit hash",
    },
    "release_update_forbidden": {
        LOCALE_ZH: "没有权限更新该 Release",
        LOCALE_EN: "Not authorized to update this release",
    },
    "release_delete_forbidden": {
        LOCALE_ZH: "没有权限删除该 Release",
        LOCALE_EN: "Not authorized to delete this release",
    },
    "release_asset_add_forbidden": {
        LOCALE_ZH: "没有权限向该 Release 添加附件",
        LOCALE_EN: "Not authorized to add assets to this release",
    },
    "release_asset_delete_forbidden": {
        LOCALE_ZH: "没有权限删除该 Release 的附件",
        LOCALE_EN: "Not authorized to delete assets from this release",
    },
    "release_tag_create_failed": {
        LOCALE_ZH: "创建 Git 标签失败",
        LOCALE_EN: "Failed to create tag",
    },
    "release_tag_hash_failed": {
        LOCALE_ZH: "获取标签哈希失败",
        LOCALE_EN: "Failed to get tag hash",
    },
    "release_tag_delete_failed": {
        LOCALE_ZH: "删除 Git 标签失败",
        LOCALE_EN: "Failed to delete tag",
    },
    "release_tag_list_failed": {
        LOCALE_ZH: "列出 Git 标签失败",
        LOCALE_EN: "Failed to list tags",
    },
    "release_tag_get_failed": {
        LOCALE_ZH: "获取 Git 标签失败",
        LOCALE_EN: "Failed to get tag",
    },
    "asset_not_found": {
        LOCALE_ZH: "附件不存在",
        LOCALE_EN: "Asset not found",
    },
    "asset_too_large": {
        LOCALE_ZH: "附件大小不能超过 50MB",
        LOCALE_EN: "Attachment size cannot exceed 50MB",
    },
    "attachment_content_empty": {
        LOCALE_ZH: "附件内容为空",
        LOCALE_EN: "Attachment content is empty",
    },
    "attachment_not_found": {
        LOCALE_ZH: "附件不存在",
        LOCALE_EN: "Attachment not found",
    },
    "attachment_too_large": {
        LOCALE_ZH: "附件大小不能超过 20MB",
        LOCALE_EN: "Attachment size cannot exceed 20MB",
    },

    # =========================================================
    # Git 浏览器（Blame / 提交图 / 对比）
    # =========================================================
    "blame_failed": {
        LOCALE_ZH: "获取文件追溯信息失败",
        LOCALE_EN: "Failed to get file blame",
    },

    # =========================================================
    # Tag 管理
    # =========================================================
    "tag_not_found": {
        LOCALE_ZH: "标签不存在",
        LOCALE_EN: "Tag not found",
    },
    "tag_no_target": {
        LOCALE_ZH: "仓库没有可打标签的提交",
        LOCALE_EN: "Repository has no commit to tag",
    },
    "tag_list_failed": {
        LOCALE_ZH: "列出标签失败",
        LOCALE_EN: "Failed to list tags",
    },
    "tag_get_failed": {
        LOCALE_ZH: "获取标签失败",
        LOCALE_EN: "Failed to get tag",
    },
    "tag_create_failed": {
        LOCALE_ZH: "创建标签失败",
        LOCALE_EN: "Failed to create tag",
    },
    "tag_delete_failed": {
        LOCALE_ZH: "删除标签失败",
        LOCALE_EN: "Failed to delete tag",
    },

    # =========================================================
    # Build / Webhook
    # =========================================================
    "build_not_found": {
        LOCALE_ZH: "构建记录不存在",
        LOCALE_EN: "Build not found",
    },
    "webhook_not_found": {
        LOCALE_ZH: "Webhook 不存在",
        LOCALE_EN: "Webhook not found",
    },
    "webhook_view_forbidden": {
        LOCALE_ZH: "没有权限查看 Webhook",
        LOCALE_EN: "Not authorized to view webhook",
    },
    "webhook_create_forbidden": {
        LOCALE_ZH: "没有权限创建 Webhook",
        LOCALE_EN: "Not authorized to create webhook",
    },
    "webhook_update_forbidden": {
        LOCALE_ZH: "没有权限更新 Webhook",
        LOCALE_EN: "Not authorized to update webhook",
    },
    "webhook_delete_forbidden": {
        LOCALE_ZH: "没有权限删除 Webhook",
        LOCALE_EN: "Not authorized to delete webhook",
    },
    "webhook_test_forbidden": {
        LOCALE_ZH: "没有权限测试 Webhook",
        LOCALE_EN: "Not authorized to test webhook",
    },
    "webhook_invalid_url": {
        LOCALE_ZH: "无效的 URL",
        LOCALE_EN: "Invalid URL",
    },
    "webhook_events_required": {
        LOCALE_ZH: "至少需要指定一个事件",
        LOCALE_EN: "At least one event must be specified",
    },
    "webhook_invalid_event": {
        LOCALE_ZH: "无效的事件类型",
        LOCALE_EN: "Invalid event",
    },
    "webhook_invalid_content_type": {
        LOCALE_ZH: "无效的 content_type",
        LOCALE_EN: "Invalid content_type",
    },
    "webhook_delivery_not_found": {
        LOCALE_ZH: "投递记录不存在",
        LOCALE_EN: "Delivery not found",
    },
    "webhook_delivery_view_forbidden": {
        LOCALE_ZH: "没有权限查看投递记录",
        LOCALE_EN: "Not authorized to view deliveries",
    },

    # =========================================================
    # 协作编辑 (collab gateway)
    # =========================================================
    "collab_invalid_dockey": {
        LOCALE_ZH: "docKey 格式非法, 应为 repository_id:branch:path",
        LOCALE_EN: "Invalid docKey format. Expected repository_id:branch:path",
    },
    "collab_invalid_repository_id": {
        LOCALE_ZH: "docKey 中 repository_id 非法",
        LOCALE_EN: "Invalid repository_id in docKey",
    },
    "collab_dockey_missing_parts": {
        LOCALE_ZH: "docKey 中 branch/path 不能为空",
        LOCALE_EN: "docKey branch/path cannot be empty",
    },
    "collab_invalid_internal_secret": {
        LOCALE_ZH: "内部密钥校验失败",
        LOCALE_EN: "Invalid internal secret",
    },
    "collab_repository_access_denied": {
        LOCALE_ZH: "没有该仓库的访问权限",
        LOCALE_EN: "No access to this repository",
    },
    "collab_repository_write_denied": {
        LOCALE_ZH: "没有该仓库的写入权限",
        LOCALE_EN: "No write access to this repository",
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