# 自动编排器实战示例

## 场景：开发 M04 Audio Analysis 模块

### 步骤 1：启动自动编排器

```bash
# 终端 1：启动监控
cd AI-FanYi
make auto-start
```

**输出**：
```
[2026-08-21 09:00:00] ℹ️  启动自动任务编排器
[2026-08-21 09:00:00] ℹ️  检查间隔: 300秒
[2026-08-21 09:00:00] ℹ️  额度阈值: 80%
[2026-08-21 09:00:00] ℹ️  当前额度: 0.0% (0/1000000)
[2026-08-21 09:00:00] ℹ️  距重置: 17999秒
[2026-08-21 09:00:00] ℹ️  等待 300 秒后下次检查...
```

---

### 步骤 2：在另一个终端开始开发

```bash
# 终端 2：开始开发
cd AI-FanYi

# 查看快速参考
make auto-help

# 检查当前额度
make auto-check
```

**输出**：
```
✓ 检查自动任务状态...
额度: 0.0% (0/1000000)
距重置: 17999秒
```

---

### 步骤 3：完成第一个子功能后保存检查点

```bash
# 终端 2：完成 VAD 模块后保存
make auto-save \
  PHASE="m04-vad-complete" \
  MESSAGE="完成 VAD（语音活动检测）模块实现和测试" \
  NEXT="开始 Speaker Diarization" \
  CONTEXT="使用 pyannote.audio 3.1 模型，在绝命毒师 S01E01 测试中：
- 准确率: 87.3%
- 检测到: 523 个语音段
- 处理时间: 3分12秒
- GPU 使用: NVIDIA RTX 4090，VRAM 4.2GB"
```

**输出**：
```
✓ 保存自动任务...
[2026-08-21 10:30:00] ℹ️  保存检查点...
[2026-08-21 10:30:00] ✅ 检查点已保存: m04-vad-complete
[2026-08-21 10:30:00] ℹ️  恢复指令已保存到 .claude/RESUME_INSTRUCTION.txt
```

---

### 步骤 4：继续开发

```bash
# 终端 2：继续开发
# ... 实现 Speaker Diarization ...

# 完成后再保存
make auto-save \
  PHASE="m04-diarization-complete" \
  MESSAGE="完成 Speaker Diarization 模块" \
  NEXT="生成 Speaker Embeddings" \
  CONTEXT "识别到 5 个说话人：
- Speaker 0: Walter White (42.3% 说话时间)
- Speaker 1: Jesse Pinkman (28.7% 说话时间)
- Speaker 2: Skyler White (12.1% 说话时间)
- Speaker 3: Hank Schrader (10.5% 说话时间)
- Speaker 4: 其他 (6.4% 说话时间)
置信度: 0.82"
```

---

### 步骤 5：额度即将用完，自动保存

**终端 1 输出**（自动触发）：
```
[2026-08-21 14:20:00] ℹ️  当前额度: 78.0% (780000/1000000)
[2026-08-21 14:25:00] ℹ️  当前额度: 82.0% (820000/1000000)
[2026-08-21 14:25:00] ⚠️  额度超过阈值，保存进度并等待重置
[2026-08-21 14:25:00] ℹ️  估算已使用: 820000 tokens
[2026-08-21 14:25:00] ✅ 检查点已保存: quota-checkpoint
[2026-08-21 14:25:00] ℹ️  等待额度重置: 4小时35分钟
[2026-08-21 14:25:00] ℹ️  重置预计时间: 2026-08-21 19:00:00
[2026-08-21 14:25:00] ℹ️  等待中... 剩余 4小时35分钟
```

---

### 步骤 6：等待期间查看状态

```bash
# 终端 2：查看任务状态
make task-status
```

**输出**：
```
✓ 当前任务状态:

📋 进度文件:
task_id: "auto-task"
last_update: "2026-08-21T14:25:00Z"
status: "in_progress"

current_phase:
  id: "m04-embeddings-in-progress"
  status: "completed"
  message: "Speaker Embeddings 生成到 60%"
  completed_at: "2026-08-21T14:20:00Z"

next_phase:
  id: "continue"
  auto_resume: "等待额度重置后继续 Speaker Embeddings 生成"

💰 额度状态:
额度: 82.0% (820000/1000000)
距重置: 16500秒 (4小时35分钟)

📖 上下文摘要 (预览):
# 任务上下文 - 2026-08-21 14:25:00

## 当前阶段: m04-embeddings-in-progress

**状态**: Speaker Embeddings 生成到 60%，因额度用完暂停

## 下一步

继续 Speaker Embeddings 生成，当前进度：
- 已处理: 300/500 个语音段
- 嵌入维度: 256
- 模型: speechbrain/spkrec-ecapa-voxceleb
```

---

### 步骤 7：额度重置后恢复

```bash
# 终端 2：生成恢复指令
make auto-resume > .claude/RESUME.txt

# 查看恢复指令
cat .claude/RESUME.txt
```

