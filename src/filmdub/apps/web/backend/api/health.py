"""健康检查 API"""
from fastapi import APIRouter, status
from pydantic import BaseModel

from filmdub.core.config import settings


router = APIRouter()


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    service: str
    auth_disabled: bool = False


@router.get("/health", status_code=status.HTTP_200_OK, response_model=HealthResponse)
async def health_check():
    """健康检查端点"""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        service="web-backend",
        auth_disabled=settings.auth_disabled,
    )
