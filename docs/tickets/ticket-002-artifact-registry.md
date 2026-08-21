# Ticket 002: Artifact Registry 实现

##状态: done

## 优先级: 高

## 模块: Layer 0 Orchestrator

## 描述

实现 Artifact Registry，负责管理模块间数据传递，支持创建、上传、下载、版本管理和引用计数。

## 任务清单

- [ ] 创建 `src/filmdub/core/storage.py` - 存储抽象层
  - [ ] ArtifactStorage 接口定义
  - [ ] MinioStorage 实现
  - [ ] LocalStorage 实现（可选）
- [ ] 创建 `src/filmdub/orchestrator/artifact_registry.py` - Artifact Registry
  - [ ] ArtifactMetadata 数据类
  - [ ] ArtifactRef 数据类
  - [ ] create() - 创建 Artifact
  - [ ] upload() - 上传数据
  - [ ] download() - 下载数据
  - [ ] get() - 获取 Artifact 信息
  - [ ] increment_ref() - 增加引用计数
  - [ ] decrement_ref() - 减少引用计数
  - [ ] list_by_project() - 列出项目的 Artifacts
  - [ ] delete() - 删除 Artifact
- [ ] 集成 MinIO 客户端
- [ ] 实现校验和计算 (SHA256)
- [ ] 实现缓存层 (Redis)
- [ ] 编写单元测试
- [ ] 编写集成测试（使用真实 MinIO）

## 依赖

- Ticket 001: 数据库模型

## 输出

- 完整的 Artifact Registry 实现
- 存储后端实现
- 测试文件

## 验收标准

1. 可以成功创建和上传 Artifact
2. 可以下载并验证数据完整性
3. 版本管理正确工作
4. 引用计数机制正确
5. 单元测试和集成测试通过

## 参考 ADR

- ADR 0003: Artifact Registry 接口设计
- ADR 0001: 基于 Artifact 的模块架构