**恢复指令内容**：
```
╔══════════════════════════════════════════════════════════════════════════════╗
║              🤖 自动任务恢复指令 🤖                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

@Claude 继续执行自动任务

═══════════════════════════════════════════════════════════════════════════════
📋 任务信息
═══════════════════════════════════════════════════════════════════════════════

task_id: auto-task
status: in_progress

current_phase:
  id: m04-embeddings-in-progress
  status: completed
  message: Speaker Embeddings 生成到 60%
  completed_at: 2026-08-21T14:20:00Z

next_phase:
  id: continue
  auto_resume: 等待额度重置后继续 Speaker Embeddings 生成

═══════════════════════════════════════════════════════════════════════════════
📖 上下文摘要
═══════════════════════════════════════════════════════════════════════════════

# 任务上下文 - 2026-08-21 14:25:00

## 当前阶段: m04-embeddings-in-progress

**状态**: Speaker Embeddings 生成到 60%，因额度用完暂停

## 下一步

继续 Speaker Embeddings 生成，当前进度：
- 已处理: 300/500 个语音段
- 嵌入维度: 256
- 模型: speechbrain/spkrec-ecapa-voxceleb

## 详细上下文

已完成功能：
1. ✅ VAD 模块（准确率 87.3%，523 个语音段）
2. ✅ Speaker Diarization（5 个说话人，置信度 0.82）
3. ⏳ Speaker Embeddings（60% 完成）

待完成功能：
1. ⏳ Speaker Embeddings（剩余 40%）
2. ⏳ 音频分析结果导出
3. ⏳ 与 Module 05 集成

═══════════════════════════════════════════════════════════════════════════════
🔧 执行指令
═══════════════════════════════════════════════════════════════════════════════

请根据上述任务信息和上下文，继续执行下一步工作。

1. 继续 Speaker Embeddings 生成（从第 301 个语音段开始）
2. 完成后导出 audio/analysis.json
3. 更新项目状态为 READY_FOR_SPEAKER_MAPPING

完成后请运行: make auto-save PHASE=m04-complete MESSAGE="完成音频分析模块" NEXT="开始 M05 说话人映射"
```

---

### 步骤 8：继续开发

```bash
# 终端 2：根据恢复指令继续
python src/filmdub/cli.py audio embeddings proj_266ef70deb92 --start 301

# 完成后保存
make auto-save \
  PHASE="m04-complete" \
  MESSAGE="完成 M04 Audio Analysis 模块" \
  NEXT="开始 M05 Speaker → Character Mapping" \
  CONTEXT="
最终结果:
- VAD: 523 个语音段，准确率 87.3%
- Diarization: 5 个说话人，置信度 0.82
- Embeddings: 500 个向量，维度 256
- 输出文件: audio/analysis.json
- 项目状态: READY_FOR_SPEAKER_MAPPING
"
```

---

## 📊 生成的检查点历史

```bash
# 查看所有检查点
ls -lh .claude/checkpoints/
```

**输出**：
```
-rw-r--r-- 1 w w 2.3K Aug 21 10:30 checkpoint_20260821_103000.json
-rw-r--r-- 1 w w 2.1K Aug 21 11:45 checkpoint_20260821_114500.json
-rw-r--r-- 1 w w 1.8K Aug 21 14:25 checkpoint_20260821_142500.json
-rw-r--r-- 1 w w 2.5K Aug 21 15:30 checkpoint_20260821_153000.json
```

---

## 🎯 完整流程总结

```
开始开发 M04
    ↓
启动自动编排器 (make auto-start)
    ↓
开发 VAD 模块
    ↓
保存检查点 (make auto-save PHASE=vad-complete ...)
    ↓
开发 Diarization 模块
    ↓
保存检查点 (make auto-save PHASE=diarization-complete ...)
    ↓
开发 Embeddings 模块
    ↓
[额度用完，自动保存]
    ↓
等待重置 (自动等待 4-5 小时)
    ↓
查看恢复指令 (make auto-resume)
    ↓
继续开发
    ↓
完成 M04 (make auto-save PHASE=m04-complete ...)
```

---

## 💡 最佳实践

### 1. 关键节点手动保存

```bash
# 完成一个完整功能后立即保存
make auto-save \
  PHASE="m04-vad" \
  MESSAGE="完成 VAD 模块" \
  NEXT="开始 Diarization" \
  CONTEXT="详细的技术指标和测试结果"
```

### 2. 保持上下文清晰

```bash
# 在 CONTEXT 中记录：
# - 已完成的功能
# - 当前进度百分比
# - 遇到的问题和解决方案
# - 技术指标（准确率、性能等）
# - 下一步的具体计划
```

### 3. 定期检查状态

```bash
# 每 1-2 小时检查一次
make auto-check
make task-status
```

### 4. 提交代码到 Git

```bash
# 重要检查点后提交
git add .
git commit -m "checkpoint: $(date +%Y%m%d_%H%M%S) - 阶段说明"
git push
```

---

**此示例展示了在实际开发中如何使用自动编排器进行长期任务管理。**

