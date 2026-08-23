"""上传 API"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from filmdub.core.orchestrator_db import get_db
from filmdub.core.models import MediaAsset, MediaStream
from .schemas.upload_schemas import (
    UploadResponse,
    UploadProgressResponse,
    MediaMetadataResponse,
    UploadStatus,
    MediaType,
    ErrorResponse,
    UploadError,
)
from ..services.upload_service import get_upload_service, UploadService

router = APIRouter(prefix="/uploads", tags=["uploads"])

# 允许的 MIME 类型
ALLOWED_MIME_TYPES = {
    # 视频
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",  # avi
    "video/x-matroska",  # mkv
    "video/webm",
    "video/mpeg",
    # 音频
    "audio/mpeg",
    "audio/wav",
    "audio/x-wav",
    "audio/ogg",
    "audio/mp4",
    # 图片
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
}

# 文件大小限制（默认 10GB）
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024


def get_mime_type(media_type: MediaType, filename: str) -> str:
    """根据文件名和媒体类型获取 MIME 类型"""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    mime_map = {
        # 视频
        MediaType.VIDEO: {
            "mp4": "video/mp4",
            "mov": "video/quicktime",
            "avi": "video/x-msvideo",
            "mkv": "video/x-matroska",
            "webm": "video/webm",
            "mpeg": "video/mpeg",
            "mpg": "video/mpeg",
        },
        # 音频
        MediaType.AUDIO: {
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "ogg": "audio/ogg",
            "m4a": "audio/mp4",
        },
        # 图片
        MediaType.IMAGE: {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
        },
    }

    mime_types = mime_map.get(media_type, {})
    return mime_types.get(ext, f"application/{media_type.value}")


@router.post("", response_model=UploadResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(..., description="要上传的文件"),
    project_id: Optional[str] = Form(None, description="关联的项目 ID"),
    media_type: MediaType = Form(MediaType.VIDEO, description="媒体类型"),
    upload_service: UploadService = Depends(get_upload_service),
):
    """
    上传文件

    - **file**: 要上传的文件
    - **project_id**: 关联的项目 ID（可选）
    - **media_type**: 媒体类型（video/audio/image）
    """
    # 验证文件大小
    file_size = 0
    for chunk in file.file:
        file_size += len(chunk)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"文件大小超过限制（最大 {MAX_FILE_SIZE // (1024*1024*1024)}GB）"
            )
    file.file.seek(0)  # 重置文件指针

    # 验证 MIME 类型
    if file.content_type not in ALLOWED_MIME_TYPES:
        # 尝试从文件名推断
        inferred_mime = get_mime_type(media_type, file.filename or "")
        if inferred_mime not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"不支持的文件类型: {file.content_type}"
            )

    # 创建上传会话
    session = upload_service.create_session(
        filename=file.filename or "unnamed",
        file_size=file_size,
        mime_type=file.content_type or get_mime_type(media_type, file.filename or ""),
        project_id=uuid.UUID(project_id) if project_id else None,
        media_type=media_type,
    )

    # 处理上传
    try:
        media_asset_id = await upload_service.handle_upload(session, file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

    return UploadResponse(
        id=session.id,
        status=session.status,
        filename=session.filename,
        file_size=session.file_size,
        mime_type=session.mime_type,
        project_id=session.project_id,
        media_type=session.media_type,
        progress=session.progress,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/{upload_id}", response_model=UploadProgressResponse)
async def get_upload_progress(
    upload_id: str,
    upload_service: UploadService = Depends(get_upload_service),
):
    """
    获取上传进度

    - **upload_id**: 上传会话 ID
    """
    try:
        upload_uuid = uuid.UUID(upload_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的上传 ID")

    session = upload_service.get_session(upload_uuid)
    if not session:
        raise HTTPException(status_code=404, detail="上传会话不存在")

    return UploadProgressResponse(
        id=session.id,
        status=session.status,
        progress=session.progress,
        bytes_uploaded=session.bytes_uploaded,
        total_bytes=session.file_size,
        speed_bytes_per_sec=session.speed,
        estimated_seconds_remaining=session.estimated_remaining,
    )


@router.get("/{upload_id}/metadata", response_model=MediaMetadataResponse)
async def get_media_metadata(
    upload_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取媒体元数据

    - **upload_id**: 上传会话 ID
    """
    # 先查找 media_asset_id
    upload_service = get_upload_service()
    try:
        upload_uuid = uuid.UUID(upload_id)
        session = upload_service.get_session(upload_uuid)
        if not session:
            raise HTTPException(status_code=404, detail="上传会话不存在")
        if session.status != UploadStatus.READY:
            raise HTTPException(status_code=400, detail="上传未完成")
        media_asset_id = getattr(session, "media_asset_id", None)
        if not media_asset_id:
            raise HTTPException(status_code=404, detail="媒体资产不存在")
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的上传 ID")

    # 查询媒体资产（异步）
    from sqlalchemy import select
    result = await db.execute(select(MediaAsset).filter(MediaAsset.id == media_asset_id))
    media_asset = result.scalar_one_or_none()
    if not media_asset:
        raise HTTPException(status_code=404, detail="媒体资产不存在")

    # 查询流信息（异步）
    result = await db.execute(select(MediaStream).filter(MediaStream.media_id == media_asset_id))
    streams = result.scalars().all()
    streams_data = []
    video_streams = []
    audio_streams = []
    subtitle_streams = []

    for stream in streams:
        stream_data = {
            "index": stream.index,
            "type": stream.stream_type,
            "codec": stream.codec,
            "codec_long": stream.codec_long,
            "profile": stream.profile,
            "level": stream.level,
            "width": stream.width,
            "height": stream.height,
            "frame_rate": stream.frame_rate,
            "bit_rate": stream.bit_rate,
            "channels": stream.channels,
            "sample_rate": stream.sample_rate,
            "language": stream.language,
        }
        streams_data.append(stream_data)

        if stream.stream_type == "video":
            video_streams.append(stream_data)
        elif stream.stream_type == "audio":
            audio_streams.append(stream_data)
        elif stream.stream_type == "subtitle":
            subtitle_streams.append(stream_data)

    return MediaMetadataResponse(
        id=upload_uuid,
        media_asset_id=media_asset_id,
        filename=media_asset.original_filename,
        duration_seconds=media_asset.duration_seconds,
        format=media_asset.container_format,
        streams=streams_data,
        video_streams=video_streams,
        audio_streams=audio_streams,
        subtitle_streams=subtitle_streams,
    )


@router.delete("/{upload_id}", status_code=204)
async def delete_upload(
    upload_id: str,
    upload_service: UploadService = Depends(get_upload_service),
):
    """
    删除上传会话

    - **upload_id**: 上传会话 ID
    """
    try:
        upload_uuid = uuid.UUID(upload_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的上传 ID")

    session = upload_service.get_session(upload_uuid)
    if not session:
        raise HTTPException(status_code=404, detail="上传会话不存在")

    upload_service.cleanup_session(upload_uuid)
    return None
