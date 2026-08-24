"""
M14 归档配置
"""
from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class M14Config(BaseSettings):
    """M14 归档配置"""

    # 归档格式
    archive_format: str = Field(default="tar.gz", description="归档格式（tar.gz/zip）")

    # 压缩级别
    compression_level: int = Field(default=6, ge=1, le=9, description="压缩级别（1-9）")

    # 输出目录
    output_dir: str = Field(default="/tmp/filmdub_archive", description="归档输出目录")

    # 数字签名
    enable_signing: bool = Field(default=False, description="是否启用数字签名")
    signing_key_path: str = Field(default="", description="签名密钥路径")

    # 校验和算法
    checksum_algorithm: str = Field(default="sha256", description="校验和算法（md5/sha1/sha256）")

    # 临时目录
    temp_dir: str = Field(default="/tmp/filmdub_archive_temp", description="临时目录")

    # 最大归档大小（字节）
    max_archive_size: int = Field(default=10 * 1024 * 1024 * 1024, description="最大归档大小（10GB）")

    # 归档命名模式
    archive_name_pattern: str = Field(
        default="{project_id}_{timestamp}",
        description="归档文件名模式"
    )

    # 是否包含源文件
    include_source_media: bool = Field(default=False, description="是否包含原始媒体文件")

    # 是否包含中间文件
    include_intermediate_files: bool = Field(default=False, description="是否包含中间处理文件")

    model_config = ConfigDict(
        env_prefix="M14_",
        case_sensitive=False
    )
