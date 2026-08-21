# Ticket 006: M04 人物数据库核心实现

##状态: done

## 优先级: 高

## 模块: M04 - Character Database

## 描述

实现 M04 人物数据库的核心功能，包括说话人聚类、人物识别和信息关联。

## 任务清单

- [ ] 创建 `src/filmdub/workers/character_db/` 目录结构
- [ ] 创建 `src/filmdub/workers/character_db/config.py` - 配置
- [ ] 创建 `src/filmdub/workers/character_db/clustering.py` - 说话人聚类
  - [ ] SpeakerClustering 类
  - [ ] cluster_speakers() - 聚类方法
  - [ ] _adjust_parameters() - 参数调整
  - [ ] _merge_small_clusters() - 合并小聚类
  - [ ] evaluate_clustering() - 评估聚类质量
- [ ] 创建 `src/filmdub/workers/character_db/linker.py` - 人物链接
  - [ ] CharacterLinker 类
  - [ ] link_speakers_to_characters() - 链接说话人到人物
  - [ ] _find_existing_character() - 查找现有人物
  - [ ] _create_character_from_cluster() - 创建人物
  - [ ] _match_tmdb_character() - 匹配 TMDB 人物
  - [ ] _infer_gender() - 推断性别
  - [ ] _infer_age_range() - 推断年龄段
  - [ ] _infer_role_type() - 推断角色类型
- [ ] 创建 `src/filmdub/workers/character_db/models.py` - 数据模型
  - [ ] Character 数据类
  - [ ] Relationship 数据类
  - [ ] SpeakerEmbedding 数据类
- [ ] 创建 `src/filmdub/workers/character_db/main.py` - Worker 入口
- [ ] 集成 scikit-learn DBSCAN
- [ ] 实现与 Layer 0 的通信
- [ ] 编写单元测试
- [ ] 编写聚类算法测试

## 依赖

- Ticket 001: 数据库模型
- Ticket 002: Artifact Registry

## 输出

- M04 核心实现
- 说话人聚类算法
- 人物链接器
- 测试文件

## 验收标准

1. 说话人聚类正确工作
2. 人物链接准确
3. 可以保存到数据库
4. 测试通过

## 参考 ADR

- ADR 0010: M04 人物数据库构建模块设计
- specs/m04-character-database.md
