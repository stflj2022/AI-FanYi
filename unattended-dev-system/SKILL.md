---
name: unattended-dev-system
description: Deploy an unattended autonomous development system with watchdog, auto-recovery, and task management to any software engineering project.
---

# Unattended Dev System Skill

A complete unattended development system that enables AI agents to work autonomously on long-term software engineering tasks with automatic recovery, progress tracking, and resource management.

## What This Skill Does

This skill deploys a complete autonomous development infrastructure consisting of:

1. **Main Driver Loop** - Executes development tasks autonomously
2. **Watchdog Monitor** - Detects and recovers from failures
3. **Auto Orchestrator** - Manages quota, progress, and recovery
4. **Task Management** - Tracks work items and progress
5. **Auto Testing** - Validates each change automatically
6. **Git Integration** - Auto-commits and pushes progress
7. **Auto-Stop on Completion** - When all tasks are done, the system shuts itself down (driver + watchdog + scheduled reports) and sends ONE final notification instead of looping forever

## When to Use

- ✅ Long-term development projects (days to weeks)
- ✅ Large refactoring or migration tasks
- ✅ Multi-module feature implementation
- ✅ Test suite development and maintenance
- ✅ Documentation generation
- ✅ Any task requiring autonomous execution

## How It Works

### System Architecture

```
┌─────────────────────────────────────────────────────────┐
│               Unattended Development System              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Main Driver (driver.sh)                        │   │
│  │  - Task execution loop                           │   │
│  │  - Auto commit + push                            │   │
│  │  - Provider rotation                             │   │
│  │  - Error handling                               │   │
│  └──────────────────────────────────────────────────┘   │
│                         ▲                              │
│                         │ 监控                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Watchdog (watchdog.sh) - Cron every 10min     │   │
│  │  - Process health check                         │   │
│  │  - Stuck detection                              │   │
│  │  - Auto restart                                │   │
│  └──────────────────────────────────────────────────┘   │
│                          ▲                               │
│                          │ 管理                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Auto Orchestrator (orchestrator.py)            │   │
│  │  - Quota monitoring                             │   │
│  │  - Progress saving                              │   │
│  │  - Recovery generation                          │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Core Features

| Feature | Description |
|---------|-------------|
| **Provider Rotation** | Auto-switch between AI providers (quota/health) |
| **Zero-Output Fuse** | Detect stuck processes (configurable timeout) |
| **Context Management** | Auto-restart session on context overflow |
| **Auto Testing** | Run test suite after each change |
| **Progress Tracking** | Save checkpoints for recovery |
| **Auto Recovery** | Watchdog restarts on failure |
| **Git Integration** | Auto-commit and push progress |
| **Task Management** | Track work items with dependencies |
| **Auto-Stop on Completion** | Driver/watchdog detect completion → run `shutdown.sh` → stop everything, send one final notification |

### Auto-Stop on Completion

A finished project must not keep burning quota or spamming notifications. When the driver detects ALL tasks completed AND tests passing (or the watchdog sees the completion marker in the driver log), it runs `shutdown.sh`, which:

1. Removes the watchdog/report entries from crontab (scheduled notifications stop)
2. Writes the `.unattended/STOPPED` marker (every component exits silently when it sees it)
3. Kills the tmux session and any leftover driver processes
4. Sends **exactly one** final "project complete" notification

`shutdown.sh` is idempotent and can also be run manually: `./shutdown.sh 'manual stop'`. To re-enable the system afterwards, delete the STOPPED marker (or re-run install.sh, which clears it).

## Installation

### Quick Start

```bash
# Run the skill
/unattended-dev-system
```

### Step-by-Step Installation

The skill will guide you through:

1. **Project Detection** - Analyze your project type and structure
2. **Configuration** - Customize settings for your project
3. **Template Generation** - Generate tailored scripts
4. **Testing** - Verify the setup works
5. **Deployment** - Start the system

## Configuration

### Auto-Generated Configuration

The skill automatically detects and configures:

- **Language** (Python, JavaScript, TypeScript, Go, etc.)
- **Framework** (FastAPI, Django, Express, etc.)
- **Test Runner** (pytest, jest, go test, etc.)
- **Package Manager** (pip, npm, cargo, etc.)
- **Build System** (make, npm scripts, etc.)
- **Git Repository** (GitHub, GitLab, Bitbucket)

### Manual Configuration Options

You can customize:

```json
{
  "driver": {
    "providers": ["provider1/model", "provider2/model"],
    "check_interval": 300,
    "timeout": 7200,
    "zero_output_fuse": 900
  },
  "watchdog": {
    "check_interval_minutes": 10,
    "stuck_threshold_minutes": 45
  },
  "testing": {
    "command": "pytest tests/ -q",
    "auto_commit": true
  },
  "git": {
    "auto_push": true,
    "commit_message_format": "chore(driver): {message}"
  }
}
```

## Usage

### Starting the System

```bash
# Start driver (in tmux)
tmux new-session -d -s dev-driver 'bash driver.sh'

