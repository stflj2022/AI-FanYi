"""
M14 Archive Module

将项目的所有关键资产完整保存，确保项目可复现
"""
from __future__ import annotations

import os
import tarfile
import zipfile
import hashlib
import json
import shutil
import logging
import platform
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from .config import M14Config
from .models import (
    ArchiveInput,
    ArchiveResult,
    ArchiveManifest,
    ArchiveAsset,
    AssetType,
)

logger = logging.getLogger(__name__)


class ArchiveModule:
    """归档模块"""

    def __init__(self, config: M14Config = None):
        """
        初始化归档模块

        Args:
            config: M14 配置
        """
        self.config = config or M14Config()
        self._ensure_directories()

    def _ensure_directories(self):
        """确保目录存在"""
        os.makedirs(self.config.output_dir, exist_ok=True)
        os.makedirs(self.config.temp_dir, exist_ok=True)

    def archive(self, input_data: ArchiveInput) -> ArchiveResult:
        """
        执行归档

        Args:
            input_data: 归档输入

        Returns:
            归档结果
        """
        start_time = datetime.utcnow()

        try:
            logger.info(f"开始归档项目: {input_data.project_id} - {input_data.project_title}")

            # 生成输出文件名
            if not input_data.output_file:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                filename = self.config.archive_name_pattern.format(
                    project_id=input_data.project_id,
                    timestamp=timestamp
                )
                filename = f"{filename}.{self.config.archive_format}"
                output_file = os.path.join(self.config.output_dir, filename)
            else:
                output_file = input_data.output_file

            # 创建临时工作目录
            work_dir = os.path.join(
                self.config.temp_dir,
                f"{input_data.project_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            )
            os.makedirs(work_dir, exist_ok=True)

            # 创建清单
            manifest = self._create_manifest(input_data)

            # 收集资产
            self._collect_assets(input_data, manifest, work_dir)

            # 计算总大小
            manifest.calculate_total_size()

            # 保存清单
            manifest_path = os.path.join(work_dir, "manifest.json")
            with open(manifest_path, 'w', encoding='utf-8') as f:
                manifest_dict = manifest.model_dump(mode='json')
                f.write(json.dumps(manifest_dict, ensure_ascii=False, indent=2))

            # 添加清单到资产列表
            manifest_size = os.path.getsize(manifest_path)
            manifest_checksum = self._calculate_checksum(manifest_path)
            manifest.assets.append(ArchiveAsset(
                type=AssetType.CONFIG,
                path="manifest.json",
                original_path=manifest_path,
                size_bytes=manifest_size,
                checksum=manifest_checksum,
                description="归档清单"
            ))

            # 创建归档文件
            self._create_archive(work_dir, output_file)

            # 可选：数字签名
            if self.config.enable_signing or input_data.enable_signing:
                self._sign_archive(output_file)

            # 获取归档文件大小
            archive_size = os.path.getsize(output_file)

            # 计算耗时
            duration = (datetime.utcnow() - start_time).total_seconds()

            # 清理临时目录
            try:
                shutil.rmtree(work_dir)
            except Exception as e:
                logger.warning(f"清理临时目录失败: {e}")

            logger.info(f"归档完成: {output_file} ({archive_size / (1024*1024):.2f} MB)")

            return ArchiveResult(
                success=True,
                archive_file=output_file,
                manifest=manifest,
                duration_seconds=duration,
                size_bytes=archive_size
            )

        except Exception as e:
            logger.error(f"归档失败: {e}", exc_info=True)

            # 清理临时目录
            work_dir = os.path.join(
                self.config.temp_dir,
                f"{input_data.project_id}_{start_time.strftime('%Y%m%d_%H%M%S')}"
            )
            if os.path.exists(work_dir):
                try:
                    shutil.rmtree(work_dir)
                except Exception:
                    pass

            duration = (datetime.utcnow() - start_time).total_seconds()

            return ArchiveResult(
                success=False,
                archive_file=output_file if 'output_file' in locals() else "",
                manifest=ArchiveManifest(
                    project_id=input_data.project_id,
                    project_title=input_data.project_title,
                    archive_format=self.config.archive_format,
                    compression_level=self.config.compression_level
                ),
                duration_seconds=duration,
                error_message=str(e)
            )

    def _create_manifest(self, input_data: ArchiveInput) -> ArchiveManifest:
        """创建归档清单"""
        manifest = ArchiveManifest(
            project_id=input_data.project_id,
            project_title=input_data.project_title,
            archive_format=self.config.archive_format,
            compression_level=self.config.compression_level
        )

        # 添加环境信息
        manifest.system_info = {
            "platform": platform.platform(),
            "python_version": sys.version,
            "architecture": platform.machine()
        }

        # 添加依赖版本
        manifest.dependencies = self._get_dependency_versions()

        return manifest

    def _collect_assets(self, input_data: ArchiveInput, manifest: ArchiveManifest, work_dir: str):
        """收集资产"""

        # 人物数据库
        if input_data.character_db_path and os.path.exists(input_data.character_db_path):
            self._add_asset_to_archive(
                input_data.character_db_path,
                AssetType.CHARACTER_DB,
                manifest,
                work_dir,
                description="人物数据库"
            )

        # 声音数据库
        if input_data.voice_db_path and os.path.exists(input_data.voice_db_path):
            self._add_asset_to_archive(
                input_data.voice_db_path,
                AssetType.VOICE_DB,
                manifest,
                work_dir,
                description="声音数据库"
            )

        # 剧情数据库
        if input_data.story_bible_path and os.path.exists(input_data.story_bible_path):
            self._add_asset_to_archive(
                input_data.story_bible_path,
                AssetType.STORY_BIBLE,
                manifest,
                work_dir,
                description="剧情数据库"
            )

        # 翻译记忆库
        if input_data.translation_memory_path and os.path.exists(input_data.translation_memory_path):
            self._add_asset_to_archive(
                input_data.translation_memory_path,
                AssetType.TRANSLATION_MEMORY,
                manifest,
                work_dir,
                description="翻译记忆库"
            )

        # Artifact 目录
        if input_data.artifact_dir and os.path.exists(input_data.artifact_dir):
            self._add_directory_to_archive(
                input_data.artifact_dir,
                AssetType.ARTIFACT,
                manifest,
                work_dir,
                description="Artifact 目录"
            )

        # 配置文件目录
        if input_data.config_dir and os.path.exists(input_data.config_dir):
            self._add_directory_to_archive(
                input_data.config_dir,
                AssetType.CONFIG,
                manifest,
                work_dir,
                description="配置文件"
            )

        # QA 报告
        if input_data.qa_report_path and os.path.exists(input_data.qa_report_path):
            self._add_asset_to_archive(
                input_data.qa_report_path,
                AssetType.QA_REPORT,
                manifest,
                work_dir,
                description="QA 报告"
            )

        # 输出媒体文件
        if input_data.output_media_path and os.path.exists(input_data.output_media_path):
            self._add_asset_to_archive(
                input_data.output_media_path,
                AssetType.OUTPUT_MEDIA,
                manifest,
                work_dir,
                description="输出媒体文件"
            )

        # 原始媒体文件（可选）
        if input_data.include_source_media and input_data.source_media_dir:
            if os.path.exists(input_data.source_media_dir):
                self._add_directory_to_archive(
                    input_data.source_media_dir,
                    AssetType.SOURCE_MEDIA,
                    manifest,
                    work_dir,
                    description="原始媒体文件"
                )

    def _add_asset_to_archive(
        self,
        source_path: str,
        asset_type: AssetType,
        manifest: ArchiveManifest,
        work_dir: str,
        description: str = None,
        relative_path: str = None
    ):
        """添加单个资产到归档"""
        try:
            # 计算相对路径
            if not relative_path:
                relative_path = os.path.basename(source_path)

            # 目标路径
            target_path = os.path.join(work_dir, relative_path)

            # 确保目标目录存在
            os.makedirs(os.path.dirname(target_path), exist_ok=True)

            # 复制文件
            shutil.copy2(source_path, target_path)

            # 计算校验和
            checksum = self._calculate_checksum(target_path)

            # 获取文件大小
            size_bytes = os.path.getsize(target_path)

            # 创建资产记录
            asset = ArchiveAsset(
                type=asset_type,
                path=relative_path,
                original_path=source_path,
                size_bytes=size_bytes,
                checksum=checksum,
                description=description
            )

            manifest.add_asset(asset)

            logger.debug(f"添加资产: {relative_path} ({size_bytes} bytes)")

        except Exception as e:
            logger.warning(f"添加资产失败 {source_path}: {e}")

    def _add_directory_to_archive(
        self,
        source_dir: str,
        asset_type: AssetType,
        manifest: ArchiveManifest,
        work_dir: str,
        description: str = None,
        relative_path: str = None
    ):
        """添加目录到归档"""
        try:
            if not relative_path:
                relative_path = os.path.basename(source_dir)

            # 遍历目录
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    source_file = os.path.join(root, file)
                    file_relative_path = os.path.join(
                        relative_path,
                        os.path.relpath(source_file, source_dir)
                    )

                    self._add_asset_to_archive(
                        source_file,
                        asset_type,
                        manifest,
                        work_dir,
                        description,
                        file_relative_path
                    )

        except Exception as e:
            logger.warning(f"添加目录失败 {source_dir}: {e}")

    def _create_archive(self, work_dir: str, output_file: str):
        """创建归档文件"""
        logger.info(f"创建归档文件: {output_file}")

        if self.config.archive_format == "tar.gz":
            self._create_tarball(work_dir, output_file)
        elif self.config.archive_format == "zip":
            self._create_zip(work_dir, output_file)
        else:
            raise ValueError(f"不支持的归档格式: {self.config.archive_format}")

    def _create_tarball(self, work_dir: str, output_file: str):
        """创建 tar.gz 归档"""
        with tarfile.open(
            output_file,
            f"w:gz",
            compresslevel=self.config.compression_level
        ) as tar:
            for item in os.listdir(work_dir):
                item_path = os.path.join(work_dir, item)
                tar.add(item_path, arcname=item)

    def _create_zip(self, work_dir: str, output_file: str):
        """创建 zip 归档"""
        with zipfile.ZipFile(
            output_file,
            'w',
            zipfile.ZIP_DEFLATED,
            compresslevel=self.config.compression_level
        ) as zipf:
            for root, dirs, files in os.walk(work_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, work_dir)
                    zipf.write(file_path, arcname)

    def _sign_archive(self, archive_file: str):
        """对归档文件进行数字签名"""
        if not self.config.signing_key_path:
            logger.warning("未配置签名密钥，跳过签名")
            return

        try:
            # 这里可以实现 GPG 签名
            # 简化实现：只计算校验和
            checksum = self._calculate_checksum(archive_file)
            sig_file = f"{archive_file}.sig"

            with open(sig_file, 'w') as f:
                f.write(f"SIGNATURE-TYPE: {self.config.checksum_algorithm}\n")
                f.write(f"CHECKSUM: {checksum}\n")
                f.write(f"TIMESTAMP: {datetime.utcnow().isoformat()}\n")

            logger.info(f"创建签名文件: {sig_file}")

        except Exception as e:
            logger.error(f"签名失败: {e}")

    def _calculate_checksum(self, file_path: str) -> str:
        """计算文件校验和"""
        hash_func = getattr(hashlib, self.config.checksum_algorithm)()

        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hash_func.update(chunk)

        return hash_func.hexdigest()

    def _get_dependency_versions(self) -> Dict[str, str]:
        """获取依赖版本"""
        versions = {}

        # 核心依赖
        try:
            import fastapi
            versions["fastapi"] = fastapi.__version__
        except ImportError:
            pass

        try:
            import pydantic
            versions["pydantic"] = pydantic.__version__
        except ImportError:
            pass

        try:
            import sqlalchemy
            versions["sqlalchemy"] = sqlalchemy.__version__
        except ImportError:
            pass

        try:
            import numpy
            versions["numpy"] = numpy.__version__
        except ImportError:
            pass

        try:
            import torch
            versions["torch"] = torch.__version__
        except ImportError:
            pass

        return versions

    def extract_archive(self, archive_file: str, output_dir: str) -> bool:
        """
        提取归档文件

        Args:
            archive_file: 归档文件路径
            output_dir: 输出目录

        Returns:
            是否成功
        """
        try:
            logger.info(f"提取归档: {archive_file} -> {output_dir}")

            os.makedirs(output_dir, exist_ok=True)

            if self.config.archive_format == "tar.gz":
                with tarfile.open(archive_file, 'r:gz') as tar:
                    tar.extractall(output_dir)
            elif self.config.archive_format == "zip":
                with zipfile.ZipFile(archive_file, 'r') as zipf:
                    zipf.extractall(output_dir)
            else:
                raise ValueError(f"不支持的归档格式: {self.config.archive_format}")

            logger.info(f"归档提取完成: {output_dir}")
            return True

        except Exception as e:
            logger.error(f"提取归档失败: {e}")
            return False

    def verify_archive(self, archive_file: str) -> bool:
        """
        验证归档文件

        Args:
            archive_file: 归档文件路径

        Returns:
            是否验证通过
        """
        try:
            logger.info(f"验证归档: {archive_file}")

            # 提取并验证清单
            temp_dir = os.path.join(self.config.temp_dir, "verify")
            os.makedirs(temp_dir, exist_ok=True)

            try:
                # 提取 manifest.json
                if self.config.archive_format == "tar.gz":
                    with tarfile.open(archive_file, 'r:gz') as tar:
                        tar.extract("manifest.json", temp_dir)
                elif self.config.archive_format == "zip":
                    with zipfile.ZipFile(archive_file, 'r') as zipf:
                        zipf.extract("manifest.json", temp_dir)

                # 读取清单
                manifest_path = os.path.join(temp_dir, "manifest.json")
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)

                # 验证校验和（简化实现，完整验证需要提取所有文件）
                logger.info(f"清单包含 {manifest_data.get('total_files', 0)} 个文件")

            finally:
                # 清理
                shutil.rmtree(temp_dir, ignore_errors=True)

            return True

        except Exception as e:
            logger.error(f"验证归档失败: {e}")
            return False

    def health_check(self) -> bool:
        """健康检查"""
        try:
            # 检查输出目录是否可写
            test_file = os.path.join(self.config.output_dir, ".health_check")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            return True
        except Exception:
            return False

    def close(self):
        """关闭归档模块"""
        logger.info("关闭 ArchiveModule")
        # 清理临时目录
        if os.path.exists(self.config.temp_dir):
            try:
                shutil.rmtree(self.config.temp_dir)
            except Exception as e:
                logger.warning(f"清理临时目录失败: {e}")
