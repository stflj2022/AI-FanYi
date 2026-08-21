# ADR 0010: M04 人物数据库构建模块设计

## 状态

设计中

## 上下文

M04 人物数据库是整个平台最重要的长期资产之一。它负责建立、维护、管理整部电视剧的人物知识库，确保跨集、跨季音色一致性和人物身份稳定。

## 核心职责

1. **人物识别**: 从视频/音频中识别出不同人物
2. **人物聚类**: 将说话人聚合成人物角色
3. **信息关联**: 关联 TMDB/IMDb 人物信息
4. **关系构建**: 建立人物关系网络
5. **数据库维护**: 跨集数据复用和更新
6. **人工确认**: 提供人工确认和修正接口

## 输入/输出

### 输入

```python
@dataclass
class M04Input:
    """M04 输入数据结构"""
    project_id: uuid.UUID

    # 来自 M03 的对白时间轴
    dialogue_timeline: DialogueTimeline

    # 来自 M05 的说话人信息
    speaker_embeddings: List[SpeakerEmbedding]

    # 项目元数据（来自 M01）
    project_metadata: ProjectMetadata

    # TMDB 人物信息（可选）
    tmdb_characters: List[TmdbCharacter] = None

    # 现有的人物数据库（如果是续集）
    existing_characters: List[Character] = None

@dataclass
class SpeakerEmbedding:
    """说话人嵌入向量"""
    speaker_id: str           # 临时说话人 ID
    embedding: List[float]    # 嵌入向量
    segments: List[DialogueSegment]  # 该说话人的对白片段
    audio_features: AudioFeatures

@dataclass
class AudioFeatures:
    """音频特征"""
    pitch_mean: float
    pitch_std: float
    energy_mean: float
    energy_std: float
    duration_mean: float
    duration_std: float
    speaking_rate: float

@dataclass
class TmdbCharacter:
    """TMDB 人物信息"""
    id: int
    name: str
    character_name: str
    order: int
    profile_path: str
    gender: Optional[int]  # 1=female, 2=male
    known_for_department: str
```

### 输出

```python
@dataclass
class M04Output:
    """M04 输出数据结构"""
    # 人物数据库
    characters: List[Character]

    # 说话人到人物的映射
    speaker_mapping: Dict[str, uuid.UUID]  # speaker_id -> character_id

    # 人物关系图
    relationship_graph: RelationshipGraph

    # 统计信息
    statistics: CharacterStatistics

@dataclass
class Character:
    """人物信息"""
    id: uuid.UUID
    project_id: uuid.UUID

    # 基本信息
    name: str
    name_en: str
    name_original: Optional[str] = None
    aliases: List[str] = None

    # 人口统计学特征
    gender: Optional[Gender] = None
    age_range: Optional[AgeRange] = None
    role_type: Optional[RoleType] = None

    # 演员信息
    actor_id: Optional[int] = None
    actor_name: Optional[str] = None
    actor_profile_path: Optional[str] = None

    # 描述信息
    description: Optional[str] = None
    personality: Optional[str] = None
    speech_pattern: Optional[str] = None
    background_story: Optional[str] = None

    # 首次出现
    first_appearance: Optional[EpisodeRef] = None

    # 关系
    relationships: List[Relationship] = None

    # 音色档案
    voice_profile_id: Optional[uuid.UUID] = None

    # 元数据
    confidence: float = 0.0        # 识别置信度
    is_confirmed: bool = False     # 是否已人工确认
    is_active: bool = True         # 是否活跃

    # 时间戳
    created_at: datetime = None
    updated_at: datetime = None

@dataclass
class Relationship:
    """人物关系"""
    target_character_id: uuid.UUID
    relationship_type: RelationshipType
    description: Optional[str] = None
    confidence: float = 1.0

class RelationshipType(Enum):
    """关系类型"""
    FAMILY = "family"              # 家庭关系
    ROMANTIC = "romantic"         # 恋爱关系
    FRIEND = "friend"             # 朋友
    COLLEAGUE = "colleague"       # 同事
    ENEMY = "enemy"               # 敌人
    MENTOR = "mentor"             # 导师
    STUDENT = "student"           # 学生
    BOSS = "boss"                 # 上下级
    PARTNER = "partner"           # 合作伙伴
    OTHER = "other"               # 其他

class Gender(Enum):
    """性别"""
    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"
    UNKNOWN = "unknown"

class AgeRange(Enum):
    """年龄段"""
    CHILD = "child"               # 0-12
    TEEN = "teen"                 # 13-19
    YOUNG_ADULT = "young_adult"   # 20-35
    ADULT = "adult"               # 36-55
    SENIOR = "senior"             # 55+
    UNKNOWN = "unknown"

class RoleType(Enum):
    """角色类型"""
    MAIN = "main"                 # 主要角色
    SUPPORTING = "supporting"    # 配角
    MINOR = "minor"               # 次要角色
    CAMEO = "cameo"               # 客串
    BACKGROUND = "background"     # 背景/群演
    UNKNOWN = "unknown"

@dataclass
class RelationshipGraph:
    """人物关系图"""
    nodes: List[Character]
    edges: List[Tuple[uuid.UUID, uuid.UUID, RelationshipType]]

@dataclass
class CharacterStatistics:
    """人物数据库统计"""
    total_characters: int
    main_characters: int
    supporting_characters: int
    confirmed_characters: int
    auto_generated_characters: int
    average_confidence: float
```