# Install watchdog (cron)
( crontab -l 2>/dev/null | grep -v watchdog.sh ; \
  echo "*/10 * * * * $(pwd)/watchdog.sh" ) | crontab -
```

### Monitoring

```bash
# View driver logs
tail -f .unattended/driver.log

# View watchdog logs
tail .unattended/watchdog.log

# View current status
cat .unattended/status.yaml

# View tasks
ls -la .unattended/tasks/
```

### Manual Operations

```bash
# Save checkpoint
python orchestrator.py --save <phase> "<message>" "<next>" "<context>"

# Generate recovery instruction
python orchestrator.py --resume > .unattended/RESUME.txt

# Wait for quota reset
python orchestrator.py --wait
```

## Project-Specific Adaptations

### Python Projects

```bash
# Auto-detected:
# - Test command: pytest tests/ -q
# - Venv: .venv/
# - Package manager: pip
```

### JavaScript/TypeScript Projects

```bash
# Auto-detected:
# - Test command: npm test
# - Package manager: npm
# - Build: npm run build
```

### Go Projects

```bash
# Auto-detected:
# - Test command: go test ./...
# - Package manager: go mod
# - Build: go build
```

## Templates

The skill generates these files:

```
.unattended/
├── driver.sh              # Main driver script
├── watchdog.sh            # Watchdog script
├── orchestrator.py        # Auto orchestrator
├── config.json            # Configuration
├── status.yaml            # Current status
├── tasks/                 # Task files
│   ├── todo/
│   ├── doing/
│   └── done/
├── checkpoints/           # Progress checkpoints
├── driver.log             # Driver logs
└── watchdog.log           # Watchdog logs
```

## Best Practices

1. **Start Small** - Test with a simple task first
2. **Monitor Closely** - Check logs regularly
3. **Set Reasonable Timeouts** - Adjust based on your tasks
4. **Keep Tests Fast** - Slow tests slow down the loop
5. **Use Version Control** - Every change is committed
6. **Backup Critical Data** - Regular backups of `.unattended/`
7. **Monitor Provider Quota** - Avoid unexpected stops
8. **Zero-Output Fuse Must Loop, Never Check-Once** - Stall detection must be a *re-arming loop* that checks every few minutes, not a single `sleep N; check-once`. A one-shot check misses the classic "wrote output first, then hung" stall (e.g. a network/TTY hang after an early success): the check passes, never re-arms, and `wait` blocks forever → the whole pipeline freezes, token quota stops moving, and progress reports stay identical every cycle. The default foreground `timeout "$DRIVER_TIMEOUT" ...` path in `driver.sh.template` already covers stalls — keep it. If you must run the AI command in the background (`... &` + `wait`), attach the provided `spawn_stall_watchdog` loop instead of inventing a one-shot fuse.

## Troubleshooting

### Driver Won't Start

```bash
# Check lock file
ls -la /tmp/dev-driver.lock
rm -f /tmp/dev-driver.lock

