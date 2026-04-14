"""
RBAC 权限控制
"""

from enum import Enum
from functools import wraps
from fastapi import HTTPException, status


class Role(str, Enum):
    ADMIN = "admin"
    PHYSICIAN = "physician"
    RESEARCHER = "researcher"
    PHARMACIST = "pharmacist"
    ANALYST = "analyst"
    VIEWER = "viewer"


class Permission(str, Enum):
    # 患者数据
    READ_PATIENT = "read:patient"
    WRITE_PATIENT = "write:patient"
    # 药物发现
    RUN_DISCOVERY = "run:discovery"
    VIEW_MOLECULES = "view:molecules"
    # 临床
    VIEW_EVIDENCE = "view:evidence"
    RUN_DIAGNOSIS = "run:diagnosis"
    # 管理
    MANAGE_USERS = "manage:users"
    MANAGE_SYSTEM = "manage:system"


ROLE_PERMISSIONS: dict[Role, list[Permission]] = {
    Role.ADMIN: list(Permission),
    Role.PHYSICIAN: [
        Permission.READ_PATIENT, Permission.WRITE_PATIENT,
        Permission.RUN_DIAGNOSIS, Permission.VIEW_EVIDENCE,
    ],
    Role.RESEARCHER: [
        Permission.READ_PATIENT, Permission.RUN_DISCOVERY,
        Permission.VIEW_MOLECULES, Permission.VIEW_EVIDENCE,
    ],
    Role.PHARMACIST: [
        Permission.READ_PATIENT, Permission.VIEW_MOLECULES,
        Permission.VIEW_EVIDENCE,
    ],
    Role.ANALYST: [
        Permission.READ_PATIENT, Permission.VIEW_MOLECULES,
        Permission.VIEW_EVIDENCE,
    ],
    Role.VIEWER: [
        Permission.READ_PATIENT, Permission.VIEW_EVIDENCE,
    ],
}


def require_permission(permission: Permission):
    """装饰器：检查用户权限"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: dict = None, **kwargs):
            user_role = Role(current_user.get("role", "viewer"))
            if permission not in ROLE_PERMISSIONS.get(user_role, []):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission.value}",
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator
