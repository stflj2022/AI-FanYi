"""
M10 Worker - Prosody & Performance

音色、韵律和表演处理 Worker
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..common import save_json_artifact, run_worker_loop

from .config import M10Config
from .processor import ProsodyProcessor
from .models import (
    DialogueSegment,
    ProsodyParams,
    ProsodyResult,
    BatchProsodyResult,
    EmotionType,
)

logger = logging.getLogger(__name__)


class M10Worker:
    """M10 模块 Worker - 韵律与表演处理"""

    def __init__(self, config: M10Config = None, projects_base_dir: str | Path = "./artifacts"):
        """
        初始化 Worker

        Args:
            config: M10 配置
            projects_base_dir: 项目基目录
        """
        self.config = config or M10Config()
        self.projects_base_dir = Path(projects_base_dir)
        self.processor = ProsodyProcessor(self.config)

        logger.info(f"M10Worker initialized (projects_base_dir={self.projects_base_dir})")

    async def process_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理作业

        Args:
            job_data: 作业数据
                - project_id: 项目 ID
                - job_id: 作业 ID
                - dialogues: 对白列表
                - target_durations: 目标时长映射（可选）

        Returns:
            处理结果
        """
        job_id = job_data.get("job_id")
        project_id = job_data.get("project_id")

        logger.info(f"Processing job {job_id} for project {project_id}")

        try:
            # 1. 获取输入数据
            dialogues_data = job_data.get("dialogues", [])
            target_durations = job_data.get("target_durations", {})

            if not dialogues_data:
                raise ValueError("No dialogues provided in job data")

            # 2. 转换为 DialogueSegment 对象
            dialogues = []
            for data in dialogues_data:
                dialogue = DialogueSegment.from_dict(data)
                dialogues.append(dialogue)

            logger.info(f"Processing {len(dialogues)} dialogue segments")

            # 3. 批量处理
            batch_result = await self.process_batch(dialogues, target_durations)

            # 4. 构建结果
            result = {
                "status": "success",
                "total": batch_result.total,
                "successful": batch_result.successful,
                "failed": batch_result.failed,
                "results": [r.to_dict() for r in batch_result.results],
            }

            # 5. 持久化结果 Artifact
            result["artifact_path"] = save_json_artifact(
                project_id,
                "prosody_performance",
                result,
                self.projects_base_dir
            )

            logger.info(f"Job {job_id} completed: {batch_result.successful}/{batch_result.total} successful")

            return result

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

    async def process_dialogue(
        self,
        dialogue: DialogueSegment,
        target_duration: Optional[float] = None,
    ) -> ProsodyResult:
        """
        处理单个对白片段

        Args:
            dialogue: 对白片段
            target_duration: 目标时长

        Returns:
            处理结果
        """
        dialogue_id = dialogue.dialogue_id
        input_path = dialogue.audio_path

        logger.info(f"Processing dialogue {dialogue_id}")

        try:
            # 1. 检查输入文件
            if not input_path.exists():
                raise FileNotFoundError(f"Input audio not found: {input_path}")

            # 2. 获取当前时长
            current_duration = await self.processor._get_audio_duration(input_path)
            dialogue.current_duration = current_duration

            # 3. 确定韵律参数
            if dialogue.prosody_params:
                params = dialogue.prosody_params
            else:
                # 从情绪映射
                params = self.processor.map_emotion_to_prosody(dialogue.emotion)
                dialogue.prosody_params = params

            # 4. 如果有目标时长，调整语速
            if target_duration and current_duration:
                speed = await self.processor.align_duration(
                    input_path,
                    target_duration,
                    current_duration
                )
                params.speed = speed

            # 5. 确定输出路径
            output_path = dialogue.output_path
            if output_path is None:
                output_dir = input_path.parent / "processed"
                output_dir.mkdir(exist_ok=True)
                output_path = output_dir / f"{input_path.stem}_processed{input_path.suffix}"

            # 6. 处理音频
            success, final_duration, error = await self.processor.process_audio(
                input_path,
                output_path,
                params
            )

            # 7. 返回结果
            if success:
                logger.info(f"Dialogue {dialogue_id} processed successfully: {final_duration:.2f}s")
                return ProsodyResult(
                    dialogue_id=dialogue_id,
                    input_path=input_path,
                    output_path=output_path,
                    success=True,
                    applied_params=params,
                    duration_before=current_duration,
                    duration_after=final_duration,
                )
            else:
                logger.error(f"Dialogue {dialogue_id} processing failed: {error}")
                return ProsodyResult(
                    dialogue_id=dialogue_id,
                    input_path=input_path,
                    output_path=output_path,
                    success=False,
                    error=error,
                )

        except Exception as e:
            logger.error(f"Dialogue {dialogue_id} processing exception: {e}")
            return ProsodyResult(
                dialogue_id=dialogue_id,
                input_path=input_path,
                output_path=None,
                success=False,
                error=str(e),
            )

    async def process_batch(
        self,
        dialogues: List[DialogueSegment],
        target_durations: Optional[Dict[str, float]] = None,
    ) -> BatchProsodyResult:
        """
        批量处理对白片段

        Args:
            dialogues: 对白片段列表
            target_durations: 目标时长映射（dialogue_id -> duration）

        Returns:
            批量处理结果
        """
        results = []
        successful = 0
        failed = 0

        # 并发处理（限制并发数）
        semaphore = asyncio.Semaphore(4)  # 最多同时处理 4 个

        async def process_with_semaphore(dialogue: DialogueSegment) -> ProsodyResult:
            async with semaphore:
                target_duration = target_durations.get(dialogue.dialogue_id) if target_durations else None
                return await self.process_dialogue(dialogue, target_duration)

        # 执行并发处理
        tasks = [process_with_semaphore(d) for d in dialogues]
        results = await asyncio.gather(*tasks)

        # 统计结果
        for result in results:
            if result.success:
                successful += 1
            else:
                failed += 1

        return BatchProsodyResult(
            total=len(dialogues),
            successful=successful,
            failed=failed,
            results=results,
        )

    async def health_check(self) -> bool:
        """
        检查 Worker 健康状态

        Returns:
            是否健康
        """
        try:
            # 检查 FFmpeg 是否可用
            process = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            return process.returncode == 0
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False

    async def close(self):
        """清理资源"""
        logger.info("M10Worker closing")


async def main():
    """主函数：运行文件系统作业轮询循环"""
    logger.info("M10 Prosody & Performance Worker starting...")

    worker = M10Worker()
    await run_worker_loop(
        "M10",
        worker.process_job,
        Path("./queue/m10"),
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    asyncio.run(main())
