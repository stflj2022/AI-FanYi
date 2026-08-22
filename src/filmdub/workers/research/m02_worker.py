"""
M02 Worker - Media Research & Identity Resolution

集成 AudioSeparationAdapter 进行音频分离
"""

from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

from filmdub.adapter import AudioSeparationAdapter
from filmdub.workers.audio_scene_analysis.models import AudioFeatures


class M02Worker:
    """M02 模块 Worker - 媒体分析与识别"""

    def __init__(
        self,
        separation_backend: str = "htdemucs",
        separation_config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化 M02 Worker

        Args:
            separation_backend: 音频分离后端 (htdemucs)
            separation_config: 分离配置
        """
        self.separation_config = separation_config or {}
        
        # 初始化音频分离适配器
        self.separation_adapter = AudioSeparationAdapter(
            backend=separation_backend,
            **self.separation_config
        )
        
        logger.info(f"M02Worker initialized with {separation_backend} backend")

    async def analyze_audio(
        self,
        audio_path: Path,
        output_dir: Optional[Path] = None,
        extract_vocals_only: bool = False
    ) -> Dict[str, Any]:
        """
        分析音频文件

        Args:
            audio_path: 音频文件路径
            output_dir: 输出目录
            extract_vocals_only: 是否只提取人声

        Returns:
            分析结果字典
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if output_dir is None:
            output_dir = audio_path.parent / "stems"
        
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Analyzing audio: {audio_path}")

        if extract_vocals_only:
            # 只提取人声
            vocals_path = output_dir / f"{audio_path.stem}_vocals.wav"
            await self.separation_adapter.separate_vocals_only(
                audio_path, vocals_path
            )
            
            result = {
                "audio_path": str(audio_path),
                "vocals_path": str(vocals_path),
                "stems": {"vocals": str(vocals_path)},
                "extract_vocals_only": True
            }
        else:
            # 分离所有音轨
            stems = await self.separation_adapter.separate(
                audio_path, output_dir
            )
            
            result = {
                "audio_path": str(audio_path),
                "output_dir": str(output_dir),
                "stems": {k: str(v) for k, v in stems.items()},
                "extract_vocals_only": False
            }

        logger.info(f"Audio analysis completed: {len(result['stems'])} stems extracted")
        return result

    async def close(self):
        """清理资源"""
        if hasattr(self.separation_adapter, 'close'):
            await self.separation_adapter.close()
