"""
M05 Worker - Audio & Scene Analysis

集成 ASRAdapter 进行语音转写
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

from filmdub.adapter import ASRAdapter


class M05Worker:
    """M05 模块 Worker - 音频与场景分析"""

    def __init__(
        self,
        asr_backend: str = "faster-whisper",
        asr_config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化 M05 Worker

        Args:
            asr_backend: ASR 后端 (faster-whisper)
            asr_config: ASR 配置
        """
        self.asr_config = asr_config or {}
        
        # 初始化 ASR 适配器
        self.asr_adapter = ASRAdapter(
            backend=asr_backend,
            **self.asr_config
        )
        
        logger.info(f"M05Worker initialized with {asr_backend} backend")

    async def transcribe_audio(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        word_timestamps: bool = True
    ) -> Dict[str, Any]:
        """
        转写音频

        Args:
            audio_path: 音频文件路径
            language: 语言代码 (如 "en", "zh")
            word_timestamps: 是否包含词级别时间戳

        Returns:
            转写结果
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Transcribing audio: {audio_path}")

        result = await self.asr_adapter.transcribe(
            audio_path=audio_path,
            language=language,
            word_timestamps=word_timestamps
        )

        logger.info(
            f"Transcription completed: {len(result['segments'])} segments, "
            f"language={result.get('language', 'unknown')}"
        )

        return result

    async def transcribe_with_speakers(
        self,
        audio_path: Path,
        num_speakers: Optional[int] = None,
        language: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        转写音频并识别说话人

        Args:
            audio_path: 音频文件路径
            num_speakers: 说话人数量 (None 自动检测)
            language: 语言代码

        Returns:
            带说话人标签的段落列表
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Transcribing with speaker diarization: {audio_path}")

        segments = await self.asr_adapter.transcribe_with_speakers(
            audio_path=audio_path,
            num_speakers=num_speakers,
            language=language
        )

        # 统计说话人数量
        speakers = set(seg.get("speaker", "UNKNOWN") for seg in segments)
        logger.info(
            f"Speaker diarization completed: {len(segments)} segments, "
            f"{len(speakers)} speakers"
        )

        return segments

    async def analyze_dialogue(
        self,
        audio_path: Path,
        with_speakers: bool = True,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析音频对话

        Args:
            audio_path: 音频文件路径
            with_speakers: 是否识别说话人
            language: 语言代码

        Returns:
            对话分析结果
        """
        if with_speakers:
            segments = await self.transcribe_with_speakers(
                audio_path=audio_path,
                language=language
            )
            
            # 统计说话人
            speakers = set(seg.get("speaker", "UNKNOWN") for seg in segments)
            
            result = {
                "audio_path": str(audio_path),
                "with_speakers": True,
                "num_speakers": len(speakers),
                "speakers": list(speakers),
                "segments": segments,
                "total_segments": len(segments),
                "total_duration": segments[-1]["end"] if segments else 0
            }
        else:
            transcription = await self.transcribe_audio(audio_path, language)
            
            result = {
                "audio_path": str(audio_path),
                "with_speakers": False,
                "language": transcription.get("language"),
                "segments": transcription["segments"],
                "total_segments": len(transcription["segments"]),
                "full_text": transcription["text"]
            }

        logger.info(f"Dialogue analysis completed")
        return result

    async def close(self):
        """清理资源"""
        if hasattr(self.asr_adapter, 'close'):
            await self.asr_adapter.close()
