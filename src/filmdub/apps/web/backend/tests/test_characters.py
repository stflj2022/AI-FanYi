"""人物数据库相关测试"""
import pytest
from uuid import uuid4
from datetime import datetime

from filmdub.apps.web.backend.services.character_service import CharacterService
from filmdub.core.models import Character, VoiceProfile


@pytest.fixture
def character_service():
    """创建人物服务实例"""
    return CharacterService


@pytest.mark.asyncio
class TestCharacterService:
    """人物服务测试"""

    async def test_create_character(self, character_service, db_session):
        """测试创建人物"""
        project_id = uuid4()

        character = await CharacterService.create_character(
            db=db_session,
            project_id=project_id,
            name="Test Character",
            gender="male",
            age_range="young_adult",
            role_type="protagonist",
            description="A test character",
            original_actor="John Doe",
        )

        assert character.id is not None
        assert character.name == "Test Character"
        assert character.gender == "male"
        assert character.age_range == "young_adult"
        assert character.role_type == "protagonist"
        assert character.description == "A test character"
        assert character.original_actor == "John Doe"
        assert character.project_id == project_id

    async def test_get_character_by_id(self, character_service, db_session):
        """测试根据 ID 获取人物"""
        project_id = uuid4()

        created = await CharacterService.create_character(
            db=db_session,
            project_id=project_id,
            name="Test Character",
        )

        found = await CharacterService.get_character_by_id(db_session, created.id)

        assert found is not None
        assert found.id == created.id
        assert found.name == "Test Character"

    async def test_get_character_by_name(self, character_service, db_session):
        """测试根据名称获取人物"""
        project_id = uuid4()

        await CharacterService.create_character(
            db=db_session,
            project_id=project_id,
            name="Unique Name",
        )

        found = await CharacterService.get_character_by_name(db_session, project_id, "Unique Name")

        assert found is not None
        assert found.name == "Unique Name"

    async def test_update_character(self, character_service, db_session):
        """测试更新人物"""
        project_id = uuid4()

        created = await CharacterService.create_character(
            db=db_session,
            project_id=project_id,
            name="Old Name",
            gender="male",
        )

        updated = await CharacterService.update_character(
            db=db_session,
            character_id=created.id,
            name="New Name",
            gender="female",
        )

        assert updated is not None
        assert updated.name == "New Name"
        assert updated.gender == "female"

    async def test_delete_character(self, character_service, db_session):
        """测试删除人物"""
        project_id = uuid4()

        created = await CharacterService.create_character(
            db=db_session,
            project_id=project_id,
            name="To Delete",
        )

        success = await CharacterService.delete_character(db_session, created.id)

        assert success is True

        found = await CharacterService.get_character_by_id(db_session, created.id)
        assert found is None

    async def test_get_characters_with_filters(self, character_service, db_session):
        """测试带筛选条件获取人物列表"""
        project_id = uuid4()

        # 创建多个人物
        await CharacterService.create_character(
            db=db_session,
            project_id=project_id,
            name="Character 1",
            gender="male",
            age_range="young_adult",
        )
        await CharacterService.create_character(
            db=db_session,
            project_id=project_id,
            name="Character 2",
            gender="female",
            age_range="young_adult",
        )
        await CharacterService.create_character(
            db=db_session,
            project_id=project_id,
            name="Character 3",
            gender="male",
            age_range="senior",
        )

        # 筛选男性
        males, total = await CharacterService.get_characters(
            db=db_session,
            project_id=project_id,
            gender="male",
        )
        assert total == 2
        assert len(males) == 2

        # 筛选青年
        young_adults, total = await CharacterService.get_characters(
            db=db_session,
            project_id=project_id,
            age_range="young_adult",
        )
        assert total == 2
        assert len(young_adults) == 2

    async def test_search_characters(self, character_service, db_session):
        """测试搜索人物"""
        project_id = uuid4()

        await CharacterService.create_character(
            db=db_session,
            project_id=project_id,
            name="Alice Smith",
            description="A brave warrior",
        )
        await CharacterService.create_character(
            db=db_session,
            project_id=project_id,
            name="Bob Johnson",
            description="A wise wizard",
        )

        # 搜索 "Alice"
        results, total = await CharacterService.get_characters(
            db=db_session,
            project_id=project_id,
            search="Alice",
        )
        assert total == 1
        assert results[0].name == "Alice Smith"

        # 搜索 "warrior"
        results, total = await CharacterService.get_characters(
            db=db_session,
            project_id=project_id,
            search="warrior",
        )
        assert total == 1

    async def test_create_voice_profile(self, character_service, db_session):
        """测试创建音色档案"""
        project_id = uuid4()

        character = await CharacterService.create_character(
            db=db_session,
            project_id=project_id,
            name="Test Character",
        )

        voice_profile = await CharacterService.create_voice_profile(
            db=db_session,
            character_id=character.id,
            voice_id="voice-123",
            provider="cosyvoice",
            model="cosyvoice-v1",
            style="neutral",
            similarity_score=0.95,
        )

        assert voice_profile.id is not None
        assert voice_profile.character_id == character.id
        assert voice_profile.voice_id == "voice-123"
        assert voice_profile.provider == "cosyvoice"
        assert voice_profile.similarity_score == 0.95

    async def test_get_voice_profiles(self, character_service, db_session):
        """测试获取音色档案"""
        project_id = uuid4()

        character = await CharacterService.create_character(
            db=db_session,
            project_id=project_id,
            name="Test Character",
        )

        # 创建多个音色档案
        await CharacterService.create_voice_profile(
            db=db_session,
            character_id=character.id,
            voice_id="voice-1",
            provider="cosyvoice",
        )
        await CharacterService.create_voice_profile(
            db=db_session,
            character_id=character.id,
            voice_id="voice-2",
            provider="f5-tts",
        )

        profiles = await CharacterService.get_voice_profiles(db_session, character.id)

        assert len(profiles) == 2

    async def test_update_voice_profile(self, character_service, db_session):
        """测试更新音色档案"""
        project_id = uuid4()

        character = await CharacterService.create_character(
            db=db_session,
            project_id=project_id,
            name="Test Character",
        )

        profile = await CharacterService.create_voice_profile(
            db=db_session,
            character_id=character.id,
            voice_id="voice-1",
            provider="cosyvoice",
            similarity_score=0.85,
        )

        updated = await CharacterService.update_voice_profile(
            db=db_session,
            voice_profile_id=profile.id,
            similarity_score=0.95,
        )

        assert updated is not None
        assert updated.similarity_score == 0.95

    async def test_delete_voice_profile(self, character_service, db_session):
        """测试删除音色档案"""
        project_id = uuid4()

        character = await CharacterService.create_character(
            db=db_session,
            project_id=project_id,
            name="Test Character",
        )

        profile = await CharacterService.create_voice_profile(
            db=db_session,
            character_id=character.id,
            voice_id="voice-1",
            provider="cosyvoice",
        )

        success = await CharacterService.delete_voice_profile(db_session, profile.id)

        assert success is True

        profiles = await CharacterService.get_voice_profiles(db_session, character.id)
        assert len(profiles) == 0


