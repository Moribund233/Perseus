"""
核心常量模块

定义项目中使用的共享常量
"""

# 仓库成员角色优先级定义
# 数值越高，权限越大
ROLE_PRIORITY = {
    "owner": 4,
    "admin": 3,
    "developer": 2,
    "readonly": 1
}

# 有效的角色列表
VALID_ROLES = list(ROLE_PRIORITY.keys())
