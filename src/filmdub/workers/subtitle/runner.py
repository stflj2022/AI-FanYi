"""
Module 03 主工作器 - Subtitle Runner
"""

import logging
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import asdict

from .config import SubtitleConfig, TranslationMode
from .models import SubtitleSource, Dialogue, SubtitleSourceType
from .init_db import init_subtitle_db
from .discovery import SubtitleScanner, SubtitleMatcher
from .importer import SubtitleParser, DialogueNormalizer
from .validator import SubtitleValidator, ValidationSeverity
from .alignment import SubtitleAligner
from .extractor import DialogueExtractor, DialogueType
from .manifest import DialogueManifestBuilder

logger = logging.getLogger(__name__)


class SubtitleRunner:
    """字幕与对话获取工作器"""

    def __init__(self, project_id: str, config: Optional[SubtitleConfig] = None):
        """
        初始化工作器

        Args:
            project_id: 项目ID
            config: 字幕配置
        """
        self.project_id = project_id
        self.config = config or SubtitleConfig()

        # 获取项目路径
        self.project_dir = Path(f"data/projects/{project_id}")
        self.db_path = self.project_dir / "database.sqlite"
        self.dialogue_dir = self.project_dir / "dialogue"

        # 初始化子模块
        self.scanner = SubtitleScanner(self.config)
        self.matcher = SubtitleMatcher(self.config)
        self.parser = SubtitleParser()
        self.validator = SubtitleValidator(self.config)
        self.aligner = SubtitleAligner(self.config)
        self.extractor = DialogueExtractor(self.config)
        self.manifest_builder = DialogueManifestBuilder(project_id, episode_id="")

        # 执行步骤
        self.steps: List[Dict[str, Any]] = []

        # 状态
        self.episode_id: str = ""
        self.english_subtitle: Optional[SubtitleSource] = None
        self.chinese_subtitle: Optional[SubtitleSource] = None
        self.dialogues: List[Dialogue] = []

        self._explicit_subtitles: Dict[str, Optional[Path]] = {"en": None, "zh": None}
        self._auto_subtitles: List[Path] = []
        self._entry_cache: Dict[str, tuple] = {}

    def run(
        self,
        video_path: Path,
        subtitle_en: Optional[Path] = None,
        subtitle_zh: Optional[Path] = None,
        subtitle_auto: Optional[List[Path]] = None,
    ) -> Dict[str, Any]:
        """
        执行完整的字幕处理流程

        Args:
            video_path: 视频文件路径
            subtitle_en: 外挂英文字幕文件（优先级最高）
            subtitle_zh: 外挂中文字幕文件（优先级最高）
            subtitle_auto: 外挂字幕文件列表，按文件名自动识别语言，
                           单个双语文件会被自动拆分为中英两路

        Returns:
            执行结果
        """
        start_time = datetime.utcnow()
        logger.info(f"Starting Subtitle Runner for project {self.project_id}")

        self._explicit_subtitles = {"en": subtitle_en, "zh": subtitle_zh}
        self._auto_subtitles = list(subtitle_auto or [])

        try:
            # 1. 初始化数据库
            self._init_database()

            # 2. 字幕发现
            subtitle_summary = self._step_discovery(video_path)
            self._determine_strategy(subtitle_summary)

            # 3. 字幕导入（英文）
            if self.english_subtitle:
                english_entries = self._step_import_subtitle(self.english_subtitle, "en")
            else:
                english_entries = []
                logger.warning("No English subtitle found")

            # 4. 字幕导入（中文）
            if self.chinese_subtitle:
                chinese_entries = self._step_import_subtitle(self.chinese_subtitle, "zh-CN")
            else:
                chinese_entries = []

            # 5. 字幕验证
            if english_entries:
                validation_report = self._step_validate(english_entries, video_path)
            else:
                validation_report = None

            # 6. 字幕对齐
            if english_entries:
                alignment_result = self._step_align(
                    english_entries,
                    chinese_entries if chinese_entries else None
                )
            else:
                alignment_result = None

            # 7. 对白提取
            if english_entries:
                dialogues = self._step_extract_dialogues(english_entries)
            else:
                dialogues = []

            # 8. 处理中文翻译
            if chinese_entries:
                self._step_merge_chinese(dialogues, chinese_entries)
            else:
                # TODO: 启动 Qwen 翻译（下一步实现）
                logger.info("No Chinese subtitle, translation would be needed")

            self.dialogues = dialogues

            # 9. 保存数据
            self._save_data(dialogues)

            # 10. 生成清单
            manifest = self._generate_manifest()

            # 更新项目状态
            self._update_project_status("READY_FOR_AUDIO")

            duration = (datetime.utcnow() - start_time).total_seconds()

            return {
                "status": "success",
                "duration": duration,
                "manifest": manifest,
                "steps": self.steps
            }

        except Exception as e:
            logger.error(f"Subtitle Runner failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "steps": self.steps
            }

    def _init_database(self) -> None:
        """初始化数据库"""
        step_start = datetime.utcnow()

        try:
            init_subtitle_db(str(self.db_path))
            logger.info("Subtitle database initialized")

            duration = (datetime.utcnow() - step_start).total_seconds()
            self.steps.append(self.manifest_builder.create_step_result(
                "init_database", "success", duration
            ))

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def _step_discovery(self, video_path: Path) -> Dict[str, Any]:
        """步骤1：字幕发现"""
        step_start = datetime.utcnow()

        try:
            # 扫描视频内嵌字幕
            embedded_tracks = self.scanner.scan_video_subtitles(video_path)

            # 扫描外部字幕
            external_subtitles = self.scanner.scan_external_subtitles(video_path)

            # 获取视频时长
            import subprocess
            cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                   '-of', 'json', str(video_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            video_duration = float(json.loads(result.stdout)['format']['duration'])

            summary = self.scanner.get_subtitle_summary(video_path)
            summary['video_duration'] = video_duration

            duration = (datetime.utcnow() - step_start).total_seconds()
            self.steps.append(self.manifest_builder.create_step_result(
                "subtitle_discovery", "success", duration,
                {"embedded_count": len(embedded_tracks), "external_count": len(external_subtitles)}
            ))

            return summary

        except Exception as e:
            logger.error(f"Subtitle discovery failed: {e}")
            raise

    def _determine_strategy(self, summary: Dict[str, Any]) -> None:
        """确定处理策略。

        外挂字幕先于内嵌轨接入并占位；内嵌轨仅补空槽，不覆盖外挂来源。
        """
        self._wire_external_sources(summary)

        # 检查中文字幕
        has_chinese = bool(self.chinese_subtitle) or summary.get('has_chinese_subtitle', False)
        has_english = bool(self.english_subtitle) or summary.get('has_english_subtitle', False)

        if has_chinese:
            self.config.translation_mode = TranslationMode.EXISTING_CHINESE
            logger.info("Strategy: Using existing Chinese subtitle")
        elif has_english:
            self.config.translation_mode = TranslationMode.QWEN_TRANSLATION
            logger.info("Strategy: Will use Qwen translation")
        else:
            self.config.translation_mode = TranslationMode.ASR
            logger.info("Strategy: Will use ASR")

        # 记录字幕来源
        for track in summary.get('embedded_subtitles', {}).get('tracks', []):
            if track['language'] == 'en' and not self.english_subtitle:
                self.english_subtitle = SubtitleSource(
                    id=f"sub_emb_{track['index']}",
                    project_id=self.project_id,
                    media_id="video",  # TODO: 从数据库获取
                    language=track['language'],
                    source_type=SubtitleSourceType.EMBEDDED,
                    stream_index=track['index'],
                    format=track.get('codec', 'srt')
                )
            elif track['language'] == 'zh-CN' and not self.chinese_subtitle:
                self.chinese_subtitle = SubtitleSource(
                    id=f"sub_emb_{track['index']}",
                    project_id=self.project_id,
                    media_id="video",
                    language=track['language'],
                    source_type=SubtitleSourceType.EMBEDDED,
                    stream_index=track['index'],
                    format=track.get('codec', 'srt')
                )

        self._wire_external_sources(summary)

    def _wire_external_sources(self, summary: Dict[str, Any]) -> None:
        """按优先级接入外挂字幕：显式指定 > 命令行自动识别 > 同名自动发现"""
        slots = {"en": ("english_subtitle", "en"), "zh": ("chinese_subtitle", "zh-CN")}

        for key, path in self._explicit_subtitles.items():
            if not path:
                continue
            attr, language = slots[key]
            setattr(self, attr, self._make_external_source(Path(path), language))

        for path in self._auto_subtitles:
            guessed = self.scanner._guess_language_from_filename(Path(path).name)
            if guessed == 'zh-CN' and not self.chinese_subtitle:
                self.chinese_subtitle = self._make_external_source(Path(path), 'zh-CN')
            elif not self.english_subtitle:
                self.english_subtitle = self._make_external_source(
                    Path(path), guessed or 'en'
                )

        for f in summary.get('external_subtitles', {}).get('files', []):
            lang = f.get('language')
            if lang == 'en' and not self.english_subtitle:
                self.english_subtitle = self._make_external_source(
                    Path(f['path']), 'en', fmt=f['format']
                )
            elif lang == 'zh-CN' and not self.chinese_subtitle:
                self.chinese_subtitle = self._make_external_source(
                    Path(f['path']), 'zh-CN', fmt=f['format']
                )

        if (self.chinese_subtitle and not self.english_subtitle
                and self.chinese_subtitle.source_type == SubtitleSourceType.EXTERNAL):
            logger.info("Chinese-only external subtitle given; "
                        "mirroring as English source for bilingual split")
            self.english_subtitle = self.chinese_subtitle

    def _make_external_source(
        self, path: Path, language: str, fmt: Optional[str] = None
    ) -> SubtitleSource:
        return SubtitleSource(
            id=f"sub_ext_{language}_{abs(hash(str(path))) % 100000}",
            project_id=self.project_id,
            media_id="video",
            language=language,
            source_type=SubtitleSourceType.EXTERNAL,
            path=str(path),
            format=(fmt or path.suffix.lstrip('.')).lower(),
        )

    def _step_import_subtitle(
        self,
        subtitle_source: SubtitleSource,
        language: str
    ) -> List:
        """步骤2：导入字幕"""
        step_start = datetime.utcnow()

        try:
            if subtitle_source.source_type == SubtitleSourceType.EMBEDDED:
                # 提取内嵌字幕
                video_path = self.project_dir / "media" / "source.mkv"  # TODO: 获取实际路径
                output_path = self.dialogue_dir / "source" / f"{language}.srt"
                output_path.parent.mkdir(parents=True, exist_ok=True)

                success = self.scanner.extract_embedded_subtitle(
                    video_path, subtitle_source.stream_index, output_path
                )
                if not success:
                    raise Exception(f"Failed to extract subtitle {subtitle_source.id}")

                subtitle_source.path = str(output_path)

            # 解析字幕
            entries = self._load_entries(subtitle_source.path, language)

            # 保存为 JSONL
            jsonl_path = self.dialogue_dir / "source" / f"{language}.jsonl"
            self.parser.to_jsonl(entries, jsonl_path, language)

            duration = (datetime.utcnow() - step_start).total_seconds()
            self.steps.append(self.manifest_builder.create_step_result(
                f"import_{language}_subtitle", "success", duration,
                {"entry_count": len(entries)}
            ))

            return entries

        except Exception as e:
            logger.error(f"Failed to import {language} subtitle: {e}")
            self.steps.append(self.manifest_builder.create_step_result(
                f"import_{language}_subtitle", "failed",
                (datetime.utcnow() - step_start).total_seconds(),
                {"error": str(e)}
            ))
            raise

    def _load_entries(self, path: str, language: str) -> List:
        """加载字幕条目；双语文件按语言拆分，解析结果按路径缓存"""
        key = str(path)
        if key not in self._entry_cache:
            parsed = self.parser.parse(Path(key))
            self._entry_cache[key] = (parsed, self.parser.split_bilingual(parsed))

        parsed, (en_part, zh_part) = self._entry_cache[key]
        if language == 'zh-CN':
            return zh_part or parsed
        if language == 'en':
            return en_part or parsed
        return parsed

    def _step_validate(
        self,
        entries: List,
        video_path: Path
    ) -> Dict[str, Any]:
        """步骤3：验证字幕"""
        step_start = datetime.utcnow()

        try:
            report = self.validator.validate(entries)

            duration = (datetime.utcnow() - step_start).total_seconds()
            self.steps.append(self.manifest_builder.create_step_result(
                "validate_subtitle", "success", duration,
                {
                    "total": report.total_entries,
                    "valid": report.valid_entries,
                    "errors": report.error_count,
                    "warnings": report.warning_count,
                    "quality_score": report.quality_score
                }
            ))

            return asdict(report)

        except Exception as e:
            logger.error(f"Subtitle validation failed: {e}")
            raise

    def _step_align(
        self,
        english_entries: List,
        chinese_entries: Optional[List]
    ) -> Dict[str, Any]:
        """步骤4：对齐字幕"""
        step_start = datetime.utcnow()

        try:
            # 获取视频时长
            video_duration = english_entries[-1].end if english_entries else 0

            result = self.aligner.align(english_entries, video_duration, chinese_entries)

            duration = (datetime.utcnow() - step_start).total_seconds()
            self.steps.append(self.manifest_builder.create_step_result(
                "align_subtitle", "success", duration,
                {
                    "method": result.method,
                    "offset": result.offset,
                    "scale": result.scale,
                    "confidence": result.confidence
                }
            ))

            return asdict(result)

        except Exception as e:
            logger.error(f"Subtitle alignment failed: {e}")
            raise

    def _step_extract_dialogues(self, entries: List) -> List[Dialogue]:
        """步骤5：提取对话"""
        step_start = datetime.utcnow()

        try:
            dialogue_items = self.extractor.extract(entries)

            # 过滤出有效的对话
            valid_dialogues = self.extractor.filter_dialogues(
                dialogue_items,
                include_types=[DialogueType.DIALOGUE]
            )

            # 转换为 Dialogue 模型
            dialogues = []
            for item in valid_dialogues:
                dialogue = Dialogue(
                    id=item.id,
                    episode_id=self.episode_id or "S01E01",  # TODO: 获取实际剧集ID
                    start=item.start,
                    end=item.end,
                    source_text=item.text,
                    normalized_text=item.normalized_text,
                    speaker_id=None,  # Module 05/06 填充
                    character_id=None,  # Module 05/06 填充
                    candidate_character=item.speaker_hint,
                    emotion_hint=item.emotion_hint,
                    dialogue_type=item.dialogue_type.value
                )
                dialogues.append(dialogue)

            duration = (datetime.utcnow() - step_start).total_seconds()
            self.steps.append(self.manifest_builder.create_step_result(
                "extract_dialogues", "success", duration,
                {"dialogue_count": len(dialogues)}
            ))

            return dialogues

        except Exception as e:
            logger.error(f"Dialogue extraction failed: {e}")
            raise

    def _step_merge_chinese(
        self,
        dialogues: List[Dialogue],
        chinese_entries: List
    ) -> None:
        """步骤6：合并中文翻译"""
        step_start = datetime.utcnow()

        try:
            # 简单映射：按时间戳匹配
            for dialogue in dialogues:
                for chinese_entry in chinese_entries:
                    # 检查时间戳是否重叠
                    if (chinese_entry.start <= dialogue.end and
                        chinese_entry.end >= dialogue.start):
                        dialogue.translated_text = chinese_entry.text
                        dialogue.translation_source = "existing_subtitle"
                        break

            duration = (datetime.utcnow() - step_start).total_seconds()
            self.steps.append(self.manifest_builder.create_step_result(
                "merge_chinese", "success", duration,
                {"translated_count": sum(1 for d in dialogues if d.translated_text)}
            ))

        except Exception as e:
            logger.error(f"Failed to merge Chinese: {e}")
            raise

    def _save_data(self, dialogues: List[Dialogue]) -> None:
        """保存数据到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 保存对话
            for dialogue in dialogues:
                cursor.execute("""
                    INSERT OR REPLACE INTO dialogues
                    (id, episode_id, start, end, source_text, normalized_text,
                     translated_text, source_language, target_language, speaker_id,
                     character_id, candidate_character, dialogue_type, emotion_hint,
                     source_type, translation_source, confidence, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    dialogue.id,
                    dialogue.episode_id,
                    dialogue.start,
                    dialogue.end,
                    dialogue.source_text,
                    dialogue.normalized_text,
                    dialogue.translated_text,
                    dialogue.source_language,
                    dialogue.target_language,
                    dialogue.speaker_id,
                    dialogue.character_id,
                    dialogue.candidate_character,
                    dialogue.dialogue_type,
                    dialogue.emotion_hint,
                    dialogue.source_type,
                    dialogue.translation_source,
                    dialogue.confidence,
                    dialogue.created_at
                ))

            conn.commit()
            logger.info(f"Saved {len(dialogues)} dialogues to database")

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save dialogues: {e}")
            raise
        finally:
            conn.close()

    def _generate_manifest(self) -> Dict[str, Any]:
        """生成清单"""
        # 保存对话到 JSONL
        jsonl_path = self.dialogue_dir / "normalized" / "dialogues.jsonl"
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)

        with open(jsonl_path, 'w', encoding='utf-8') as f:
            for dialogue in self.dialogues:
                f.write(json.dumps(dialogue.to_dict(), ensure_ascii=False) + '\n')

        # 生成清单
        subtitle_sources = []
        if self.english_subtitle:
            subtitle_sources.append(self.english_subtitle.to_dict())
        if self.chinese_subtitle:
            subtitle_sources.append(self.chinese_subtitle.to_dict())

        manifest = self.manifest_builder.build(
            subtitle_sources=subtitle_sources,
            dialogues=[d.to_dict() for d in self.dialogues],
            translation_mode=self.config.translation_mode.value,
            steps=self.steps
        )

        # 保存清单
        manifest_path = self.dialogue_dir / "dialogue_manifest.json"
        self.manifest_builder.save(manifest, manifest_path)

        return manifest

    def _update_project_status(self, status: str) -> None:
        """更新项目状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE projects
                SET status = ?, updated_at = ?
                WHERE id = ?
            """, (status, datetime.utcnow().isoformat(), self.project_id))

            conn.commit()
            logger.info(f"Updated project status to {status}")

        except Exception as e:
            logger.error(f"Failed to update project status: {e}")
            raise
        finally:
            conn.close()
