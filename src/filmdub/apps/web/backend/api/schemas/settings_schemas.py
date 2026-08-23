"""设置相关的 Pydantic schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
import uuid


class UserSettingsUpdate(BaseModel):
    """更新用户设置请求"""
    # 个人信息
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="用户名")
    email: Optional[str] = Field(None, max_length=255, description="邮箱")

    # 默认配置
    default_target_language: Optional[str] = Field(None, max_length=10, description="默认目标语言")
    default_video_quality: Optional[str] = Field(None, max_length=20, description="默认视频质量")
    default_subtitle_format: Optional[str] = Field(None, max_length=20, description="默认字幕格式")

    # 高级设置
    auto_start_jobs: Optional[bool] = Field(None, description="自动开始任务")
    notification_enabled: Optional[bool] = Field(None, description="启用通知")
    theme: Optional[str] = Field(None, max_length=20, description="主题")


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., min_length=6, description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=100, description="新密码")


class UserSettingsResponse(BaseModel):
    """用户设置响应"""
    id: str
    username: str
    email: str
    is_admin: bool
    is_active: bool
    settings: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

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
                'settings': obj.settings or {},
                'created_at': obj.created_at,
                'updated_at': obj.updated_at,
            }
            return cls(**obj_dict)
        return super().model_validate(obj)
