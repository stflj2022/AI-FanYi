"""认证相关的 Pydantic schemas"""
from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict


class UserRegister(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    confirm_password: str = Field(..., description="确认密码")

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        values = info.data
        if 'password' in values and v != values['password']:
            raise ValueError('两次输入的密码不一致')
        return v


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserResponse(BaseModel):
    """用户响应"""
    id: str
    username: str
    email: str
    is_admin: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={uuid.UUID: lambda v: str(v)}
    )

    @classmethod
    def model_validate(cls, obj):
        """从数据库模型验证，自动转换 UUID"""
        if hasattr(obj, 'id') and isinstance(obj.id, uuid.UUID):
            obj_dict = {
                'id': str(obj.id),
                'username': obj.username,
                'email': obj.email,
                'is_admin': obj.is_admin,
                'is_active': obj.is_active,
                'created_at': obj.created_at,
                'updated_at': obj.updated_at,
            }
            return cls(**obj_dict)
        return super().model_validate(obj)


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # 秒
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """刷新 Token 请求"""
    refresh_token: str = Field(..., description="刷新 Token")


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=100, description="新密码")
