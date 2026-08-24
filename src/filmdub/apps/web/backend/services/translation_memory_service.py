"""翻译记忆服务"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from filmdub.core.models import TranslationMemoryEntry, GlossaryTerm


class TranslationMemoryService:
    """翻译记忆服务"""

    @staticmethod
    async def get_translation_entries(
        db: AsyncSession,
        project_id: Optional[UUID] = None,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        character_name: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[TranslationMemoryEntry], int]:
        """获取翻译记忆条目列表"""
        query = select(TranslationMemoryEntry)

        # 筛选条件
        conditions = []
        if project_id:
            conditions.append(TranslationMemoryEntry.project_id == project_id)
        if source_lang:
            conditions.append(TranslationMemoryEntry.source_lang == source_lang)
        if target_lang:
            conditions.append(TranslationMemoryEntry.target_lang == target_lang)
        if character_name:
            conditions.append(TranslationMemoryEntry.character_name == character_name)
        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    TranslationMemoryEntry.source_text.ilike(search_pattern),
                    TranslationMemoryEntry.translated_text.ilike(search_pattern),
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        # 获取总数
        count_query = select(func.count(TranslationMemoryEntry.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        # 分页和排序
        query = query.order_by(TranslationMemoryEntry.usage_count.desc(), TranslationMemoryEntry.updated_at.desc())
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        entries = result.scalars().all()

        return entries, total

    @staticmethod
    async def get_translation_entry_by_id(db: AsyncSession, entry_id: UUID) -> Optional[TranslationMemoryEntry]:
        """根据 ID 获取翻译记忆条目"""
        result = await db.execute(
            select(TranslationMemoryEntry).where(TranslationMemoryEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_translation_entry(
        db: AsyncSession,
        project_id: Optional[UUID],
        source_text: str,
        translated_text: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None,
        character_name: Optional[str] = None,
        scene_description: Optional[str] = None,
        similarity_score: Optional[float] = None,
    ) -> TranslationMemoryEntry:
        """创建翻译记忆条目"""
        entry = TranslationMemoryEntry(
            project_id=project_id,
            source_text=source_text,
            translated_text=translated_text,
            source_lang=source_lang,
            target_lang=target_lang,
            context=context,
            character_name=character_name,
            scene_description=scene_description,
            similarity_score=similarity_score,
            usage_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry

    @staticmethod
    async def update_translation_entry(
        db: AsyncSession,
        entry_id: UUID,
        source_text: Optional[str] = None,
        translated_text: Optional[str] = None,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        context: Optional[str] = None,
        character_name: Optional[str] = None,
        scene_description: Optional[str] = None,
        similarity_score: Optional[float] = None,
    ) -> Optional[TranslationMemoryEntry]:
        """更新翻译记忆条目"""
        entry = await TranslationMemoryService.get_translation_entry_by_id(db, entry_id)
        if not entry:
            return None

        if source_text is not None:
            entry.source_text = source_text
        if translated_text is not None:
            entry.translated_text = translated_text
        if source_lang is not None:
            entry.source_lang = source_lang
        if target_lang is not None:
            entry.target_lang = target_lang
        if context is not None:
            entry.context = context
        if character_name is not None:
            entry.character_name = character_name
        if scene_description is not None:
            entry.scene_description = scene_description
        if similarity_score is not None:
            entry.similarity_score = similarity_score

        entry.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(entry)
        return entry

    @staticmethod
    async def delete_translation_entry(db: AsyncSession, entry_id: UUID) -> bool:
        """删除翻译记忆条目"""
        entry = await TranslationMemoryService.get_translation_entry_by_id(db, entry_id)
        if not entry:
            return False

        await db.delete(entry)
        await db.commit()
        return True

    @staticmethod
    async def increment_usage_count(db: AsyncSession, entry_id: UUID) -> Optional[TranslationMemoryEntry]:
        """增加使用计数"""
        entry = await TranslationMemoryService.get_translation_entry_by_id(db, entry_id)
        if not entry:
            return None

        entry.usage_count += 1
        entry.last_used = datetime.utcnow()
        entry.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(entry)
        return entry

    @staticmethod
    async def get_glossary_terms(
        db: AsyncSession,
        project_id: Optional[UUID] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[GlossaryTerm], int]:
        """获取术语列表"""
        query = select(GlossaryTerm)

        # 筛选条件
        conditions = []
        if project_id:
            conditions.append(GlossaryTerm.project_id == project_id)
        if category:
            conditions.append(GlossaryTerm.category == category)
        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    GlossaryTerm.source_term.ilike(search_pattern),
                    GlossaryTerm.target_term.ilike(search_pattern),
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        # 获取总数
        count_query = select(func.count(GlossaryTerm.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        # 分页和排序
        query = query.order_by(GlossaryTerm.usage_count.desc(), GlossaryTerm.source_term)
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        terms = result.scalars().all()

        return terms, total

    @staticmethod
    async def get_glossary_term_by_id(db: AsyncSession, term_id: UUID) -> Optional[GlossaryTerm]:
        """根据 ID 获取术语"""
        result = await db.execute(
            select(GlossaryTerm).where(GlossaryTerm.id == term_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_glossary_term(
        db: AsyncSession,
        project_id: Optional[UUID],
        source_term: str,
        target_term: str,
        category: Optional[str] = None,
        notes: Optional[str] = None,
        examples: Optional[List[str]] = None,
    ) -> GlossaryTerm:
        """创建术语"""
        term = GlossaryTerm(
            project_id=project_id,
            source_term=source_term,
            target_term=target_term,
            category=category,
            notes=notes,
            examples=examples or [],
            usage_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(term)
        await db.commit()
        await db.refresh(term)
        return term

    @staticmethod
    async def update_glossary_term(
        db: AsyncSession,
        term_id: UUID,
        source_term: Optional[str] = None,
        target_term: Optional[str] = None,
        category: Optional[str] = None,
        notes: Optional[str] = None,
        examples: Optional[List[str]] = None,
    ) -> Optional[GlossaryTerm]:
        """更新术语"""
        term = await TranslationMemoryService.get_glossary_term_by_id(db, term_id)
        if not term:
            return None

        if source_term is not None:
            term.source_term = source_term
        if target_term is not None:
            term.target_term = target_term
        if category is not None:
            term.category = category
        if notes is not None:
            term.notes = notes
        if examples is not None:
            term.examples = examples

        term.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(term)
        return term

    @staticmethod
    async def delete_glossary_term(db: AsyncSession, term_id: UUID) -> bool:
        """删除术语"""
        term = await TranslationMemoryService.get_glossary_term_by_id(db, term_id)
        if not term:
            return False

        await db.delete(term)
        await db.commit()
        return True

    @staticmethod
    async def increment_term_usage_count(db: AsyncSession, term_id: UUID) -> Optional[GlossaryTerm]:
        """增加术语使用计数"""
        term = await TranslationMemoryService.get_glossary_term_by_id(db, term_id)
        if not term:
            return None

        term.usage_count += 1
        term.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(term)
        return term

    @staticmethod
    async def get_statistics(
        db: AsyncSession,
        project_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """获取翻译统计"""
        # 统计翻译条目总数
        tm_count_query = select(func.count(TranslationMemoryEntry.id))
        if project_id:
            tm_count_query = tm_count_query.where(TranslationMemoryEntry.project_id == project_id)
        tm_count_result = await db.execute(tm_count_query)
        total_entries = tm_count_result.scalar() or 0

        # 统计术语总数
        glossary_count_query = select(func.count(GlossaryTerm.id))
        if project_id:
            glossary_count_query = glossary_count_query.where(GlossaryTerm.project_id == project_id)
        glossary_count_result = await db.execute(glossary_count_query)
        total_glossary_terms = glossary_count_result.scalar() or 0

        # 统计语言对
        lang_pair_query = select(
            TranslationMemoryEntry.source_lang,
            TranslationMemoryEntry.target_lang,
            func.count(TranslationMemoryEntry.id).label('count')
        )
        if project_id:
            lang_pair_query = lang_pair_query.where(TranslationMemoryEntry.project_id == project_id)
        lang_pair_query = lang_pair_query.group_by(
            TranslationMemoryEntry.source_lang,
            TranslationMemoryEntry.target_lang
        )
        lang_pair_result = await db.execute(lang_pair_query)
        language_pairs = [
            {"pair": f"{row.source_lang}->{row.target_lang}", "count": row.count}
            for row in lang_pair_result
        ]

        # 最常用的翻译（前10）
        most_used_query = select(TranslationMemoryEntry)
        if project_id:
            most_used_query = most_used_query.where(TranslationMemoryEntry.project_id == project_id)
        most_used_query = most_used_query.order_by(TranslationMemoryEntry.usage_count.desc()).limit(10)
        most_used_result = await db.execute(most_used_query)
        most_used_translations = [
            {
                "id": str(entry.id),
                "source": entry.source_text[:50] + "..." if len(entry.source_text) > 50 else entry.source_text,
                "target": entry.translated_text[:50] + "..." if len(entry.translated_text) > 50 else entry.translated_text,
                "usage_count": entry.usage_count,
            }
            for entry in most_used_result.scalars().all()
        ]

        # 最常用的术语（前10）
        most_used_terms_query = select(GlossaryTerm)
        if project_id:
            most_used_terms_query = most_used_terms_query.where(GlossaryTerm.project_id == project_id)
        most_used_terms_query = most_used_terms_query.order_by(GlossaryTerm.usage_count.desc()).limit(10)
        most_used_terms_result = await db.execute(most_used_terms_query)
        most_used_terms = [
            {
                "id": str(term.id),
                "source": term.source_term,
                "target": term.target_term,
                "usage_count": term.usage_count,
            }
            for term in most_used_terms_result.scalars().all()
        ]

        return {
            "total_entries": total_entries,
            "total_glossary_terms": total_glossary_terms,
            "language_pairs": language_pairs,
            "most_used_translations": most_used_translations,
            "most_used_terms": most_used_terms,
        }
