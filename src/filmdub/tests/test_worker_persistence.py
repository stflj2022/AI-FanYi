"""
Worker 数据库持久化测试
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from filmdub.orchestrator.worker_persistence import WorkerDBPersistence
from filmdub.orchestrator.models import Character, Gender, AgeRange, RoleType


class TestWorkerDBPersistence:
    """测试 Worker 数据库持久化"""

    @pytest.fixture
    def persistence(self, db: AsyncSession):
        """创建持久化服务实例"""
        return WorkerDBPersistence(db)

    @pytest.fixture
    def project_id(self):
        """项目 ID"""
        import uuid
        return f"test_project_{uuid.uuid4().hex[:8]}"

    @pytest.mark.asyncio
    async def test_save_character(self, persistence, project_id):
        """测试保存人物"""
        character_data = {
            "name": "Walter White",
            "name_en": "Walter White",
            "gender": Gender.MALE,
            "age_range": AgeRange.YOUNG_ADULT,
            "role_type": RoleType.MAIN,
            "actor_name": "Bryan Cranston",
            "personality": "Complex, brilliant, initially timid later becomes ruthless",
            "speech_pattern": "Precise, scientific, uses specific vocabulary",
            "relationships": {
                "Jesse Pinkman": {"type": "teacher_student", "description": "Former student and partner"}
            },
            "is_active": True,
        }

        character = await persistence.save_character(project_id, character_data)

        assert character.id is not None
        assert character.name == "Walter White"
        assert character.gender == Gender.MALE
        assert character.role_type == RoleType.MAIN

    @pytest.mark.asyncio
    async def test_get_character_by_name(self, persistence, project_id):
        """测试根据名称查询人物"""
        character_data = {
            "name": "Jesse Pinkman",
            "gender": Gender.MALE,
            "role_type": RoleType.MAIN,
        }

        await persistence.save_character(project_id, character_data)

        character = await persistence.get_character_by_name(project_id, "Jesse Pinkman")

        assert character is not None
        assert character.name == "Jesse Pinkman"

    @pytest.mark.asyncio
    async def test_update_character(self, persistence, project_id):
        """测试更新人物"""
        character_data = {
            "name": "Skyler White",
            "gender": Gender.FEMALE,
            "role_type": RoleType.MAIN,
            "personality": "Cautious, protective",
        }

        await persistence.save_character(project_id, character_data)

        # 更新
        updated_data = {
            "name": "Skyler White",
            "personality": "Cautious, protective, increasingly suspicious",
            "speech_pattern": "Direct, questioning",
        }

        updated = await persistence.save_character(project_id, updated_data)

        assert updated.personality == "Cautious, protective, increasingly suspicious"
        assert updated.speech_pattern == "Direct, questioning"

    @pytest.mark.asyncio
    async def test_save_voice_profile(self, persistence, project_id):
        """测试保存音色档案"""
        # 先创建人物
        character_data = {
            "name": "Walter White",
            "gender": Gender.MALE,
            "role_type": RoleType.MAIN,
        }

        character = await persistence.save_character(project_id, character_data)

        # 保存音色档案
        voice_data = {
            "name": "Walter-Voice-v1",
            "version": "v1.0",
            "tts_model": "qwen-tts",
            "tts_model_version": "1.0.0",
            "tts_config": {
                "backend": "qwen",
                "voice_id": "walter_v1",
            },
            "pitch_range": "0.9-1.1",
            "speed_range": "0.95-1.05",
            "emotional_range": ["neutral", "angry", "calm"],
            "is_validated": True,
        }

        voice_profile = await persistence.save_voice_profile(
            project_id,
            str(character.id),
            voice_data
        )

        assert voice_profile.id is not None
        assert voice_profile.tts_model == "qwen-tts"
        assert voice_profile.is_validated is True

    @pytest.mark.asyncio
    async def test_get_voice_profile_by_character(self, persistence, project_id):
        """测试根据人物 ID 查询音色档案"""
        # 创建人物
        character_data = {
            "name": "Jesse Pinkman",
            "gender": Gender.MALE,
            "role_type": RoleType.MAIN,
        }

        character = await persistence.save_character(project_id, character_data)

        # 保存音色档案
        voice_data = {
            "tts_model": "qwen-tts",
            "tts_config": {"voice_id": "jesse_v1"},
        }

        await persistence.save_voice_profile(project_id, str(character.id), voice_data)

        # 查询
        voice_profile = await persistence.get_voice_profile_by_character(str(character.id))

        assert voice_profile is not None
        assert voice_profile.tts_model == "qwen-tts"

    @pytest.mark.asyncio
    async def test_list_project_characters(self, persistence, project_id):
        """测试列出项目人物"""
        # 创建多个人物
        for i in range(3):
            character_data = {
                "name": f"Character {i}",
                "gender": Gender.MALE,
                "role_type": RoleType.SUPPORTING if i > 0 else RoleType.MAIN,
            }
            await persistence.save_character(project_id, character_data)

        characters = await persistence.list_project_characters(project_id)

        assert len(characters) == 3

    @pytest.mark.asyncio
    async def test_save_audio_analysis(self, persistence, project_id):
        """测试保存音频分析结果"""
        analysis_id = await persistence.save_audio_analysis(
            project_id,
            {
                "media_file": "ep1.mp4",
                "analysis_type": "speaker_segment",
                "payload": {
                    "segments": [
                        {"speaker_id": "s1", "start_time": 0.0, "end_time": 2.0}
                    ]
                },
            },
        )
        # 应返回真实 UUID（而非旧占位符）
        import uuid
        assert uuid.UUID(analysis_id)

        # 验证已落库
        from filmdub.orchestrator.models import AudioAnalysis
        result = await persistence.db.execute(
            select(AudioAnalysis).where(AudioAnalysis.id == uuid.UUID(analysis_id))
        )
        saved = result.scalar_one_or_none()
        assert saved is not None
        assert saved.analysis_type == "speaker_segment"
        assert saved.payload["segments"][0]["speaker_id"] == "s1"

    @pytest.mark.asyncio
    async def test_cross_project_isolation(self, persistence):
        """测试跨项目隔离"""
        project_id_1 = "project_1"
        project_id_2 = "project_2"

        # 在项目 1 创建人物
        character_data = {
            "name": "Walter White",
            "gender": Gender.MALE,
            "role_type": RoleType.MAIN,
        }

        await persistence.save_character(project_id_1, character_data)

        # 在项目 2 创建同名人物
        await persistence.save_character(project_id_2, character_data)

        # 查询应该返回各自项目的人物
        char_1 = await persistence.get_character_by_name(project_id_1, "Walter White")
        char_2 = await persistence.get_character_by_name(project_id_2, "Walter White")

        assert char_1 is not None
        assert char_2 is not None
        # 两个项目各自的同名人物应归属不同的 project UUID（跨项目隔离）
        assert char_1.project_id != char_2.project_id
        assert char_1.id != char_2.id

        # 反向验证：用项目名解析出的 UUID 应能查到各自人物
        proj_1_uuid = await persistence._resolve_project_uuid(project_id_1)
        proj_2_uuid = await persistence._resolve_project_uuid(project_id_2)
        assert char_1.project_id == proj_1_uuid
        assert char_2.project_id == proj_2_uuid
