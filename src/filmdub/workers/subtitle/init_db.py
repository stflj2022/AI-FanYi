"""
Module 03 数据库初始化
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# SQL 语句
CREATE_SUBTITLE_SOURCES_TABLE = """
CREATE TABLE IF NOT EXISTS subtitle_sources (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    media_id TEXT NOT NULL,
    language TEXT NOT NULL,
    source_type TEXT NOT NULL,
    path TEXT,
    stream_index INTEGER,
    format TEXT NOT NULL DEFAULT 'srt',
    duration REAL,
    confidence REAL DEFAULT 1.0,
    quality_score REAL,
    metadata TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (media_id) REFERENCES media_assets(id)
);
"""

CREATE_DIALOGUES_TABLE = """
CREATE TABLE IF NOT EXISTS dialogues (
    id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL,
    start REAL NOT NULL,
    end REAL NOT NULL,
    source_text TEXT NOT NULL,
    normalized_text TEXT,
    translated_text TEXT,
    source_language TEXT NOT NULL DEFAULT 'en',
    target_language TEXT NOT NULL DEFAULT 'zh-CN',
    speaker_id TEXT,
    character_id TEXT,
    candidate_character TEXT,
    dialogue_type TEXT NOT NULL DEFAULT 'dialogue',
    emotion_hint TEXT,
    source_type TEXT NOT NULL DEFAULT 'subtitle',
    translation_source TEXT,
    confidence REAL DEFAULT 1.0,
    metadata TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (episode_id) REFERENCES episodes(id),
    FOREIGN KEY (speaker_id) REFERENCES speakers(id),
    FOREIGN KEY (character_id) REFERENCES characters(id)
);
"""

CREATE_TRANSLATION_MEMORY_TABLE = """
CREATE TABLE IF NOT EXISTS translation_memory (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    character_id TEXT,
    source_text TEXT NOT NULL,
    translated_text TEXT NOT NULL,
    scene_context TEXT,
    confidence REAL DEFAULT 1.0,
    usage_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    last_used TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (character_id) REFERENCES characters(id)
);
"""

CREATE_SUBTITLE_EVIDENCE_TABLE = """
CREATE TABLE IF NOT EXISTS subtitle_evidence (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    data TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
"""

# 索引
CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_subtitle_sources_project ON subtitle_sources(project_id);",
    "CREATE INDEX IF NOT EXISTS idx_subtitle_sources_media ON subtitle_sources(media_id);",
    "CREATE INDEX IF NOT EXISTS idx_subtitle_sources_language ON subtitle_sources(language);",
    "CREATE INDEX IF NOT EXISTS idx_dialogues_episode ON dialogues(episode_id);",
    "CREATE INDEX IF NOT EXISTS idx_dialogues_character ON dialogues(character_id);",
    "CREATE INDEX IF NOT EXISTS idx_dialogues_speaker ON dialogues(speaker_id);",
    "CREATE INDEX IF NOT EXISTS idx_dialogues_time ON dialogues(start, end);",
    "CREATE INDEX IF NOT EXISTS idx_translation_memory_project ON translation_memory(project_id);",
    "CREATE INDEX IF NOT EXISTS idx_translation_memory_character ON translation_memory(character_id);",
    "CREATE INDEX IF NOT EXISTS idx_translation_memory_source ON translation_memory(source_text);",
    "CREATE INDEX IF NOT EXISTS idx_subtitle_evidence_project ON subtitle_evidence(project_id);",
    "CREATE INDEX IF NOT EXISTS idx_subtitle_evidence_type ON subtitle_evidence(evidence_type);",
]


def init_subtitle_db(db_path: str) -> bool:
    """
    初始化 Module 03 数据库表

    Args:
        db_path: 数据库文件路径

    Returns:
        是否成功
    """
    try:
        # 确保目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 创建表
        tables = [
            CREATE_SUBTITLE_SOURCES_TABLE,
            CREATE_DIALOGUES_TABLE,
            CREATE_TRANSLATION_MEMORY_TABLE,
            CREATE_SUBTITLE_EVIDENCE_TABLE,
        ]

        for table_sql in tables:
            cursor.execute(table_sql)
            logger.info(f"Created table: {table_sql.split()[5]}")

        # 创建索引
        for index_sql in CREATE_INDEXES:
            try:
                cursor.execute(index_sql)
                index_name = index_sql.split()[5]
                logger.info(f"Created index: {index_name}")
            except sqlite3.OperationalError as e:
                logger.warning(f"Index creation warning: {e}")

        conn.commit()
        conn.close()

        logger.info(f"Module 03 database initialized: {db_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize Module 03 database: {e}")
        return False


def check_subtitle_db(db_path: str) -> bool:
    """
    检查 Module 03 数据库是否已初始化

    Args:
        db_path: 数据库文件路径

    Returns:
        是否已初始化
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN (
                'subtitle_sources', 'dialogues',
                'translation_memory', 'subtitle_evidence'
            )
        """)

        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        return len(tables) == 4

    except Exception as e:
        logger.error(f"Failed to check Module 03 database: {e}")
        return False