# Check dependencies
bash driver.sh --check-deps
```

### Driver Stalled / Progress Frozen / Quota Not Moving

**Symptoms**: token quota does not move for a long time, progress reports are identical every cycle, driver log stops growing.

**Root cause**: the AI subprocess hung *after* producing some output (network/TTY hang), and the driver is blocked forever on `wait` in the main loop. A single-shot 900s fuse will NOT catch this — it only checks once right after launch.

**Diagnose**:

```bash
# Find the AI process and check whether it is really dead (low %CPU, TIME not growing)
ps -o pid,etime,time,%cpu,stat -C pi

# Check how stale the driver log is
stat -c '%y' .unattended/driver.log
```

**Fix**:

```bash
# 1. Kill the hung AI process — `wait` returns and the driver proceeds to next round
pkill -TERM -P <ai_pid> 2>/dev/null; kill -TERM <ai_pid> 2>/dev/null

# 2. Confirm the driver uses loop-based stall detection (spawn_stall_watchdog),
#    not a one-shot check; then restart the driver service to load the fix
systemctl --user restart web-ui-driver.service   # or: tmux kill-session -t dev-driver && restart
```

### Tests Keep Failing

```bash
# Run tests manually
pytest tests/ -v

# Fix issues, then restart driver
tmux kill-session -t dev-driver
tmux new-session -d -s dev-driver 'bash driver.sh'
```

### Git Push Fails

```bash
# Check SSH key
ssh -T git@github.com

# Configure git
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

## Integration with Other Skills

Works well with:
- `grill-me` - Clarify design before starting
- `to-spec` - Generate specifications
- `to-tickets` - Break down into tasks
- `implement` - Execute the tasks
- `code-review` - Review the changes

## Advanced Features

### Custom Task Definitions

Create `.unattended/task-template.md`:

```markdown
# Task Template

## Task Description
{{task_description}}

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Dependencies
- Depends on: {{depends_on}}

## Testing
```bash
{{test_command}}
```
```

### Custom Recovery Logic

Add `.unattended/recovery-hook.sh`:

```bash
#!/bin/bash
# Custom recovery logic
echo "Running custom recovery..."
# Your custom logic here
```

### Notification Integration

Configure webhooks in `config.json`:

```json
{
  "notification": {
    "enabled": true,
    "webhook": "https://api.slack.com/...",
    "on_events": ["task_complete", "error", "quota_limit"]
  }
}
```

## Example Workflows

### Workflow 1: Feature Development

```bash
# 1. Grill design
/grill-me

# 2. Generate spec
/to-spec

# 3. Create tasks
/to-tickets

# 4. Start unattended system
/unattended-dev-system

# 5. Monitor progress
tail -f .unattended/driver.log
```

### Workflow 2: Bug Fixing

```bash
# 1. Grill problem
/grill-me

# 2. Fix manually or use implement
/implement

# 3. Start system for testing
/unattended-dev-system
```

### Workflow 3: Refactoring

```bash
# 1. Define refactoring scope
# 2. Create tasks
# 3. Start system
/unattended-dev-system
```

## Removing the System

```bash
# Stop driver
tmux kill-session -t dev-driver

# Remove watchdog
crontab -l | grep -v watchdog.sh | crontab -

# Remove files (optional)
rm -rf .unattended/
rm -f driver.sh watchdog.sh orchestrator.py
```

## See Also

- Project-specific documentation in `.unattended/README.md`
- Generated configuration in `.unattended/config.json`
- Status dashboard (if enabled)

---

**Version**: 1.1.1
**Last Updated**: 2026-08-23

### v1.1.1 (post code-review fixes)

**Security/robustness fixes** (verified by v1.1.1 regression checks in `test-skill.sh`):
- `validate_path` / `validate_ai_command` now called at driver startup (were dead code in v1.1 → injection/path-traversal guards were not active).
- `config.json` read at runtime by driver & watchdog (was never consumed).
- Fixed `git status --porcelain`, `$REPOPO` typo, `get_file_age` returning age, `set -e`+ERR-trap killing driver, `((errors++))` abort, watchdog `{{PROJECT_NAME}}` render, python version check.