## 模块架构

```
┌──────────────────────────────────────────────────────────────┐
│                         M04                                  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────┐      ┌────────────────┐                 │
│  │  说话人聚类     │──────│  人物识别      │                 │
│  │  (聚类算法)     │      │  (实体链接)     │                 │
│  └────────────────┘      └────────────────┘                 │
│         │                         │                            │
│         └──────────┬──────────────┘                            │
│                    ▼                                         │
│         ┌────────────────────────┐                            │
│         │      信息关联            │                            │
│         │   (TMDB/IMDb/知识图谱)   │                            │
│         └────────────────────────┘                            │
│                    │                                         │
│                    ▼                                         │
│         ┌────────────────────────┐                            │
│         │      关系构建            │                            │
│         │   (关系抽取/图谱构建)     │                            │
│         └────────────────────────┘                            │
│                    │                                         │
│                    ▼                                         │
│         ┌────────────────────────┐                            │
│         │      数据库更新           │                            │
│         │   (跨集复用/增量更新)     │                            │
│         └────────────────────────┘                            │
│                    │                                         │
│                    ▼                                         │
│         ┌────────────────────────┐                            │
│         │      人工确认            │                            │
│         │   (置信度/冲突解决)       │                            │
│         └────────────────────────┘                            │
└──────────────────────────────────────────────────────────────┘
```

## 核心算法

### 1. 说话人聚类

```python
from sklearn.cluster import DBSCAN
from sklearn.metrics import silhouette_score
import numpy as np

class SpeakerClustering:
    """说话人聚类"""

    def __init__(self, min_samples: int = 2, eps: float = 0.5):
        self.min_samples = min_samples
        self.eps = eps

    def cluster_speakers(
        self,
        embeddings: List[SpeakerEmbedding],
        expected_count: Optional[int] = None
    ) -> Dict[str, int]:
        """对说话人进行聚类

        Args:
            embeddings: 说话人嵌入列表
            expected_count: 期望的人物数量（可选，用于参数调整）

        Returns:
            说话人 ID 到聚类 ID 的映射
        """
        # 提取嵌入向量
        embedding_matrix = np.array([emb.embedding for emb in embeddings])

        # 如果有预期数量，调整参数
        if expected_count:
            self._adjust_parameters(expected_count, len(embeddings))

        # 使用 DBSCAN 聚类
        clustering = DBSCAN(
            eps=self.eps,
            min_samples=self.min_samples,
            metric='cosine'
        )

        labels = clustering.fit_predict(embedding_matrix)

        # 建立映射
        speaker_to_cluster = {
            embeddings[i].speaker_id: int(labels[i])
            for i in range(len(embeddings))
            if labels[i] >= 0  # 忽略噪声点
        }

        # 合并小聚类（可能是误检）
        speaker_to_cluster = self._merge_small_clusters(
            speaker_to_cluster, labels
        )

        return speaker_to_cluster

    def _adjust_parameters(self, expected_count: int, total_speakers: int):
        """根据预期数量调整参数"""
        # 简化的参数调整逻辑
        ratio = total_speakers / expected_count

        if ratio > 2:
            # 说话人太多，增大 eps 进行合并
            self.eps = min(self.eps * 1.2, 1.0)
        elif ratio < 0.5:
            # 说话人太少，减小 eps 进行分离
            self.eps = max(self.eps * 0.8, 0.1)

    def _merge_small_clusters(
        self,
        speaker_to_cluster: Dict[str, int],
        labels: np.ndarray
    ) -> Dict[str, int]:
        """合并小聚类"""
        from collections import Counter

        # 统计每个聚类的大小
        cluster_sizes = Counter(labels)
        cluster_sizes.pop(-1, None)  # 移除噪声点

        # 找到小聚类（<3个说话人）
        small_clusters = [
            cluster_id for cluster_id, size in cluster_sizes.items()
            if size < 3
        ]

        # 如果有小聚类，合并到最近的聚类
        if small_clusters and len(cluster_sizes) > 1:
            # 简化处理：合并到最大的聚类
            largest_cluster = max(cluster_sizes, key=cluster_sizes.get)

            for small_cluster in small_clusters:
                for speaker_id, cluster_id in speaker_to_cluster.items():
                    if cluster_id == small_cluster:
                        speaker_to_cluster[speaker_id] = largest_cluster

        return speaker_to_cluster

    def evaluate_clustering(
        self,
        embeddings: List[SpeakerEmbedding],
        labels: List[int]
    ) -> float:
        """评估聚类质量"""
        if len(set(labels)) < 2:
            return 0.0

        embedding_matrix = np.array([emb.embedding for emb in embeddings])
        valid_indices = [i for i, label in enumerate(labels) if label >= 0]

        if len(valid_indices) < 2:
            return 0.0

        valid_embeddings = embedding_matrix[valid_indices]
        valid_labels = [labels[i] for i in valid_indices]

        return silhouette_score(valid_embeddings, valid_labels)
```

