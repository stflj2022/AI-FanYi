# Unattended Dev System - Quick Start Guide v1.1

**Enhanced with security validation, platform support, and troubleshooting**

## Installation

### Prerequisites Check

Before installing, ensure you have:
- Bash 4.0+ or compatible shell
- Git 2.0+ with SSH key configured (for auto-push)
- Python 3.11+ (for Python projects)
- Node.js 16+ (for JavaScript/TypeScript)
- Go 1.20+ (for Go projects)
- Rust 1.70+ (for Rust projects)
- Java 8+ + Maven/Gradle (for Java projects)

### Step 1: Navigate to Your Project

```bash
cd /path/to/your/project
```

### Step 2: Run the Skill

```bash
/unattended-dev-system
```

The skill will automatically:
1. ✅ Validate environment (checks required commands)
2. ✅ Detect project type (Python/JS/Go/Rust/Java/Generic)
3. ✅ Generate configuration files
4. ✅ Create necessary directories
5. ✅ Validate installation
6. ✅ Ask for AI providers

### Step 3: Configure AI Providers (if not during install)

```bash
# Edit config
nano .unattended/config.json

# Update providers list:
{
  "driver": {
    "providers": [
      "zai-coding-cn/glm-4.7",
      "deepseek/deepseek-v4-flash"
    ]
  }
}
```

### Step 4: Verify Installation

```bash
# Test the skill
bash ~/.pi/agent/skills/unattended-dev-system/test-skill.sh

# Check status
python orchestrator.py --status
```

## First Run

### Option A: Background (Recommended)

```bash
# Start driver in tmux session
tmux new-session -d -s dev-driver './driver.sh'

# Install watchdog (cron every 10 minutes)
( crontab -l 2>/dev/null | grep -v watchdog.sh ; \
  echo "*/10 * * * * * $(pwd)/watchdog.sh" ) | crontab -

# Monitor logs
tail -f .unattended/logs/driver.log
```

### Option B: Foreground (Testing)

```bash
# Run in foreground for testing
./driver.sh

# Or with debug output
bash -x driver.sh
```

## Monitoring

### View Status

```bash
# All status
python orchestrator.py --status

# Checkpoints
python orchestrator --list-checkpoints

# Quota usage
python orchestrator --check

# Task progress
cat .unattended/status.yaml
```

### View Logs

```bash
# Driver logs (real-time)
tail -f .unattended/logs/driver.log

# Orchestrator logs
tail -f .unattended/logs/orchestrator.log

# Watchdog logs
tail .unattended/logs/watchdog.log

# Filter errors
grep ERROR .unattended/logs/driver.log | tail -20

# Filter warnings
grep WARNING .unattended/logs/driver.log | tail -20
```

### Health Check

```bash
# Quick health check
pgrep -f "driver.sh" && echo "✅ Driver running" || echo "❌ Driver not running"

# Check lock file
ls -la /tmp/*-driver.lock || echo "✅ No lock file"

# Last activity
stat -c %y .unattended/logs/driver.log | xargs -I {} date -d @{}
```

## Common Commands

### Status & Progress

```bash
# View current status
python orchestrator.py --status

# List all checkpoints
python orchestrator --list-checkpoints

# View latest checkpoint
python orchestrator.py --list-checkpoints | head -5

# Check quota usage
python orchestrator.py --check
```

### Checkpoint Management

```bash
# Save checkpoint
python orchestrator.py --save "database-design" "完成数据库schema设计" "开始实现ORM模型" "使用SQLAlchemy 2.0"

# Generate resume instruction
python orchestrator.py --resume > .unattended/RESUME.txt
cat .unattended/RESUME.txt
```

### Driver Control

```bash
# Stop driver
tmux kill-session -t dev-driver

# Restart driver
tmux kill-session -t dev-driver
tmux new-session -d -s dev-driver './driver.sh'

# View in tmux
tmux attach -t dev-driver
# Press Ctrl+B then D to detach

# Check tmux sessions
tmux ls
```

### Watchdog Control

```bash
# Check watchdog status
tail .unattended/logs/watchdog.log

# Reinstall watchdog
( crontab -l 2>/dev/null | grep -v watchdog.sh ; \
  echo "*/10 * * * * $(pwd)/watchdog.sh" ) | crontab -

# Remove watchdog
crontab -l | grep -v watchdog.sh | crontab -
```

## Configuration

### Edit Configuration File

```bash
nano .unattended/config.json
```

### Key Settings

```json
{
  "driver": {
    "providers": ["provider1/model", "provider2/model"],
    "timeout": 7200,
    "zero_output_fuse": 900,
    "check_interval": 300
  },
  "watchdog": {
    "stuck_threshold_minutes": 45,
    "check_interval_minutes": 10
  },
  "testing": {
    "command": "pytest tests/ -q",
    "auto_commit": true
  },
  "git": {
    "auto_push": true,
    "commit_message_format": "chore(driver): {message}"
  },
  "notification": {
    "enabled": false,
    "webhook": "https://..."
  }
}
```

