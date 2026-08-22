# Unattended Dev System - Examples

This document provides examples of using the unattended development system in different types of projects.

## Python Projects

### FastAPI Project

```bash
# Install skill (in project root)
cd my-fastapi-project
/unattended-dev-system

# The skill will auto-detect:
# - Language: python
# - Framework: FastAPI
# - Test command: pytest tests/ -q

# Start
tmux new-session -d -s dev-driver './driver.sh'
```

### Django Project

```bash
# Install
cd my-django-project
/unattended-dev-system

# Auto-detected test command:
# - python manage.py test

# Configure providers
nano .unattended/config.json
# Update "driver.providers" with your AI providers

# Start
tmux new-session -d -s dev-driver './driver.sh'
```

## JavaScript/TypeScript Projects

### Node.js Project

```bash
# Install
cd my-nodejs-project
/unattended-dev-system

# Auto-detected:
# - Language: javascript/typescript
# - Framework: Node.js
# - Test command: npm test

# Start
tmux new-session -d -s dev-driver './driver.sh'
```

### Express.js Project

```bash
# Install
cd my-express-project
/unattended-dev-system

# Configure test command in .unattended/config.json:
# "testing": { "command": "npm test" }

# Start
tmux new-session -d -s dev-driver './driver.sh'
```

### React Project

```bash
# Install
cd my-react-app
/unattended-dev-system

# For frontend projects, you might want to:
# 1. Configure test command to run lint + build
# 2. Set up separate test runner

# Edit .unattended/config.json:
{
  "testing": {
    "command": "npm run lint && npm run build"
  }
}

# Start
tmux new-session -d -s dev-driver './driver.sh'
```

## Go Projects

```bash
# Install
cd my-go-project
/unattended-dev-system

# Auto-detected:
# - Language: go
# - Framework: Go
# - Test command: go test ./...

# Start
tmux new-session -d -s dev-driver './driver.sh'
```

## Generic Projects

For projects without standard structure:

```bash
# Install
cd my-custom-project
/unattended-dev-system

# The skill will detect as "generic"
# Edit .unattended/config.json to configure:

{
  "driver": {
    "providers": ["your-provider/your-model"],
    "timeout": 3600
  },
  "testing": {
    "command": "make test",
    "auto_commit": false
  },
  "git": {
    "auto_push": false
  }
}

# Start
tmux new-session -d -s dev-driver './driver.sh'
```

## Common Workflows

### Workflow 1: Feature Development

```bash
# 1. Use Matt skills to plan
/grill-me
/to-spec
/to-tickets

# 2. Install and start unattended system
/unattended-dev-system
tmux new-session -d -s dev-driver './driver.sh'

# 3. Monitor
tail -f .unattended/logs/driver.log

# 4. Check progress periodically
cat .unattended/status.yaml
python orchestrator.py --list-checkpoints
```

### Workflow 2: Bug Fixing

```bash
# 1. Grill the bug
/grill-me

# 2. Use implement to fix
/implement

# 3. Start unattended for testing
/unattended-dev-system

# 4. Configure to run tests only
# Edit .unattended/config.json:
{
  "driver": {
    "providers": ["provider/model"]
  },
  "testing": {
    "command": "pytest tests/test_bug_fix.py -v"
  }
}
```

### Workflow 3: Refactoring

```bash
# 1. Define refactoring scope
# 2. Create tasks manually in .unattended/tasks/todo/
cat > .unattended/tasks/todo/001-refactor-auth.md << 'EOF'
# Task: Refactor Authentication

## Description
Refactor authentication system to use JWT

## Acceptance Criteria
- [ ] Implement JWT generation
- [ ] Implement JWT validation
- [ ] Update all endpoints
- [ ] Tests pass

## Testing
```bash
pytest tests/test_auth.py -v
```
EOF

# 3. Start system
/unattended-dev-system
tmux new-session -d -s dev-driver './driver.sh'
```

### Workflow 4: Documentation Generation

```bash
# 1. Create tasks for documentation
cat > .unattended/tasks/todo/001-api-docs.md << 'EOF'
# Task: Generate API Documentation

## Description
Generate comprehensive API documentation

## Acceptance Criteria
- [ ] Document all endpoints
- [ ] Add examples
- [ ] Generate OpenAPI spec

## Testing
```bash
npm run docs
```
EOF

# 2. Configure for documentation work
# Edit .unattended/config.json:
{
  "testing": {
    "command": "npm run docs",
    "auto_commit": true
  }
}

# 3. Start system
tmux new-session -d -s dev-driver './driver.sh'
```