### 2. 人物识别与链接

```python
class CharacterLinker:
    """人物链接器"""

    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold

    def link_speakers_to_characters(
        self,
        speaker_clusters: Dict[str, int],
        tmdb_characters: List[TmdbCharacter],
        existing_characters: List[Character] = None
    ) -> List[Character]:
        """将说话人聚类链接到人物"""
        characters = []

        # 如果有现有人物，优先匹配
        if existing_characters:
            characters.extend(existing_characters)

        # 为每个新聚类创建人物
        unique_clusters = set(speaker_clusters.values())

        for cluster_id in unique_clusters:
            # 检查是否已存在于现有人物中
            existing = self._find_existing_character(
                cluster_id, characters
            )

            if existing:
                continue

            # 创建新人物
            character = self._create_character_from_cluster(
                cluster_id,
                speaker_clusters,
                tmdb_characters
            )

            if character:
                characters.append(character)

        return characters

    def _find_existing_character(
        self,
        cluster_id: int,
        characters: List[Character]
    ) -> Optional[Character]:
        """查找现有人物"""
        # 简化处理：检查是否有未匹配的人物
        for char in characters:
            if not char.voice_profile_id and char.is_active:
                return char
        return None

    def _create_character_from_cluster(
        self,
        cluster_id: int,
        speaker_clusters: Dict[str, int],
        tmdb_characters: List[TmdbCharacter]
    ) -> Optional[Character]:
        """从聚类创建人物"""
        # 获取该聚类的所有说话人
        cluster_speakers = [
            speaker_id for speaker_id, cid in speaker_clusters.items()
            if cid == cluster_id
        ]

        if not cluster_speakers:
            return None

        # 尝试匹配 TMDB 人物
        tmdb_char = self._match_tmdb_character(
            cluster_speakers, tmdb_characters
        )

        # 推断人口统计学特征
        gender = self._infer_gender(cluster_speakers)
        age_range = self._infer_age_range(cluster_speakers)
        role_type = self._infer_role_type(cluster_speakers)

        return Character(
            id=uuid.uuid4(),
            project_id=None,  # 将在调用时设置
            name=tmdb_char.name if tmdb_char else f"Character_{cluster_id}",
            name_en=tmdb_char.character_name if tmdb_char else f"Character_{cluster_id}",
            gender=gender,
            age_range=age_range,
            role_type=role_type,
            actor_id=tmdb_char.id if tmdb_char else None,
            actor_name=tmdb_char.name if tmdb_char else None,
            confidence=self._calculate_confidence(cluster_speakers, tmdb_char),
            is_confirmed=False,
            is_active=True
        )

    def _match_tmdb_character(
        self,
        cluster_speakers: List[str],
        tmdb_characters: List[TmdbCharacter]
    ) -> Optional[TmdbCharacter]:
        """匹配 TMDB 人物"""
        if not tmdb_characters:
            return None

        # 简化处理：按顺序分配
        # 实际应该使用更复杂的匹配算法
        available_chars = [
            char for char in tmdb_characters
            if not char.assigned  # 假设有标记
        ]

        if available_chars:
            return available_chars[0]

        return None

    def _infer_gender(self, cluster_speakers: List[str]) -> Gender:
        """推断性别"""
        # 根据音频特征推断
        # 这里简化处理，返回未知
        return Gender.UNKNOWN

    def _infer_age_range(self, cluster_speakers: List[str]) -> AgeRange:
        """推断年龄段"""
        # 根据音频特征推断
        # 这里简化处理，返回未知
        return AgeRange.UNKNOWN

    def _infer_role_type(self, cluster_speakers: List[str]) -> RoleType:
        """推断角色类型"""
        # 根据对白数量推断
        dialogue_count = sum(
            len(seg.segments) for seg in cluster_speakers
        )

        if dialogue_count > 100:
            return RoleType.MAIN
        elif dialogue_count > 20:
            return RoleType.SUPPORTING
        elif dialogue_count > 5:
            return RoleType.MINOR
        else:
            return RoleType.BACKGROUND

    def _calculate_confidence(
        self,
        cluster_speakers: List[str],
        tmdb_char: Optional[TmdbCharacter]
    ) -> float:
        """计算置信度"""
        base_confidence = 0.5

        # 如果有 TMDB 匹配，提高置信度
        if tmdb_char:
            base_confidence += 0.2

        # 如果聚类质量高，提高置信度
        if len(cluster_speakers) >= 3:
            base_confidence += 0.1

        return min(base_confidence, 1.0)
```

