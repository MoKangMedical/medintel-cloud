"""
统一认证 & 权限管理
"""

from .jwt import create_access_token, verify_token, get_current_user
from .rbac import Role, Permission, require_permission

__all__ = [
    "create_access_token", "verify_token", "get_current_user",
    "Role", "Permission", "require_permission",
]
