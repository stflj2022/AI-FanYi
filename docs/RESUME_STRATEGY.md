# 长期任务进度管理策略

## 问题背景

1. **上下文窗口限制**: AI 模型有固定的上下文窗口（如 1M tokens）
2. **API 额度限制**: 智谱 API 每 5 小时重置一次额度
3. **任务中断风险**: 长时间运行的任务可能因各种原因中断

## 解决方案

### 1. 任务分解策略

将大任务分解为独立的、可恢复的小任务：

```
大任务
├── 子任务 1 (独立) → 完成后保存状态
├── 子任务 2 (独立) → 完成后保存状态
├── 子任务 3 (独立) → 完成后保存状态
└── ...
```

### 2. 进度持久化

#### 进度文件格式

```yaml
# .claude/task-progress.yaml
task_id: "implement-m01-module"
started_at: "2024-01-21T10:00:00Z"
last_update: "2024-01-21T11:30:00Z"

status: "in_progress"

phases:
  - id: "database-models"
    name: "创建数据库模型"
    status: "completed"
    completed_at: "2024-01-21T10:45:00Z"
    outputs:
      - "src/db/models.py"

  - id: "api-endpoints"
    name: "创建 API 端点"
    status: "in_progress"
    started_at: "2024-01-21T10:50:00Z"
    current_step: "创建项目端点"
    completed_steps:
      - "定义数据模型"
      - "创建依赖注入"

  - id: "testing"
    name: "编写测试"
    status: "pending"
    depends_on: ["api-endpoints"]

context_summary: |
  M01 模块实现进度 50%:
  - 数据库模型已完成
  - API 端点进行中（已完成 2/4 步骤）
  - 下一步：完成剩余 API 端点，然后编写测试
```

#### 进度管理脚本

```bash
#!/bin/bash
# scripts/manage-progress.sh

PROGRESS_FILE=".claude/task-progress.yaml"

# 保存进度
save_progress() {
    local phase_id=$1
    local status=$2
    local message=$3

    cat > $PROGRESS_FILE <<EOF
task_id: "$TASK_ID"
started_at: "$START_TIME"
last_update: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
status: "$status"

current_phase:
  id: "$phase_id"
  status: "$status"
  message: "$message"

context_summary: |
  $CONTEXT_SUMMARY
EOF

    echo "✓ 进度已保存到 $PROGRESS_FILE"
}

# 加载进度
load_progress() {
    if [ -f "$PROGRESS_FILE" ]; then
        echo "找到进度文件，恢复任务..."
        cat $PROGRESS_FILE
        return 0
    else
        echo "无进度文件，开始新任务"
        return 1
    fi
}
```

### 3. 使用 Workflow 工具

Workflow 支持断点续传：

```javascript
// workflows/implement-module.js

export const meta = {
    name: 'implement-module',
    description: '实现指定模块的代码',
    phases: [
        { title: 'Design' },
        { title: 'Implement' },
        { title: 'Test' }
    ]
}

const progress = loadProgress();

if (progress) {
    // 从进度恢复
    const resumePhase = progress.current_phase;
    log(`从 ${resumePhase} 阶段恢复...`);

    // 跳过已完成的阶段
    for (const phase of completedPhases) {
        log(`跳过已完成的 ${phase}`);
    }
}

// 继续执行
phase('Implement')
const result = await agent("实现 M01 模块...", {phase: 'Implement'})

// 保存进度
saveProgress({
    current_phase: 'Test',
    completed_phases: ['Design', 'Implement'],
    context: result.summary
})
```

### 4. 智谱额度管理

#### 额度监控脚本

