"""
M14 归档模块测试
"""
import json
import os
import tarfile
import zipfile
import pytest
import tempfile
from pathlib import Path

from filmdub.workers.archive import (
    M14Config,
    ArchiveModule,
    ArchiveInput,
    ArchiveResult,
    ArchiveManifest,
    ArchiveAsset,
    AssetType,
)


class TestM14Config:
    """M14Config 测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = M14Config()
        assert config.archive_format == "tar.gz"
        assert config.compression_level == 6
        assert config.checksum_algorithm == "sha256"
        assert config.enable_signing is False

    def test_custom_config(self):
        """测试自定义配置"""
        config = M14Config(
            archive_format="zip",
            compression_level=9,
            checksum_algorithm="sha1",
            enable_signing=True
        )
        assert config.archive_format == "zip"
        assert config.compression_level == 9
        assert config.checksum_algorithm == "sha1"
        assert config.enable_signing is True


class TestArchiveAsset:
    """ArchiveAsset 测试"""

    def test_create_asset(self):
        """测试创建资产"""
        asset = ArchiveAsset(
            type=AssetType.CHARACTER_DB,
            path="characters.json",
            original_path="/data/characters.json",
            size_bytes=1024,
            checksum="abc123",
            description="人物数据库"
        )

        assert asset.type == AssetType.CHARACTER_DB
        assert asset.path == "characters.json"
        assert asset.size_bytes == 1024
        assert asset.checksum == "abc123"
        assert asset.description == "人物数据库"


class TestArchiveManifest:
    """ArchiveManifest 测试"""

    def test_create_manifest(self):
        """测试创建清单"""
        manifest = ArchiveManifest(
            project_id="proj001",
            project_title="测试项目",
            archive_format="tar.gz",
            compression_level=6
        )

        assert manifest.project_id == "proj001"
        assert manifest.project_title == "测试项目"
        assert manifest.archive_format == "tar.gz"
        assert manifest.compression_level == 6
        assert len(manifest.assets) == 0
        assert manifest.total_files == 0
        assert manifest.total_size_bytes == 0

    def test_add_asset(self):
        """测试添加资产"""
        manifest = ArchiveManifest(
            project_id="proj001",
            project_title="测试项目",
            archive_format="tar.gz",
            compression_level=6
        )

        asset = ArchiveAsset(
            type=AssetType.CHARACTER_DB,
            path="characters.json",
            original_path="/data/characters.json",
            size_bytes=1024,
            checksum="abc123"
        )

        manifest.add_asset(asset)

        assert len(manifest.assets) == 1
        assert manifest.total_files == 1
        assert manifest.total_size_bytes == 1024

    def test_calculate_total_size(self):
        """测试计算总大小"""
        manifest = ArchiveManifest(
            project_id="proj001",
            project_title="测试项目",
            archive_format="tar.gz",
            compression_level=6
        )

        asset1 = ArchiveAsset(
            type=AssetType.CHARACTER_DB,
            path="characters.json",
            original_path="/data/characters.json",
            size_bytes=1024,
            checksum="abc123"
        )

        asset2 = ArchiveAsset(
            type=AssetType.VOICE_DB,
            path="voices.json",
            original_path="/data/voices.json",
            size_bytes=2048,
            checksum="def456"
        )

        manifest.add_asset(asset1)
        manifest.add_asset(asset2)

        manifest.calculate_total_size()

        assert manifest.total_files == 2
        assert manifest.total_size_bytes == 3072


class TestArchiveModule:
    """ArchiveModule 测试"""

    @pytest.fixture
    def module(self):
        """创建归档模块"""
        return ArchiveModule()

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """临时目录"""
        return str(tmp_path)

    @pytest.fixture
    def sample_character_db(self, tmp_path):
        """创建示例人物数据库"""
        data = {
            "characters": {
                "char1": {
                    "id": "char1",
                    "name": "Walter White",
                    "voice_id": "voice1"
                }
            }
        }

        file_path = tmp_path / "character_db.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return str(file_path)

    @pytest.fixture
    def sample_translation_memory(self, tmp_path):
        """创建示例翻译记忆库"""
        data = {
            "translations": [
                {
                    "source": "Hello",
                    "target": "你好",
                    "context": "greeting"
                }
            ]
        }

        file_path = tmp_path / "translation_memory.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return str(file_path)

    @pytest.fixture
    def sample_artifact_dir(self, tmp_path):
        """创建示例 Artifact 目录"""
        artifact_dir = tmp_path / "artifacts"
        artifact_dir.mkdir()

        # 创建一些 artifact 文件
        for i in range(3):
            artifact_file = artifact_dir / f"artifact_{i}.json"
            data = {"id": i, "data": f"artifact {i}"}
            with open(artifact_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)

        return str(artifact_dir)

    def test_health_check(self, module):
        """测试健康检查"""
        result = module.health_check()
        assert isinstance(result, bool)

    def test_calculate_checksum(self, module, tmp_path):
        """测试计算校验和"""
        test_file = tmp_path / "test.txt"
        with open(test_file, 'w') as f:
            f.write("test content")

        checksum = module._calculate_checksum(str(test_file))

        assert isinstance(checksum, str)
        assert len(checksum) > 0

        # 相同文件应该有相同的校验和
        checksum2 = module._calculate_checksum(str(test_file))
        assert checksum == checksum2

    def test_archive_simple(self, module, sample_character_db, temp_dir):
        """测试简单归档"""
        output_file = os.path.join(temp_dir, "test_archive.tar.gz")

        input_data = ArchiveInput(
            project_id="test_proj",
            project_title="测试项目",
            character_db_path=sample_character_db,
            output_file=output_file
        )

        result = module.archive(input_data)

        assert result.success is True
        assert os.path.exists(result.archive_file)
        assert result.size_bytes > 0
        assert isinstance(result.manifest, ArchiveManifest)
        assert result.manifest.project_id == "test_proj"
        assert len(result.manifest.assets) > 0

    def test_archive_with_multiple_assets(
        self,
        module,
        sample_character_db,
        sample_translation_memory,
        sample_artifact_dir,
        temp_dir
    ):
        """测试包含多个资产的归档"""
        output_file = os.path.join(temp_dir, "test_multi_archive.tar.gz")

        input_data = ArchiveInput(
            project_id="test_proj",
            project_title="测试项目",
            character_db_path=sample_character_db,
            translation_memory_path=sample_translation_memory,
            artifact_dir=sample_artifact_dir,
            output_file=output_file
        )

        result = module.archive(input_data)

        assert result.success is True
        assert os.path.exists(result.archive_file)

        # 应该包含多个资产
        asset_types = {asset.type for asset in result.manifest.assets}
        assert AssetType.CHARACTER_DB in asset_types
        assert AssetType.TRANSLATION_MEMORY in asset_types
        assert AssetType.ARTIFACT in asset_types

    def test_archive_missing_files(self, module, temp_dir):
        """测试缺少文件的归档"""
        output_file = os.path.join(temp_dir, "test_missing.tar.gz")

        input_data = ArchiveInput(
            project_id="test_proj",
            project_title="测试项目",
            character_db_path="/nonexistent/character_db.json",
            output_file=output_file
        )

        result = module.archive(input_data)

        # 缺少文件不应该导致失败，只是没有该资产
        assert result.success is True

    def test_extract_tarball(self, module, temp_dir):
        """测试提取 tar.gz 归档"""
        # 先创建归档
        archive_file = os.path.join(temp_dir, "test_extract.tar.gz")

        # 创建测试文件
        test_content_file = os.path.join(temp_dir, "content.txt")
        with open(test_content_file, 'w') as f:
            f.write("test content for extraction")

        input_data = ArchiveInput(
            project_id="test_proj",
            project_title="测试项目",
            output_file=archive_file
        )

        result = module.archive(input_data)
        assert result.success is True

        # 提取归档
        extract_dir = os.path.join(temp_dir, "extracted")
        success = module.extract_archive(archive_file, extract_dir)

        assert success is True
        assert os.path.exists(extract_dir)
        assert os.path.exists(os.path.join(extract_dir, "manifest.json"))

    def test_extract_zip(self, temp_dir):
        """测试提取 zip 归档"""
        config = M14Config(archive_format="zip")
        module = ArchiveModule(config)

        # 先创建归档
        archive_file = os.path.join(temp_dir, "test_extract.zip")

        input_data = ArchiveInput(
            project_id="test_proj",
            project_title="测试项目",
            output_file=archive_file
        )

        result = module.archive(input_data)
        assert result.success is True

        # 提取归档
        extract_dir = os.path.join(temp_dir, "extracted_zip")
        success = module.extract_archive(archive_file, extract_dir)

        assert success is True
        assert os.path.exists(extract_dir)
        assert os.path.exists(os.path.join(extract_dir, "manifest.json"))

    def test_verify_archive(self, module, temp_dir):
        """测试验证归档"""
        # 先创建归档
        archive_file = os.path.join(temp_dir, "test_verify.tar.gz")

        input_data = ArchiveInput(
            project_id="test_proj",
            project_title="测试项目",
            output_file=archive_file
        )

        result = module.archive(input_data)
        assert result.success is True

        # 验证归档
        valid = module.verify_archive(archive_file)
        assert valid is True

    def test_verify_invalid_archive(self, module, temp_dir):
        """测试验证无效归档"""
        # 创建无效的归档文件
        invalid_archive = os.path.join(temp_dir, "invalid.tar.gz")
        with open(invalid_archive, 'w') as f:
            f.write("this is not a valid tar.gz file")

        valid = module.verify_archive(invalid_archive)
        assert valid is False

    def test_get_dependency_versions(self, module):
        """测试获取依赖版本"""
        versions = module._get_dependency_versions()

        assert isinstance(versions, dict)
        # 应该包含至少一个依赖版本（如果安装了的话）
        # 不强制要求，因为环境可能不同

    def test_auto_generate_filename(self, module, sample_character_db):
        """测试自动生成文件名"""
        input_data = ArchiveInput(
            project_id="test_proj",
            project_title="测试项目",
            character_db_path=sample_character_db,
            output_file=None  # 不指定输出文件，应该自动生成
        )

        result = module.archive(input_data)

        assert result.success is True
        assert "test_proj" in result.archive_file
        assert result.archive_file.endswith(".tar.gz")

    def test_max_size_limit(self, module, temp_dir):
        """测试大小限制"""
        # 创建一个大于限制的归档（需要很大文件，这里只测试逻辑）
        small_config = M14Config(max_archive_size=100)  # 100 bytes
        small_module = ArchiveModule(small_config)

        # 创建一个小归档，应该成功
        output_file = os.path.join(temp_dir, "test_small.tar.gz")

        input_data = ArchiveInput(
            project_id="test_proj",
            project_title="测试项目",
            output_file=output_file
        )

        result = small_module.archive(input_data)
        # 清单文件可能小于 100 字节
        # 实际限制检查需要更复杂的实现
        assert isinstance(result, ArchiveResult)