## Platform-Specific Notes

### Linux
- ✅ Fully supported
- Default platform, all features available
- Cron job configuration works natively

### macOS
- ✅ Supported with some limitations
- Cron launchd by launchd
- File paths use `stat -f` instead of `stat -c %Y`
- Flock may behave differently

### Windows (WSL)
- ⚠️ Partial support
- Bash 5.0+ required (WSL or Git Bash)
- Cron replacement needed (Task Scheduler)
- File locks may not work reliably

### Windows (Git Bash)
- ⚠️ Partial support
- Requires Git Bash
- Cron replacement needed
- POSIX commands may need adaptation

## Troubleshooting

### Issue: Installation Fails

```bash
# Check which step failed
bash -x install.sh 2>&1 | tail -50

# Common issues:
# - Required command not found: Install missing dependency
# - Python 3.11+ not found: Install or upgrade Python
# - Git not configured: Configure git user.name and user.email
```

### Issue: Driver Won't Start

```bash
# Check lock file
ls -la /tmp/*-driver.lock
rm -f /tmp/*-driver.lock

# Check syntax
bash -n driver.sh

# Try manually
./driver.sh
```

### Issue: Tests Keep Failing

```bash
# Run tests manually
{{TEST_COMMAND}}

# Check specific test file
pytest tests/test_specific.py -v

# Fix tests, then restart
tmux kill-session -t dev-driver
tmux new-session -d -s dev-driver './driver.sh'
```

### Issue: Git Push Fails

```bash
# Check SSH key
ssh -T git@github.com

# Check git config
git config user.name
git config user.email

# Test push manually
git push origin HEAD
```

### Issue: Provider Quota Exhausted

```bash
# Check quota
python orchestrator.py --check

# Check for quota errors
grep -i "quota\|429\|余额不足" .unattended/logs/driver.log | tail -10

# Switch provider manually (if needed)
# Edit .unattended/config.json
```

### Issue: Driver Keeps Restarting

```bash
# Check watchdog log
tail .unattended/logs/watchdog.log

# Check driver log for errors
grep ERROR .unattended/logs/driver.log | tail -20

# Check for zero output
grep "⏳ 零输出熔断" .unattended/logs/driver.log | tail -10
```

## Best Practices

### 1. Start Small
- Test with a simple task first
- Monitor closely for first few rounds
- Adjust timeouts based on your tasks

### 2. Monitor Regularly
- Check logs every hour
- Review checkpoints daily
- Review git commits daily

### 3. Keep Tests Fast
- Use test caching
- Run only changed tests
- Avoid long-running tests

### 4. Use Version Control
- Every change is committed
- Each commit has descriptive message
- Review before pushing

### 5. Security
- Don't expose API keys in logs
- Use environment variables for secrets
- Limit write permissions

## Advanced Usage

### Dry Run Mode

```bash
# Create dry-run mode in driver.sh
DRY_RUN=true ./driver.sh
# Will simulate without actual AI execution
```

### Multiple Projects

```bash
# Each project gets its own instance
cd ~/projects/project1
/unattended-dev-system
tmux new-session -d -s dev-driver-1 './driver.sh'

cd ~/projects/project2
/unattended-dev-system
tmux new-session -d -s dev-driver-2 './driver.sh'
```

### Custom Test Commands

Edit `.unattended/config.json`:

```json
{
  "testing": {
    "command": "pytest tests/ -v --cov=src --cov-report=html",
    "auto_commit": true
  }
}
```

### Multiple Notification Channels

Edit `.unattended/config.json`:

```json
{
  "notification": {
    "enabled": true,
    "channels": [
      {
        "type": "slack",
        "webhook": "https://hooks.slack.com/services/...",
        "on_events": ["task_complete", "error", "ALL_DONE"]
      },
      {
        "type": "email",
        "to": "team@example.com",
        "on_events": ["ALL_DONE"]
      }
    ]
  }
}
```

## Getting Help

### Documentation

```bash
# Full skill documentation
cat SKILL.md

# Architecture docs
cat docs/ARCHITECTURE.md

# ADRs
ls docs/adr/

# Glossary
cat docs/glossary.md
```

### Examples

```bash
# Usage examples
cat docs/EXAMPLES.md

# Quick reference
cat docs/QUICKSTART.md
```

### Support

```bash
# View status
python orchestrator.py --status

# Check logs
tail -f .unattended/logs/driver.log

# Generate resume instruction
python orchestrator --resume
```

---

**Version**: 1.1  
**Based on**: AI-FanYi v7 (ed81d91)  
**Enhanced**: Security validation, platform support, better error handling  
**Last Updated**: 2026-08-23 03:15
