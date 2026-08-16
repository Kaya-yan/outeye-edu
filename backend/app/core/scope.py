"""
知识库三层权限作用域

作用域层级：
- system：系统种子（官方知识），全员可见，永久保留
- organization：组织共享，同组织成员可见
- private：私有，仅所有者可见（默认）
"""

from typing import Dict, Any

SCOPE_SYSTEM = "system"
SCOPE_ORGANIZATION = "organization"
SCOPE_PRIVATE = "private"


def can_access(payload: Dict[str, Any], user: Dict[str, Any]) -> bool:
    """判定当前用户是否有权访问某条记录（按 payload 中的作用域字段）"""
    scope = payload.get("scope", SCOPE_PRIVATE)

    if scope == SCOPE_SYSTEM:
        return True

    if scope == SCOPE_PRIVATE:
        return payload.get("owner_id") == user.get("user_id")

    if scope == SCOPE_ORGANIZATION:
        user_org = user.get("org_id")
        return user_org is not None and payload.get("org_id") == user_org

    return False


def build_upload_scope(user: Dict[str, Any], scope: str = SCOPE_PRIVATE) -> Dict[str, Any]:
    """构建上传记录的作用域字段（写入 Qdrant payload）"""
    return {
        "scope": scope,
        "owner_id": user.get("user_id"),
    }