### 3. 关系构建

```python
class RelationshipBuilder:
    """关系构建器"""

    def __init__(self):
        self.llm_client = None  # 用于关系抽取的 LLM

    async def build_relationships(
        self,
        characters: List[Character],
        dialogue_timeline: DialogueTimeline
    ) -> RelationshipGraph:
        """构建人物关系图"""
        edges = []

        # 从对白中抽取关系
        for char1 in characters:
            for char2 in characters:
                if char1.id == char2.id:
                    continue

                # 检查两个角色是否有交互
                interactions = self._find_interactions(
                    char1, char2, dialogue_timeline
                )

                if interactions:
                    # 推断关系类型
                    relationship = await self._infer_relationship(
                        char1, char2, interactions
                    )

                    if relationship:
                        edges.append((char1.id, char2.id, relationship))

                        # 添加到人物的关系列表
                        if char1.relationships is None:
                            char1.relationships = []
                        char1.relationships.append(relationship)

        return RelationshipGraph(
            nodes=characters,
            edges=edges
        )

    def _find_interactions(
        self,
        char1: Character,
        char2: Character,
        dialogue_timeline: DialogueTimeline
    ) -> List[DialogueSegment]:
        """查找两个角色的交互"""
        interactions = []

        for segment in dialogue_timeline.segments:
            if segment.speaker == char1.name_en and \
               self._mentions_character(segment, char2):
                interactions.append(segment)

        return interactions

    def _mentions_character(
        self,
        segment: DialogueSegment,
        character: Character
    ) -> bool:
        """检查对白是否提到某个角色"""
        # 简化处理：检查是否包含角色名
        mentions = [character.name, character.name_en]
        if character.aliases:
            mentions.extend(character.aliases)

        text_lower = segment.text.lower()
        return any(
            mention.lower() in text_lower
            for mention in mentions
        )

    async def _infer_relationship(
        self,
        char1: Character,
        char2: Character,
        interactions: List[DialogueSegment]
    ) -> Optional[Relationship]:
        """使用 LLM 推断关系"""
        # 构建提示
        prompt = self._build_relationship_prompt(
            char1, char2, interactions
        )

        # 调用 LLM
        # 这里简化处理
        return Relationship(
            target_character_id=char2.id,
            relationship_type=RelationshipType.OTHER,
            description="Inferred from dialogue",
            confidence=0.6
        )

    def _build_relationship_prompt(
        self,
        char1: Character,
        char2: Character,
        interactions: List[DialogueSegment]
    ) -> str:
        """构建 LLM 提示"""
        dialogue_snippets = [
            f"{seg.speaker}: {seg.text}"
            for seg in interactions[:5]  # 限制上下文
        ]

        return f"""
根据以下对白，推断 {char1.name_en} 和 {char2.name_en} 之间的关系：

对白:
{chr(10).join(dialogue_snippets)}

返回 JSON 格式：
{{
    "relationship_type": "friend|family|romantic|enemy|colleague|other",
    "confidence": 0.0-1.0,
    "description": "简短描述"
}}
"""
```

### 4. 跨集数据复用

