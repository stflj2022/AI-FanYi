"""
M02 Worker - Media Research & Identity Resolution

集成 AudioSeparationAdapter 进行音频分离
"""

from pathlib import Path
from typing import Dict, Any, Optional
import json
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

    async def analyze_scenes(
        self,
        video_path: Path,
        output_dir: Optional[Path] = None,
        **detector_kwargs
    ) -> Dict[str, Any]:
        """
        分析视频的场景/镜头/黑屏，输出 Scene Timeline（ticket-034）

        Args:
            video_path: 视频文件路径
            output_dir: 输出目录（写入 <stem>_scene_timeline.json）
            detector_kwargs: SceneDetector 参数（scene_threshold/shot_threshold 等）

        Returns:
            Scene Timeline 字典（含 scenes/shots/black_frames）
        """
        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        from filmdub.workers.research.scene_detection import SceneDetector

        detector = SceneDetector(**detector_kwargs)
        timeline = detector.detect(video_path)

        # 写出 Scene Timeline 文件（对齐时间轴）
        if output_dir is not None:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            timeline_path = output_dir / f"{Path(video_path).stem}_scene_timeline.json"
            with open(timeline_path, 'w', encoding='utf-8') as f:
                json.dump(timeline, f, ensure_ascii=False, indent=2)
            timeline["timeline_path"] = str(timeline_path)

        logger.info(
            f"Scene detection completed: {len(timeline['scenes'])} scenes, "
            f"{len(timeline['shots'])} shots, {len(timeline['black_frames'])} black segments"
        )
        return timeline

    async def close(self):
        """清理资源"""
        if hasattr(self.separation_adapter, 'close'):
            await self.separation_adapter.close()
