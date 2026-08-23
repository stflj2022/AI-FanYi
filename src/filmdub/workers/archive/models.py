"""
M14 归档数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AssetType(str, Enum):
    """资产类型"""
    CHARACTER_DB = "character_db"  # 人物数据库
    VOICE_DB = "voice_db"  # 声音数据库
    STORY_BIBLE = "story_bible"  # 剧情数据库
    TRANSLATION_MEMORY = "translation_memory"  # 翻译记忆库
    ARTIFACT = "artifact"  # Artifact
    CONFIG = "config"  # 配置文件
    QA_REPORT = "qa_report"  # QA 报告
    MODEL_VERSION = "model_version"  # 模型版本信息
    SOURCE_MEDIA = "source_media"  # 原始媒体文件
    OUTPUT_MEDIA = "output_media"  # 输出媒体文件
    INTERMEDIATE_FILE = "intermediate_file"  # 中间文件
    OTHER = "other"  # 其他


class ArchiveAsset(BaseModel):
    """归档资产"""
    type: AssetType = Field(..., description="资产类型")
    path: str = Field(..., description="资产路径（相对路径）")
    original_path: str = Field(..., description="原始路径")
    size_bytes: int = Field(default=0, description="文件大小（字节）")
    checksum: str = Field(..., description="文件校验和")
    description: Optional[str] = Field(default=None, description="资产描述")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="额外元数据")


class ArchiveManifest(BaseModel):
    """归档清单"""
    version: str = Field(default="1.0", description="清单版本")
    project_id: str = Field(..., description="项目 ID")
    project_title: str = Field(..., description="项目标题")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")

    # 归档信息
    archive_format: str = Field(..., description="归档格式")
    compression_level: int = Field(..., description="压缩级别")
    total_size_bytes: int = Field(default=0, description="总大小（字节）")
    total_files: int = Field(default=0, description="文件总数")

    # 资产列表
    assets: List[ArchiveAsset] = Field(default_factory=list, description="资产列表")

    # 环境信息
    python_version: Optional[str] = Field(default=None, description="Python 版本")
    dependencies: Optional[Dict[str, str]] = Field(default=None, description="依赖版本")
    system_info: Optional[Dict[str, str]] = Field(default=None, description="系统信息")

    # 工作流信息
    workflow_version: Optional[str] = Field(default=None, description="工作流版本")
    orchestrator_version: Optional[str] = Field(default=None, description="编排器版本")

    # 签名
    signature: Optional[str] = Field(default=None, description="数字签名")
    signing_key_id: Optional[str] = Field(default=None, description="签名密钥 ID")

    # 备注
    notes: Optional[str] = Field(default=None, description="备注信息")

    def add_asset(self, asset: ArchiveAsset):
        """添加资产"""
        self.assets.append(asset)
        self.total_size_bytes += asset.size_bytes
        self.total_files += 1

    def calculate_total_size(self):
        """计算总大小"""
        self.total_size_bytes = sum(a.size_bytes for a in self.assets)
        self.total_files = len(self.assets)


class ArchiveResult(BaseModel):
    """归档结果"""
    success: bool = Field(..., description="是否成功")
    archive_file: str = Field(..., description="归档文件路径")
    manifest: ArchiveManifest = Field(..., description="归档清单")
    duration_seconds: float = Field(default=0.0, description="耗时（秒）")
    size_bytes: int = Field(default=0, description="归档文件大小（字节）")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")


class ArchiveInput(BaseModel):
    """归档输入"""
    project_id: str = Field(..., description="项目 ID")
    project_title: str = Field(..., description="项目标题")

    # 资产路径
    character_db_path: Optional[str] = Field(default=None, description="人物数据库路径")
    voice_db_path: Optional[str] = Field(default=None, description="声音数据库路径")
    story_bible_path: Optional[str] = Field(default=None, description="剧情数据库路径")
    translation_memory_path: Optional[str] = Field(default=None, description="翻译记忆库路径")
    artifact_dir: Optional[str] = Field(default=None, description="Artifact 目录")
    config_dir: Optional[str] = Field(default=None, description="配置文件目录")
    qa_report_path: Optional[str] = Field(default=None, description="QA 报告路径")
    source_media_dir: Optional[str] = Field(default=None, description="原始媒体文件目录")
    output_media_path: Optional[str] = Field(default=None, description="输出媒体文件路径")

    # 输出
    output_file: Optional[str] = Field(default=None, description="输出文件路径")

    # 选项
    include_source_media: bool = Field(default=False, description="是否包含原始媒体")
    include_intermediate_files: bool = Field(default=False, description="是否包含中间文件")
    enable_signing: bool = Field(default=False, description="是否启用签名")
