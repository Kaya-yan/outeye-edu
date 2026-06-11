"""
用户管理端点
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime

from app.core.database import get_async_db
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
)

router = APIRouter()


# Pydantic模型
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    institution: Optional[str] = None
    title: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    institution: Optional[str]
    title: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    institution: Optional[str] = None
    title: Optional[str] = None
    bio: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# 示例用户数据（实际应用中应从数据库获取）
# 密码已使用 bcrypt 哈希
SAMPLE_USERS = [
    {
        "id": "1",
        "email": "teacher@example.com",
        "hashed_password": get_password_hash("Teacher@123"),
        "full_name": "张老师",
        "institution": "山东大学翻译学院",
        "title": "副教授",
        "is_active": True,
        "created_at": datetime.fromisoformat("2026-01-01T00:00:00")
    },
    {
        "id": "2",
        "email": "student@example.com",
        "hashed_password": get_password_hash("Student@123"),
        "full_name": "李同学",
        "institution": "山东大学翻译学院",
        "title": "研究生",
        "is_active": True,
        "created_at": datetime.fromisoformat("2026-01-02T00:00:00")
    }
]


@router.post("/login", response_model=TokenResponse)
async def login(user_login: UserLogin):
    """用户登录"""
    for user in SAMPLE_USERS:
        if user["email"] == user_login.email:
            if not verify_password(user_login.password, user["hashed_password"]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                )
            access_token = create_access_token(
                data={"sub": user["id"], "email": user["email"]}
            )
            return TokenResponse(
                access_token=access_token,
                expires_in=7200
            )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
    )


@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """获取用户列表（需要认证）"""
    return [
        {k: v for k, v in user.items() if k != "hashed_password"}
        for user in SAMPLE_USERS[skip:skip + limit]
    ]


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """获取当前用户信息"""
    for user in SAMPLE_USERS:
        if user["id"] == current_user["user_id"]:
            return {k: v for k, v in user.items() if k != "hashed_password"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """获取单个用户（需要认证）"""
    for user in SAMPLE_USERS:
        if user["id"] == user_id:
            return {k: v for k, v in user.items() if k != "hashed_password"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )


@router.post("/", response_model=UserResponse)
async def create_user(
    user: UserCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """创建用户"""
    # 检查邮箱是否已存在
    for existing_user in SAMPLE_USERS:
        if existing_user["email"] == user.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    # 密码强度验证
    if len(user.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )

    new_user = {
        "id": str(len(SAMPLE_USERS) + 1),
        "email": user.email,
        "hashed_password": get_password_hash(user.password),
        "full_name": user.full_name,
        "institution": user.institution,
        "title": user.title,
        "is_active": True,
        "created_at": datetime.now()
    }
    SAMPLE_USERS.append(new_user)
    return {k: v for k, v in new_user.items() if k != "hashed_password"}


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """更新用户（需要认证，只能更新自己）"""
    if current_user["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )

    for user in SAMPLE_USERS:
        if user["id"] == user_id:
            if user_update.full_name:
                user["full_name"] = user_update.full_name
            if user_update.institution:
                user["institution"] = user_update.institution
            if user_update.title:
                user["title"] = user_update.title
            return {k: v for k, v in user.items() if k != "hashed_password"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """删除用户（需要认证，只能删除自己）"""
    if current_user["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user"
        )

    for i, user in enumerate(SAMPLE_USERS):
        if user["id"] == user_id:
            del SAMPLE_USERS[i]
            return {"message": "User deleted successfully"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )
