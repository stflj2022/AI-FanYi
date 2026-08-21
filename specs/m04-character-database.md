# M04: Character Database Construction - 人物数据库构建

## 概述

M04 是平台最重要的长期资产模块之一，负责建立、维护、管理整部电视剧的人物知识库，确保跨集、跨季音色一致性和人物身份稳定。

## 核心职责

1. **人物识别**: 从视频/音频中识别出不同人物
2. **人物聚类**: 将说话人聚合成人物角色
3. **信息关联**: 关联 TMDB/IMDb 人物信息
4. **关系构建**: 建立人物关系网络
5. **数据库维护**: 跨集数据复用和更新
6. **人工确认**: 提供人工确认和修正接口

## 输入/输出

### 输入 Artifact

- `dialogue_timeline` (来自 M03): 对白时间轴
- `speaker_embeddings` (来自 M05): 说话人嵌入向量
- `project_metadata` (来自 M01): 项目元数据
- `tmdb_characters` (可选): TMDB 人物信息
- `existing_characters` (可选): 现有人物数据库（续集）

### 输出 Artifact

- `character_database`: 人物数据库
- `speaker_mapping`: 说话人到人物的映射
- `relationship_graph`: 人物关系图
- `character_statistics`: 统计信息

## 技术栈

- **语言**: Python 3.11+
- **聚类算法**: scikit-learn (DBSCAN)
- **嵌入模型**: speechbrain / pyannote
- **外部数据**: TMDB API
- **LLM**: 本地 LLM (Qwen) 用于关系推断

## 数据结构

### Character

```python
@dataclass
class Character:
    id: uuid.UUID
    project_id: uuid.UUID

    # 基本信息
    name: str
    name_en: str
    aliases: List[str] = None

    # 人口统计学
    gender: Optional[Gender] = None
    age_range: Optional[AgeRange] = None
    role_type: Optional[RoleType] = None

    # 演员信息
    actor_id: Optional[int] = None
    actor_name: Optional[str] = None

    # 描述
    description: Optional[str] = None
    personality: Optional[str] = None
    speech_pattern: Optional[str] = None

    # 首次出现
    first_appearance: Optional[EpisodeRef] = None

    # 关系
    relationships: List[Relationship] = None

    # 音色档案
    voice_profile_id: Optional[uuid.UUID] = None

    # 元数据
    confidence: float = 0.0
    is_confirmed: bool = False
    is_active: bool = True
```

### Relationship

```python
@dataclass
class Relationship:
    target_character_id: uuid.UUID
    relationship_type: RelationshipType
    description: Optional[str] = None
    confidence: float = 1.0
```

## 核心算法

### 1. 说话人聚类

使用 DBSCAN 算法对说话人嵌入进行聚类：

```python
from sklearn.cluster import DBSCAN

class SpeakerClustering:
    def cluster_speakers(
        self,
        embeddings: List[SpeakerEmbedding],
        expected_count: Optional[int] = None
    ) -> Dict[str, int]:
        """对说话人进行聚类"""
        embedding_matrix = np.array([emb.embedding for emb in embeddings])

        clustering = DBSCAN(
            eps=self.eps,
            min_samples=self.min_samples,
            metric='cosine'
        )

        labels = clustering.fit_predict(embedding_matrix)

        return {embeddings[i].speaker_id: int(labels[i])
                for i in range(len(embeddings))
                if labels[i] >= 0}
```

### 2. 人物识别与链接

将聚类结果链接到 TMDB 人物信息：

```python
class CharacterLinker:
    def link_speakers_to_characters(
        self,
        speaker_clusters: Dict[str, int],
        tmdb_characters: List[TmdbCharacter],
        existing_characters: List[Character] = None
    ) -> List[Character]:
        """将说话人聚类链接到人物"""
        # 优先匹配现有人物
        # 然后匹配 TMDB 人物
        # 最后创建新人物
```

### 3. 关系构建

使用 LLM 从对白中推断人物关系：

```python
class RelationshipBuilder:
    async def build_relationships(
        self,
        characters: List[Character],
        dialogue_timeline: DialogueTimeline
    ) -> RelationshipGraph:
        """构建人物关系图"""
        # 查找角色间交互
        # 使用 LLM 推断关系
        # 构建关系图
```

### 4. 跨集数据复用

```python
class CrossEpisodeManager:
    async def get_existing_characters(
        self,
        project_id: uuid.UUID,
        season: Optional[int] = None
    ) -> List[Character]:
        """获取现有人物"""

    async def update_character(
        self,
        character: Character
    ) -> None:
        """更新人物信息"""

    async def merge_characters(
        self,
        source_id: uuid.UUID,
        target_id: uuid.UUID
    ) -> None:
        """合并两个角色"""
```

## 目录结构

```
src/filmdub/workers/character_db/
├── __init__.py
├── main.py                 # Worker 入口
├── config.py               # 配置
├── clustering.py           # 说话人聚类
├── linker.py               # 人物链接
├── relationships.py        # 关系构建
├── cross_episode.py        # 跨集管理
├── models.py               # 数据模型
└── tests/
    ├── test_clustering.py
    ├── test_linker.py
    └── test_relationships.py
```

## 配置示例

```python
# config.py
@dataclass
class M04Config:
    # 聚类参数
    clustering_eps: float = 0.5
    clustering_min_samples: int = 2

    # 相似度阈值
    similarity_threshold: float = 0.7

    # TMDB API
    tmdb_api_key: Optional[str] = None

    # LLM 配置
    llm_endpoint: str = "http://localhost:8000"
    llm_model: str = "qwen"

    # 置信度阈值
    auto_confirm_threshold: float = 0.9
    manual_review_threshold: float = 0.7
```

## 依赖模块

- **M02**: 获取 TMDB 人物信息
- **M03**: 获取对白时间轴
- **M05**: 获取说话人嵌入向量

## 后续模块依赖

M04 的输出被以下模块使用：
- **M06**: 人物信息用于说话人到人物映射
- **M07**: 人物背景用于对白智能处理
- **M08**: 人物说话特点用于韵律规划
- **M09**: Voice Profile 用于 TTS

## 实现优先级

### Phase 1: 核心聚类 (高优先级)
1. 说话人聚类算法
2. 基本人物创建
3. 保存到数据库

### Phase 2: 信息关联 (高优先级)
1. TMDB 人物匹配
2. 现有人物复用
3. 人口统计学推断

### Phase 3: 关系构建 (中优先级)
1. 角色交互检测
2. LLM 关系推断
3. 关系图构建

### Phase 4: 跨集管理 (中优先级)
1. 现有人物加载
2. 人物更新
3. 人物合并

### Phase 5: 人工确认 (低优先级)
1. 确认 API
2. 置信度计算
3. 冲突解决

## 测试要点

1. 不同数量人物的聚类测试
2. 跨集人物一致性测试
3. TMDB 匹配准确性测试
4. 关系推断准确性测试
5. 边界情况处理（群演、客串）

## 参考 ADR

- ADR 0010: M04 人物数据库构建模块设计
- ADR 0002: Layer 0 数据库 Schema 设计
