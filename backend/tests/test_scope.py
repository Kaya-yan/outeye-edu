"""
知识库三层权限作用域测试（TDD）

作用域：system（系统种子，全员可见）| organization（组织共享）| private（仅所有者）
"""

import pytest

from app.core.scope import (
    SCOPE_SYSTEM,
    SCOPE_ORGANIZATION,
    SCOPE_PRIVATE,
    can_access,
    build_upload_scope,
)


class TestScopeAccess:
    """作用域访问判定测试"""

    def test_system_visible_to_all(self):
        """system 作用域对所有用户可见"""
        payload = {"scope": SCOPE_SYSTEM}
        user = {"user_id": "u1", "org_id": None}
        assert can_access(payload, user) is True

    def test_private_visible_to_owner_only(self):
        """private 作用域仅所有者可见"""
        payload = {"scope": SCOPE_PRIVATE, "owner_id": "u1"}
        owner = {"user_id": "u1"}
        other = {"user_id": "u2"}

        assert can_access(payload, owner) is True
        assert can_access(payload, other) is False

    def test_organization_visible_to_same_org(self):
        """organization 作用域对同组织成员可见"""
        payload = {"scope": SCOPE_ORGANIZATION, "org_id": "org-1"}
        same_org = {"user_id": "u1", "org_id": "org-1"}
        diff_org = {"user_id": "u2", "org_id": "org-2"}
        no_org = {"user_id": "u3"}

        assert can_access(payload, same_org) is True
        assert can_access(payload, diff_org) is False
        assert can_access(payload, no_org) is False

    def test_missing_scope_defaults_to_private(self):
        """缺少 scope 字段时默认 private（向后兼容，最保守）"""
        payload = {"owner_id": "u1"}
        owner = {"user_id": "u1"}
        other = {"user_id": "u2"}

        assert can_access(payload, owner) is True
        assert can_access(payload, other) is False


class TestBuildUploadScope:
    """上传作用域构建测试"""

    def test_regular_user_upload_is_private(self):
        """普通用户上传默认 private，owner 为自己"""
        user = {"user_id": "u1"}
        result = build_upload_scope(user)

        assert result["scope"] == SCOPE_PRIVATE
        assert result["owner_id"] == "u1"

    def test_admin_system_seed(self):
        """管理员可上传 system 作用域"""
        user = {"user_id": "admin", "is_admin": True}
        result = build_upload_scope(user, scope=SCOPE_SYSTEM)

        assert result["scope"] == SCOPE_SYSTEM
        assert result["owner_id"] == "admin"
