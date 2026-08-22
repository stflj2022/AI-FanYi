"""
M04 Worker - Character Database Construction

集成 VoiceAdapter 进行音色克隆和管理
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
import json

logger = logging.getLogger(__name__)

from filmdub.adapter import VoiceAdapter
from filmdub.workers.character_db.models import Character


class M04Worker:
    """M04 模块 Worker - 人物数据库构建"""

    def __init__(
        self,
        voice_backend: str = "qwen",
        voice_config: Optional[Dict[str, Any]] = None,
        voices_dir: Optional[Path] = None
    ):
        """
        初始化 M04 Worker

        Args:
            voice_backend: 语音后端 (qwen)
            voice_config: 语音配置
            voices_dir: 音色库目录
        """
        self.voice_config = voice_config or {}
        self.voices_dir = voices_dir or Path.cwd() / "cloned_voices"
        self.voices_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化语音适配器
        self.voice_adapter = VoiceAdapter(
            backend=voice_backend,
            **self.voice_config
        )
        
        # 人物数据库
        self.characters: Dict[str, Character] = {}
        
        logger.info(f"M04Worker initialized with {voice_backend} backend")
        logger.info(f"Voices directory: {self.voices_dir}")

    async def clone_character_voice(
        self,
        character_id: str,
        character_name: str,
        reference_audio_path: Path,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        为人物克隆音色

        Args:
            character_id: 人物 ID
            character_name: 人物名称
            reference_audio_path: 参考音频路径
            description: 描述

        Returns:
            克隆结果
        """
        if not reference_audio_path.exists():
            raise FileNotFoundError(f"Reference audio not found: {reference_audio_path}")

        logger.info(f"Cloning voice for character {character_name} ({character_id})")

        # 使用 VoiceAdapter 克隆音色
        voice_id = await self.voice_adapter.clone_voice(
            name=f"{character_name}_{character_id}",
            reference_audio_path=reference_audio_path,
            description=description or f"Voice for {character_name}"
        )

        # 保存音色映射
        voice_mapping_path = self.voices_dir / f"{character_id}_voice.json"
        voice_info = {
            "character_id": character_id,
            "character_name": character_name,
            "voice_id": voice_id,
            "reference_audio": str(reference_audio_path),
            "description": description,
            "created_at": None  # Would use datetime.utcnow() if needed
        }
        
        with voice_mapping_path.open("w") as f:
            json.dump(voice_info, f, indent=2)

        logger.info(f"Voice cloned successfully: {voice_id}")
        return voice_info

    async def get_character_voice(
        self,
        character_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取人物音色信息

        Args:
            character_id: 人物 ID

        Returns:
            音色信息或 None
        """
        voice_mapping_path = self.voices_dir / f"{character_id}_voice.json"
        
        if not voice_mapping_path.exists():
            return None
        
        with voice_mapping_path.open("r") as f:
            return json.load(f)

    async def list_all_voices(self) -> List[Dict[str, Any]]:
        """
        列出所有可用音色

        Returns:
            音色列表
        """
        voices = await self.voice_adapter.list_voices()
        logger.info(f"Listed {len(voices)} voices from service")
        return voices

    async def delete_character_voice(
        self,
        character_id: str
    ) -> bool:
        """
        删除人物音色

        Args:
            character_id: 人物 ID

        Returns:
            是否删除成功
        """
        # 获取音色 ID
        voice_info = await self.get_character_voice(character_id)
        if not voice_info:
            return False
        
        # 从服务删除
        success = await self.voice_adapter.delete_voice(voice_info["voice_id"])
        
        # 删除本地映射文件
        if success:
            voice_mapping_path = self.voices_dir / f"{character_id}_voice.json"
            if voice_mapping_path.exists():
                voice_mapping_path.unlink()
            logger.info(f"Deleted voice for character {character_id}")
        
        return success

    async def synthesize_character_speech(
        self,
        character_id: str,
        text: str,
        output_path: Path,
        speed: float = 1.0,
        pitch: float = 1.0
    ) -> Path:
        """
        为人物合成语音

        Args:
            character_id: 人物 ID
            text: 合成文本
            output_path: 输出路径
            speed: 语速
            pitch: 音高

        Returns:
            输出音频路径
        """
        # 获取音色 ID
        voice_info = await self.get_character_voice(character_id)
        if not voice_info:
            raise ValueError(f"No voice found for character {character_id}")
        
        voice_id = voice_info["voice_id"]
        
        # 使用 VoiceAdapter 合成
        result_path = await self.voice_adapter.synthesize(
            text=text,
            voice_id=voice_id,
            output_path=output_path,
            speed=speed,
            pitch=pitch
        )
        
        logger.info(f"Synthesized speech for {character_id}: {len(text)} chars")
        return result_path

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