## Advanced Examples

### Example 1: Multi-Provider Setup

```json
// .unattended/config.json
{
  "driver": {
    "providers": [
      "zai-coding-cn/glm-4.7",
      "deepseek/deepseek-v4-flash",
      "anthropic/claude-sonnet-4-5"
    ]
  }
}
```

### Example 2: Custom Test Command

```json
// .unattended/config.json
{
  "testing": {
    "command": "pytest tests/ -v --cov=src --cov-report=html",
    "auto_commit": true
  }
}
```

### Example 3: Notification Setup

```json
// .unattended/config.json
{
  "notification": {
    "enabled": true,
    "webhook": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    "on_events": ["task_complete", "error", "quota_limit"]
  }
}
```

### Example 4: Custom Timeout Settings

```json
// .unattended/config.json
{
  "driver": {
    "timeout": 3600,           // 1 hour per round
    "zero_output_fuse": 600,   // 10 minutes no output
    "check_interval": 180      // Check every 3 minutes
  }
}
```

## Integration with CI/CD

### GitHub Actions

```yaml
# .github/workflows/unattended.yml
name: Unattended Dev System

on:
  workflow_dispatch:

jobs:
  run-driver:
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
      - name: Run unattended driver
        run: |
          chmod +x driver.sh
          ./driver.sh
        timeout-minutes: 360
```

### GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - unattended

unattended:
  stage: unattended
  script:
    - chmod +x driver.sh
    - ./driver.sh
  timeout: 6 hours
  only:
    - schedules
```

## Monitoring and Debugging

### Log Analysis

```bash
# Show errors
grep ERROR .unattended/logs/driver.log

# Show warnings
grep WARNING .unattended/logs/driver.log

# Show provider switches
grep "Switching to provider" .unattended/logs/driver.log

# Show checkpoints
grep "Checkpoint saved" .unattended/logs/driver.log
```

### Health Check Script

```bash
#!/bin/bash
# health-check.sh

echo "=== Unattended System Health Check ==="

# Check driver
if pgrep -f "driver.sh" > /dev/null; then
    echo "✅ Driver running"
else
    echo "❌ Driver not running"
fi

# Check watchdog
if crontab -l | grep -q "watchdog.sh"; then
    echo "✅ Watchdog installed"
else
    echo "❌ Watchdog not installed"
fi

# Check logs
if [ -f ".unattended/logs/driver.log" ]; then
    echo "✅ Driver log exists"
    echo "   Last update: $(stat -c %y .unattended/logs/driver.log)"
else
    echo "❌ Driver log missing"
fi

# Check status
if [ -f ".unattended/status.yaml" ]; then
    echo "✅ Status file exists"
    cat .unattended/status.yaml
else
    echo "❌ Status file missing"
fi

# Check tasks
TODO_COUNT=$(ls .unattended/tasks/todo/ 2>/dev/null | wc -l)
DONE_COUNT=$(ls .unattended/tasks/done/ 2>/dev/null | wc -l)
echo "Tasks: $DONE_COUNT done, $TODO_COUNT todo"
```

## Best Practices

### 1. Start Small

```bash
# Test with a simple task first
echo "# Test Task" > .unattended/tasks/todo/000-test.md

# Run for one round to verify
timeout 600 ./driver.sh
```

### 2. Monitor Closely

```bash
# Watch logs in real-time
tail -f .unattended/logs/driver.log | grep -E "ERROR|WARNING|✅|❌"
```

### 3. Set Reasonable Timeouts

```bash
# Adjust based on your tasks
# Fast tasks: 1800 seconds (30 min)
# Slow tasks: 14400 seconds (4 hours)
```

### 4. Keep Tests Fast

```bash
# Use pytest cache
pytest --cache-show

# Run only changed tests
pytest tests/ --changed-only
```

### 5. Use Version Control

```bash
# Every change is committed automatically
# But review regularly
git log --oneline -20
```

## Troubleshooting Common Issues

### Issue: Driver keeps restarting

```bash
# Check watchdog log
tail .unattended/logs/watchdog.log

# Check if tests are failing
pytest tests/ -v

# Fix tests, then restart
```

### Issue: Git push failing

```bash
# Check git config
git config user.name
git config user.email

# Check SSH key
ssh -T git@github.com

# Test push manually
git push origin HEAD
```

### Issue: Provider quota exhausted

```bash
# Check quota
python orchestrator.py --check

# Configure fallback provider
# Edit .unattended/config.json

# Wait for reset or switch manually
```

---

**More Examples**: See `SKILL.md` for complete documentation