@pytest.mark.asyncio
class TestCharacterAPI:
    """人物 API 测试"""

    async def test_create_character_api(self, client, db_session):
        """测试创建人物 API"""
        project_id = str(uuid4())

        response = await client.post(
            "/api/v1/characters",
            json={
                "project_id": project_id,
                "name": "API Test Character",
                "gender": "male",
                "age_range": "young_adult",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "API Test Character"
        assert data["gender"] == "male"

    async def test_get_characters_api(self, client, db_session):
        """测试获取人物列表 API"""
        project_id = str(uuid4())

        # 创建人物
        await client.post(
            "/api/v1/characters",
            json={
                "project_id": project_id,
                "name": "Character 1",
            },
        )
        await client.post(
            "/api/v1/characters",
            json={
                "project_id": project_id,
                "name": "Character 2",
            },
        )

        response = await client.get(f"/api/v1/characters?project_id={project_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2

    async def test_get_character_api(self, client, db_session):
        """测试获取人物详情 API"""
        project_id = str(uuid4())

        create_response = await client.post(
            "/api/v1/characters",
            json={
                "project_id": project_id,
                "name": "Get Test",
            },
        )

        character_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/characters/{character_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Get Test"

    async def test_update_character_api(self, client, db_session):
        """测试更新人物 API"""
        project_id = str(uuid4())

        create_response = await client.post(
            "/api/v1/characters",
            json={
                "project_id": project_id,
                "name": "Original Name",
            },
        )

        character_id = create_response.json()["id"]

        response = await client.put(
            f"/api/v1/characters/{character_id}",
            json={
                "name": "Updated Name",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    async def test_delete_character_api(self, client, db_session):
        """测试删除人物 API"""
        project_id = str(uuid4())

        create_response = await client.post(
            "/api/v1/characters",
            json={
                "project_id": project_id,
                "name": "To Delete",
            },
        )

        character_id = create_response.json()["id"]

        response = await client.delete(f"/api/v1/characters/{character_id}")

        assert response.status_code == 204

        # 验证已删除
        get_response = await client.get(f"/api/v1/characters/{character_id}")
        assert get_response.status_code == 404

    async def test_get_voice_profiles_api(self, client, db_session):
        """测试获取音色档案 API"""
        project_id = str(uuid4())

        # 创建人物
        char_response = await client.post(
            "/api/v1/characters",
            json={
                "project_id": project_id,
                "name": "Test Character",
            },
        )

        character_id = char_response.json()["id"]

        # 创建音色档案
        await client.post(
            f"/api/v1/characters/{character_id}/voice-profiles",
            json={
                "voice_id": "voice-1",
                "provider": "cosyvoice",
            },
        )

        # 获取音色档案
        response = await client.get(f"/api/v1/characters/{character_id}/voice-profiles")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
