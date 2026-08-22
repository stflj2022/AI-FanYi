# Unattended Dev System Skill - 使用示例

## 示例 1: 在 Python 项目中使用

```bash
# 假设你有一个 Python FastAPI 项目
cd ~/projects/my-api

# 运行 skill
/unattended-dev-system

# Skill 会自动检测：
# ✓ Language: python
# ✓ Framework: FastAPI
# ✓ Test command: pytest tests/ -q

# 配置 providers
# 输入: zai-coding-cn/glm-4.7
# 输入: deepseek/deepseek-v4-flash

# 生成的文件结构：
my-api/
├── driver.sh
├── watchdog.sh
├── orchestrator.py
└── .unattended/
    ├── config.json
    ├── status.yaml
    ├── tasks/
    ├── checkpoints/
    └── logs/

# 启动系统
tmux new-session -d -s dev-driver './driver.sh'

# 安装看门狗
( crontab -l 2>/dev/null | grep -v watchdog.sh ; \
  echo "*/10 * * * * $(pwd)/watchdog.sh" ) | crontab -

# 监控
tail -f .unattended/logs/driver.log
```

## 示例 2: 在 Node.js 项目中使用

```bash
# 假设你有一个 Node.js Express 项目
cd ~/projects/my-express-api

# 运行 skill
/unattended-dev-system

# Skill 会自动检测：
# ✓ Language: javascript
# ✓ Framework: Node.js
# ✓ Test command: npm test

# 启动系统
tmux new-session -d -s dev-driver './driver.sh'

# 监控
tail -f .unattended/logs/driver.log
```

## 示例 3: 配合 Matt Skills 使用

```bash
cd ~/projects/my-project

# 阶段 1: 使用 Matt skills 规划
/grill-me               # 质询需求
/to-spec                # 生成规范
/to-tickets             # 分解任务

# 阶段 2: 部署无人值守系统
/unattended-dev-system

# 阶段 3: 创建任务文件
mkdir -p .unattended/tasks/todo
cat > .unattended/tasks/todo/001-implementation.md << 'EOF'
# Task 001: Implement Core Feature

## Description
Implement the core authentication module

## Acceptance Criteria
- [ ] User registration
- [ ] Login with JWT
- [ ] Password reset
- [ ] All tests pass

## Testing
```bash
pytest tests/test_auth.py -v
```

## Dependencies
- Depends on: Task 000 (Setup database)
EOF

# 阶段 4: 启动系统
tmux new-session -d -s dev-driver './driver.sh'

# 阶段 5: 监控进度
watch -n 10 'cat .unattended/status.yaml'

# 阶段 6: 完成后代码审查
/code-review main
```

## 示例 4: 手动保存检查点

```bash
# 在开发过程中保存进度
python orchestrator.py --save \
    "database-design" \
    "完成数据库 schema 设计" \
    "开始实现 ORM 模型" \
    "使用了 SQLAlchemy 2.0，包含 10 张表"

# 查看所有检查点
python orchestrator.py --list-checkpoints

# 生成恢复指令
python orchestrator.py --resume > .unattended/RESUME.txt
cat .unattended/RESUME.txt
```

## 示例 5: 配置自定义测试命令

```bash
# 编辑配置
nano .unattended/config.json

# 修改测试命令为：
{
  "testing": {
    "command": "pytest tests/ -v --cov=src --cov-report=html",
    "auto_commit": true
  }
}

# 重启驱动使配置生效
tmux kill-session -t dev-driver
tmux new-session -d -s dev-driver './driver.sh'
```

## 示例 6: 配置通知

```bash
# 编辑配置
nano .unattended/config.json

# 添加通知配置：
{
  "notification": {
    "enabled": true,
    "webhook": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    "on_events": ["task_complete", "error", "quota_limit"]
  }
}

# 现在每当任务完成、出错或配额耗尽时，会收到 Slack 通知
```

## 示例 7: 手动停止和重启

```bash
# 查看状态
tmux ls

# 停止驱动
tmux kill-session -t dev-driver

# 查看最后的日志
tail -100 .unattended/logs/driver.log

# 重新启动
tmux new-session -d -s dev-driver './driver.sh'

# 验证运行
pgrep -f driver.sh
```

## 示例 8: 清理和重新开始

```bash
# 停止系统
tmux kill-session -t dev-driver
crontab -l | grep -v watchdog.sh | crontab -

# 清理文件（可选）
rm -rf .unattended

# 重新安装
/unattended-dev-system

# 重新配置 providers
# 然后启动
tmux new-session -d -s dev-driver './driver.sh'
```

## 示例 9: 查看详细日志

```bash
# 查看驱动日志（实时）
tail -f .unattended/logs/driver.log

# 查看错误
grep ERROR .unattended/logs/driver.log

# 查看 provider 切换
grep "Switching to provider" .unattended/logs/driver.log

# 查看保存的检查点
grep "Checkpoint saved" .unattended/logs/driver.log

# 查看测试运行
grep "test" .unattended/logs/driver.log
```

## 示例 10: 集成到 CI/CD

```yaml
# .github/workflows/unattended.yml
name: Unattended Development

on:
  workflow_dispatch:
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨 2 点运行

jobs:
  unattended-dev:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Install skill
        run: |
          cp -r ~/.pi/agent/skills/unattended-dev-system .
          chmod +x install.sh
          ./install.sh
      - name: Run unattended driver
        run: |
          chmod +x driver.sh
          ./driver.sh
        timeout-minutes: 360
        env:
          CI: true
```

## 示例 11: 多项目并行运行

```bash
# 项目 1
cd ~/projects/project1
/unattended-dev-system
tmux new-session -d -s dev-driver-1 './driver.sh'

# 项目 2
cd ~/projects/project2
/unattended-dev-system
tmux new-session -d -s dev-driver-2 './driver.sh'

# 查看所有驱动
tmux ls

# 分别监控
tail -f ~/projects/project1/.unattended/logs/driver.log
tail -f ~/projects/project2/.unattended/logs/diver.log
```

## 示例 12: 调试模式

```bash
# 前台运行（便于调试）
./driver.sh

# 或使用 bash -x 查看详细执行过程
bash -x ./driver.sh

# 查看配置
python orchestrator.py --status

# 查看最近的检查点
python orchestrator.py --list-checkpoints | head -5
```

---

## 更多示例

查看 `docs/EXAMPLES.md` 获取更多语言和框架的详细示例。
