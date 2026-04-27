"""数字分身子模块"""
from .engine import DigitalTwinEngine, TwinResponse
from .personality import PersonalityManager, PersonalityProfile
from .memory import HierarchicalMemory
from .roles import get_role, list_roles, RoleConfig

__all__ = ["DigitalTwinEngine", "TwinResponse", "PersonalityManager", "PersonalityProfile",
           "HierarchicalMemory", "get_role", "list_roles", "RoleConfig"]
