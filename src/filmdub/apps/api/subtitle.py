"""
Module 03 API 端点
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from workers.subtitle import SubtitleRunner, SubtitleConfig, TranslationMode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subtitle", tags=["subtitle"])


class SubtitleStartRequest(BaseModel):
    """开始字幕处理请求"""
    project_id: str
    video_path: Optional[str] = None
    translation_mode: Optional[str] = None


class SubtitleResponse(BaseModel):
    """字幕处理响应"""
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None


@router.post("/start", response_model=SubtitleResponse)
async def start_subtitle_processing(
    request: SubtitleStartRequest,
    background_tasks: BackgroundTasks
):
    """
    开始字幕处理
    """
    try:
        # 检查项目是否存在
        project_dir = Path(f"data/projects/{request.project_id}")
        if not project_dir.exists():
            raise HTTPException(status_code=404, detail=f"Project {request.project_id} not found")

        # 创建配置
        config = SubtitleConfig()

        # 设置翻译模式
        if request.translation_mode:
            try:
                config.translation_mode = TranslationMode(request.translation_mode)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid translation mode: {request.translation_mode}"
                )

        # 获取视频路径
        if not request.video_path:
            video_path = project_dir / "media" / "source.mkv"
            if not video_path.exists():
                raise HTTPException(
                    status_code=400,
                    detail="No video file found. Please provide video_path"
                )
        else:
            video_path = Path(request.video_path)
            if not video_path.exists():
                raise HTTPException(status_code=404, detail=f"Video file not found: {request.video_path}")

        # 创建工作器
        runner = SubtitleRunner(request.project_id, config)

        # 在后台执行
        def run_in_background():
            try:
                result = runner.run(video_path)
                logger.info(f"Subtitle processing completed for {request.project_id}: {result['status']}")
            except Exception as e:
                logger.error(f"Subtitle processing failed for {request.project_id}: {e}", exc_info=True)

        background_tasks.add_task(run_in_background)

        return SubtitleResponse(
            status="started",
            message=f"Subtitle processing started for project {request.project_id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start subtitle processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{project_id}", response_model=SubtitleResponse)
async def get_subtitle_status(project_id: str):
    """
    获取字幕处理状态
    """
    try:
        project_dir = Path(f"data/projects/{project_id}")
        manifest_path = project_dir / "dialogue" / "dialogue_manifest.json"

        if not manifest_path.exists():
            return SubtitleResponse(
                status="not_started",
                message=f"No subtitle processing found for project {project_id}"
            )

        import json
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        return SubtitleResponse(
            status="completed",
            message=f"Subtitle processing completed for project {project_id}",
            data=manifest
        )

    except Exception as e:
        logger.error(f"Failed to get subtitle status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/manifest/{project_id}", response_model=SubtitleResponse)
async def get_subtitle_manifest(project_id: str):
    """
    获取对话清单
    """
    try:
        project_dir = Path(f"data/projects/{project_id}")
        manifest_path = project_dir / "dialogue" / "dialogue_manifest.json"

        if not manifest_path.exists():
            raise HTTPException(status_code=404, detail=f"Dialogue manifest not found for project {project_id}")

        import json
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        return SubtitleResponse(
            status="success",
            message=f"Retrieved dialogue manifest for project {project_id}",
            data=manifest
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dialogue manifest: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dialogues/{project_id}", response_model=SubtitleResponse)
async def get_dialogues(project_id: str, limit: int = 100, offset: int = 0):
    """
    获取对话列表
    """
    try:
        project_dir = Path(f"data/projects/{project_id}")
        jsonl_path = project_dir / "dialogue" / "normalized" / "dialogues.jsonl"

        if not jsonl_path.exists():
            raise HTTPException(status_code=404, detail=f"No dialogues found for project {project_id}")

        dialogues = []
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i < offset:
                    continue
                if len(dialogues) >= limit:
                    break
                dialogue = json.loads(line)
                dialogues.append(dialogue)

        return SubtitleResponse(
            status="success",
            message=f"Retrieved {len(dialogues)} dialogues for project {project_id}",
            data={
                "dialogues": dialogues,
                "total": len(dialogues),
                "offset": offset,
                "limit": limit
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dialogues: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/reset/{project_id}", response_model=SubtitleResponse)
async def reset_subtitle(project_id: str):
    """
    重置字幕处理
    """
    try:
        import shutil

        project_dir = Path(f"data/projects/{project_id}")
        dialogue_dir = project_dir / "dialogue"

        if not dialogue_dir.exists():
            return SubtitleResponse(
                status="not_found",
                message=f"No dialogue data found for project {project_id}"
            )

        shutil.rmtree(dialogue_dir)

        return SubtitleResponse(
            status="success",
            message=f"Subtitle data reset for project {project_id}"
        )

    except Exception as e:
        logger.error(f"Failed to reset subtitle data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


import json  # 放在文件末尾
