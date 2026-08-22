"""
M09 Worker - Voice Synthesis

集成 VoiceAdapter 进行语音合成
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

from filmdub.adapter import VoiceAdapter


class M09Worker:
    """M09 模块 Worker - 语音合成"""

    def __init__(
        self,
        voice_backend: str = "qwen",
        voice_config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化 M09 Worker

        Args:
            voice_backend: 语音后端 (qwen)
            voice_config: 语音配置
        """
        self.voice_config = voice_config or {}
        
        # 初始化语音适配器
        self.voice_adapter = VoiceAdapter(
            backend=voice_backend,
            **self.voice_config
        )
        
        logger.info(f"M09Worker initialized with {voice_backend} backend")

    async def synthesize_speech(
        self,
        text: str,
        voice_id: str,
        output_path: Path,
        speed: float = 1.0,
        pitch: float = 1.0
    ) -> Path:
        """
        合成语音

        Args:
            text: 合成文本
            voice_id: 音色 ID
            output_path: 输出路径
            speed: 语速因子
            pitch: 音高因子

        Returns:
            输出音频路径
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Synthesizing speech: {len(text)} chars, "
            f"voice={voice_id}, speed={speed}, pitch={pitch}"
        )

        result_path = await self.voice_adapter.synthesize(
            text=text,
            voice_id=voice_id,
            output_path=output_path,
            speed=speed,
            pitch=pitch
        )

        logger.info(f"Speech synthesized: {result_path}")
        return result_path

    async def synthesize_batch(
        self,
        items: List[Dict[str, Any]],
        output_dir: Path
    ) -> List[Dict[str, Any]]:
        """
        批量合成语音

        Args:
            items: 合成项目列表，每项包含 text, voice_id, output_filename
            output_dir: 输出目录

        Returns:
            合成结果列表
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = []
        
        for i, item in enumerate(items):
            try:
                text = item["text"]
                voice_id = item["voice_id"]
                output_filename = item.get("output_filename", f"speech_{i:04d}.wav")
                speed = item.get("speed", 1.0)
                pitch = item.get("pitch", 1.0)
                
                output_path = output_dir / output_filename
                
                result_path = await self.synthesize_speech(
                    text=text,
                    voice_id=voice_id,
                    output_path=output_path,
                    speed=speed,
                    pitch=pitch
                )
                
                results.append({
                    "success": True,
                    "index": i,
                    "text": text,
                    "voice_id": voice_id,
                    "output_path": str(result_path),
                    "error": None
                })
                
            except Exception as e:
                logger.error(f"Failed to synthesize item {i}: {e}")
                results.append({
                    "success": False,
                    "index": i,
                    "text": item.get("text", ""),
                    "voice_id": item.get("voice_id", ""),
                    "output_path": None,
                    "error": str(e)
                })

        successful = sum(1 for r in results if r["success"])
        logger.info(f"Batch synthesis completed: {successful}/{len(items)} successful")

        return results

    async def list_available_voices(self) -> List[Dict[str, Any]]:
        """
        列出可用音色

        Returns:
            音色列表
        """
        voices = await self.voice_adapter.list_voices()
        logger.info(f"Listed {len(voices)} available voices")
        return voices

    async def get_voice_info(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """
        获取音色信息

        Args:
            voice_id: 音色 ID

        Returns:
            音色信息
        """
        voice_info = await self.voice_adapter.get_voice(voice_id)
        return voice_info

    async def health_check(self) -> bool:
        """
        检查语音服务健康状态

        Returns:
            是否健康
        """
        if hasattr(self.voice_adapter, "health_check"):
            return await self.voice_adapter.health_check()
        return True

    async def close(self):
        """清理资源"""
        if hasattr(self.voice_adapter, 'close'):
            await self.voice_adapter.close()