```python
class CrossEpisodeManager:
    """跨集数据管理器"""

    def __init__(self, db):
        self.db = db

    async def get_existing_characters(
        self,
        project_id: uuid.UUID,
        season: Optional[int] = None
    ) -> List[Character]:
        """获取现有人物"""
        query = "SELECT * FROM characters WHERE project_id = $1"
        params = [project_id]

        if season is not None:
            query += " AND season = $2"
            params.append(season)

        rows = await self.db.fetch(query, *params)
        return [self._row_to_character(row) for row in rows]

    async def update_character(
        self,
        character: Character
    ) -> None:
        """更新人物信息"""
        await self.db.execute(
            """
            UPDATE characters
            SET name = $1, name_en = $2, aliases = $3,
                gender = $4, age_range = $5, role_type = $6,
                description = $7, personality = $8,
                confidence = $9, is_confirmed = $10,
                updated_at = NOW()
            WHERE id = $11
            """,
            character.name, character.name_en, character.aliases,
            character.gender.value if character.gender else None,
            character.age_range.value if character.age_range else None,
            character.role_type.value if character.role_type else None,
            character.description, character.personality,
            character.confidence, character.is_confirmed,
            character.id
        )

    async def merge_characters(
        self,
        source_id: uuid.UUID,
        target_id: uuid.UUID
    ) -> None:
        """合并两个角色"""
        await self.db.execute(
            """
            UPDATE dialogues
            SET character_id = $1
            WHERE character_id = $2
            """,
            target_id, source_id
        )

        await self.db.execute(
            """
            UPDATE characters
            SET is_active = false
            WHERE id = $1
            """,
            source_id
        )
```

## 人工确认接口

```python
class HumanConfirmationAPI:
    """人工确认 API"""

    async def get_pending_confirmations(
        self,
        project_id: uuid.UUID,
        confidence_threshold: float = 0.7
    ) -> List[Character]:
        """获取需要确认的人物"""
        return await self.db.fetch(
            """
            SELECT * FROM characters
            WHERE project_id = $1
            AND confidence < $2
            AND is_confirmed = false
            ORDER BY confidence DESC
            """,
            project_id, confidence_threshold
        )

    async def confirm_character(
        self,
        character_id: uuid.UUID,
        confirmed_data: Dict[str, Any]
    ) -> None:
        """确认人物信息"""
        await self.db.execute(
            """
            UPDATE characters
            SET is_confirmed = true,
                name = COALESCE($2, name),
                name_en = COALESCE($3, name_en),
                gender = COALESCE($4, gender),
                age_range = COALESCE($5, age_range),
                role_type = COALESCE($6, role_type),
                updated_at = NOW()
            WHERE id = $1
            """,
            character_id,
            confirmed_data.get('name'),
            confirmed_data.get('name_en'),
            confirmed_data.get('gender'),
            confirmed_data.get('age_range'),
            confirmed_data.get('role_type')
        )

    async def reject_character(
        self,
        character_id: uuid.UUID,
        reason: str
    ) -> None:
        """拒绝人物识别结果"""
        await self.db.execute(
            """
            UPDATE characters
            SET is_active = false,
                confidence = 0,
                updated_at = NOW()
            WHERE id = $1
            """,
            character_id
        )

    async def add_character(
        self,
        project_id: uuid.UUID,
        character_data: Dict[str, Any]
    ) -> uuid.UUID:
        """手动添加人物"""
        character_id = uuid.uuid4()

        await self.db.execute(
            """
            INSERT INTO characters (
                id, project_id, name, name_en,
                gender, age_range, role_type,
                is_confirmed, is_active, confidence
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, true, true, 1.0)
            """,
            character_id, project_id,
            character_data['name'],
            character_data['name_en'],
            character_data.get('gender'),
            character_data.get('age_range'),
            character_data.get('role_type')
        )

        return character_id
```

## 错误处理

### 错误代码

| 代码 | 描述 | 可重试 |
|------|------|--------|
| M004-001 | 说话人聚类失败 | 是 |
| M004-002 | 人物链接失败 | 是 |
| M004-003 | TMDB 数据获取失败 | 是 |
| M004-004 | 关系推断失败 | 是 |
| M004-005 | 数据库更新失败 | 是 |

### 降级策略

1. **聚类失败**: 使用更简单的算法或人工分配
2. **TMDB 失败**: 使用音频特征推断
3. **关系推断失败**: 建立空关系图

## 测试要点

1. 不同数量人物的聚类测试
2. 跨集人物一致性测试
3. TMDB 匹配准确性测试
4. 关系推断准确性测试
5. 边界情况处理（群演、客串）

## 后续模块依赖

M04 的输出被以下模块使用：
- **M06**: 人物信息用于说话人到人物映射
- **M07**: 人物背景用于对白智能处理
- **M08**: 人物说话特点用于韵律规划
- **M09**: Voice Profile 用于 TTS
