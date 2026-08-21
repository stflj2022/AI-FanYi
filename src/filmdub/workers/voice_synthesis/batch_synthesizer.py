"""
批量合成器

支持并发批量合成
"""
import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger
from pathlib import Path

from .config import M09Config
from .model_manager import TTSModelManager
from .tts_engine import TTSEngine
from .models import M09Input, M09Output


class BatchSynthesizer:
    """批量合成器"""

    def __init__(
        self,
        model_manager: TTSModelManager,
        config: M09Config = None
    ):
        """
        初始化批量合成器

        Args:
            model_manager: 模型管理器
            config: M09 配置
        """
        self.model_manager = model_manager
        self.config = config or M09Config()
        self.tts_engine = TTSEngine(model_manager, config)

        # 信号量控制并发
        self.semaphore = asyncio.Semaphore(self.config.max_concurrent_jobs)

    async def synthesize_batch(
        self,
        inputs: List[M09Input],
        output_dir: str
    ) -> List[M09Output]:
        """
        批量合成

        Args:
            inputs: 输入列表
            output_dir: 输出目录

        Returns:
            输出列表
        """
        logger.info(f"Starting batch synthesis: {len(inputs)} dialogues")

        # 确保输出目录存在
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # 并发合成
        tasks = [
            self._synthesize_with_semaphore(input_item, output_dir)
            for input_item in inputs
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        outputs = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Dialogue {i} failed: {result}")
                outputs.append(M09Output(
                    status="error",
                    dialogue_id=inputs[i].dialogue_id,
                    character_id=inputs[i].character_id,
                    error=str(result)
                ))
            else:
                outputs.append(result)

        # 统计
        success_count = sum(1 for o in outputs if o.status == "success")
        error_count = sum(1 for o in outputs if o.status == "error")

        logger.info(
            f"Batch synthesis completed: "
            f"{success_count} success, {error_count} error"
        )

        return outputs

    async def _synthesize_with_semaphore(
        self,
        input_item: M09Input,
        output_dir: str
    ) -> M09Output:
        """
        带信号量控制的合成

        Args:
            input_item: 输入
            output_dir: 输出目录

        Returns:
            输出
        """
        async with self.semaphore:
            return await self._synthesize_single(input_item, output_dir)

    async def _synthesize_single(
        self,
        input_item: M09Input,
        output_dir: str
    ) -> M09Output:
        """
        单个合成

        Args:
            input_item: 输入
            output_dir: 输出目录

        Returns:
            输出
        """
        try:
            # 构建输出路径
            output_path = str(
                Path(output_dir) / f"{input_item.dialogue_id}.{self.config.audio_format}"
            )

            # 构建韵律参数
            prosody = {
                "dialogue_id": input_item.dialogue_id,
                "character_id": input_item.character_id,
                "speed": input_item.speed,
                "pitch": input_item.pitch,
                "pause_before": input_item.pause_before,
                "pause_after": input_item.pause_after,
                "energy": input_item.energy,
                "emotion": input_item.emotion,
                "emotion_intensity": input_item.emotion_intensity
            }

            # 在线程池中运行合成（避免阻塞事件循环）
            loop = asyncio.get_event_loop()
            artifact = await loop.run_in_executor(
                None,
                self.tts_engine.synthesize,
                input_item.text,
                input_item.voice_profile_id,
                prosody,
                output_path
            )

            if artifact:
                return M09Output(
                    status="success",
                    dialogue_id=input_item.dialogue_id,
                    character_id=input_item.character_id,
                    audio_artifact=artifact,
                    metadata=input_item.metadata
                )
            else:
                return M09Output(
                    status="error",
                    dialogue_id=input_item.dialogue_id,
                    character_id=input_item.character_id,
                    error="Synthesis returned no audio"
                )

        except Exception as e:
            logger.error(f"Synthesis failed for dialogue {input_item.dialogue_id}: {e}")
            return M09Output(
                status="error",
                dialogue_id=input_item.dialogue_id,
                character_id=input_item.character_id,
                error=str(e)
            )