```python
# scripts/check-quota.py

#!/usr/bin/env python3
"""检查智谱 API 额度并智能调度"""

import os
import time
import requests
from datetime import datetime, timedelta

class QuotaManager:
    def __init__(self):
        self.reset_interval = 5 * 60 * 60  # 5小时
        self.usage_file = ".claude/quota-usage.json"
        self.load_usage()

    def load_usage(self):
        if os.path.exists(self.usage_file):
            with open(self.usage_file) as f:
                data = json.load(f)
                self.last_reset = datetime.fromisoformat(data['last_reset'])
                self.tokens_used = data['tokens_used']
        else:
            self.last_reset = datetime.now()
            self.tokens_used = 0

    def save_usage(self):
        with open(self.usage_file, 'w') as f:
            json.dump({
                'last_reset': self.last_reset.isoformat(),
                'tokens_used': self.tokens_used,
                'last_check': datetime.now().isoformat()
            }, f)

    def check_reset(self):
        """检查是否已过重置时间"""
        now = datetime.now()
        elapsed = (now - self.last_reset).total_seconds()

        if elapsed >= self.reset_interval:
            print(f"✓ 额度已重置！距离上次重置: {elapsed/3600:.1f} 小时")
            self.last_reset = now
            self.tokens_used = 0
            self.save_usage()
            return True
        else:
            remaining = self.reset_interval - elapsed
            print(f"距离下次重置: {remaining/3600:.1f} 小时")
            return False

    def estimate_safe_task(self, estimated_tokens):
        """估算是否安全执行任务"""
        self.check_reset()

        # 假设智谱每5小时有约 1M tokens 额度
        max_quota = 1000000
        remaining = max_quota - self.tokens_used

        if estimated_tokens > remaining:
            print(f"⚠️  额度不足！需要 {estimated_tokens}，剩余 {remaining}")
            return False

        return True

    def wait_for_reset(self):
        """等待额度重置"""
        now = datetime.now()
        elapsed = (now - self.last_reset).total_seconds()
        remaining = self.reset_interval - elapsed

        if remaining > 0:
            print(f"等待额度重置: {remaining/60:.1f} 分钟")
            print(f"预计重置时间: {(now + timedelta(seconds=remaining)).strftime('%H:%M')}")

            # 保存当前状态
            self.save_progress_before_wait()

            # 等待（带提醒）
            time.sleep(remaining)

            self.check_reset()
            return True
        return False

    def save_progress_before_wait(self):
        """等待前保存进度"""
        print("💾 等待前保存进度...")
        # 调用保存进度逻辑
        os.system("make save-progress")
```

### 5. Agent 技能配置

在 CLAUDE.md 中添加断点续传技能：

```markdown
## 断点续传技能

当检测到上下文快满或额度不足时：

1. **自动保存进度**
   - 将当前状态保存到 `.claude/task-progress.yaml`
   - 生成简洁的上下文摘要
   - 记录已完成和待完成的任务

2. **生成恢复指令**
   - 创建恢复脚本
   - 标注恢复点

3. **智能分段**
   - 将大任务分成 5-10 个子任务
   - 每个子任务独立可验证
   - 子任务间通过 Artifact 传递数据

### 恢复指令

当任务中断后，使用以下指令恢复：

```
/resume from ".claude/task-progress.yaml"
继续 M01 模块实现，从 API 端点设计阶段恢复。
当前进度: 数据库模型已完成，API 端点完成 50%。
下一步: 完成剩余 API 端点。
```
```

### 6. 实用命令

#### Makefile 添加

```makefile
# 进度管理
save-progress: ## 保存当前进度
	@echo "保存任务进度..."
	@bash scripts/save-current-progress.sh

load-progress: ## 加载进度
	@echo "加载任务进度..."
	@cat .claude/task-progress.yaml 2>/dev/null || echo "无进度文件"

check-quota: ## 检查 API 额度
	@python3 scripts/check-quota.py

wait-reset: ## 等待额度重置并恢复
	@python3 scripts/wait-for-reset.py

resume: ## 从进度恢复
	@echo "从进度恢复任务..."
	@bash scripts/resume-from-progress.sh
```

## 最佳实践

### 1. 任务大小控制

- ✅ 每个子任务 < 50K tokens
- ✅ 每个会话完成 1-2 个子任务
- ✅ 子任务间通过文件/Artifact 传递状态

### 2. 进度检查点

- ✅ 每完成一个模块保存进度
- ✅ 生成代码后立即提交
- ✅ 每个阶段输出可验证的文件

### 3. 额度管理

- ✅ 任务开始前检查额度
- ✅ 额度不足时等待重置
- ✅ 重置后自动恢复

### 4. 上下文管理

- ✅ 定期创建会话摘要
- ✅ 删除已完成的旧内容
- ✅ 使用引用而非重复内容

## 使用示例

### 开始长期任务

```bash
# 1. 开始任务
make start-task MODULE=m01

# 2. 自动执行并保存进度
# Claude 会自动在额度快用完时保存

# 3. 等待重置
make wait-reset

# 4. 恢复任务
make resume
```

### 手动保存进度

```markdown
@Claude 请保存当前进度到 .claude/task-progress.yaml

当前状态:
- M01 数据库模型已完成
- API 端点进行中 (50%)
- 下一步: 完成 CRUD 操作实现
```

## 工具集成

这些策略可以集成到：

1. **Workflow 工具**: 自动进度管理
2. **Agent 工具**: 子任务分解
3. **Makefile**: 便捷命令
4. **GitHub Actions**: CI/CD 断点续传

## 监控和告警

```python
# 额度告警
def alert_quota_low(remaining_ratio):
    if remaining_ratio < 0.2:
        send_notification(f"⚠️ API 额度仅剩 {remaining_ratio*100}%")
    if remaining_ratio < 0.05:
        send_notification("🚨 API 额度即将耗尽，建议暂停任务")
```
