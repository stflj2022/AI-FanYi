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

## When to Use

- ✅ Long-term development projects (days to weeks)
- ✅ Large refactoring or migration tasks
- Multi-module feature implementation
- Test suite development and maintenance
- Documentation generation
- Any task requiring autonomous execution

## How It Works

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│               Unattended Development System              │
├─────────────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Main Driver (driver.sh)                        │   │
│  │  - Task execution loop                           │   │
│  │  - Auto commit + push                            │   │
│  │  - Provider rotation                             │   │
│  │  - Error handling                               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                         ▲                              │
│                         │ 监控                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Watchdog (watchdog.sh) - Cron every 10min     │   │
│  │  - Process health check                         │   │
│  │  - Stuck detection                              │   │
│  │  - Auto restart                                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          ▲                               │
│                          │ 管理                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Auto Orchestrator (orchestrator.py)            │   │
│  │  - Quota monitoring                             │   │
│  │  - Progress saving                              │   │
│  │  - Recovery generation                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────────────┘
```

### Core Features

| Feature | Description |
|---------|-------------|
| **Provider Rotation** | Auto-switch between AI providers (quota/health check) |
| **Zero-Output Fuse** | Detect stuck processes (configurable timeout) |
| **Context Management** | Auto-restart session on overflow |
| **Auto Testing** | Run test suite after each change |
| **Progress Tracking** | Save checkpoints for recovery |
| **Auto Recovery** | Watchdog restarts on failure |
| **Git Integration** | Auto-commit and push progress |
| **Task Management** | Track work items with dependencies |
| **Notification** | Webhook support for Slack/Discord/Email |

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

- **Language** (Python, JavaScript, TypeScript, Go, Rust, Java, Generic)
- **Framework** (Django, FastAPI, Express, Go, Cargo, Maven, Gradle)
- **Test Runner** (pytest, npm test, go test, cargo test, mvn test)
- **Package Manager** (pip, npm, go get, cargo, maven, gradle)
- **Build System** (make, npm scripts, go build, cargo build, mvn package)
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
  },
  "notification": {
    "enabled": false,
    "webhook": null
  }
}
```

## Usage

### Starting the System

```bash
# Start driver (in tmux)
tmux new-session -d -s dev-driver 'bash driver.sh'

# Install watchdog (cron every 10min)
( crontab -l 2>/dev/null | grep -v watchdog.sh ; \
  echo "*/10 * * * * $(pwd)/watchdog.sh" ) | crontab -
```

### Monitoring

```bash
# View driver logs
tail -f .unattended/logs/driver.log

# View watchdog logs
tail .unattended/logs/watchdog.log

# View current status
cat .unattended/status.yaml

# List checkpoints
python orchestrator.py --list-checkpoints

# Check quota
python orchestrator.py --check
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

Auto-detected configurations:
- Test command: `pytest tests/ -q`
- Virtualenv: `.venv/` or `venv/`
- Package manager: `pip`

### JavaScript/TypeScript Projects

Auto-detected configurations:
- Test command: `npm test`
- Package manager: `npm`
- Build: `npm run build`

### Go Projects

Auto-detected configurations:
- Test command: `go test ./...`
- Package manager: `go mod`
- Build: `go build`

### Go Projects

Auto-detected configurations:
- Test command: `cargo test`
- Package manager: `cargo`
- Build: `cargo build`

### Java Projects

Auto-detected configurations:
- Test command: `mvn test`
- Package manager: `mvn` or `gradle`

## Templates

The skill generates these files:

```
.unattended/
├── driver.sh              # Main driver script
├── watchdog.sh            # Watchdog monitor
├── orchestrator.py        # Auto orchestrator
├── config.json            # Configuration
├── status.yaml            # Current status
├── tasks/                 # Task files
├── checkpoints/           # Progress checkpoints
├── logs/                 # Log files
├── docs/                  # Documentation
│   ├── ADR/              # Architecture decisions
│   ├── glossary.md         # Term definitions
│   └── ARCHITECTURE.md       # System architecture
└── README.md               # User guide
```

## Best Practices

1. **Start Small** - Test with a simple task first
2. **Monitor Closely** - Check logs regularly
3. **Set Reasonable Timeouts** - Adjust based on your tasks
4. **Keep Tests Fast** - Slow tests slow down the loop
5. **Use Version Control** - Every change is committed
6. **Monitor Provider Quota** - Avoid unexpected stops
7. **Backup Critical Data** - Regular backups of `.unattended/`

## Troubleshooting

### Driver Won't Start

```bash
# Check lock file
ls -la /tmp/*-driver.lock
rm -f /tmp/*-driver.lock

# Check dependencies
bash ~/.pi/agent/skills/unattended-dev-system/test-skill.sh

# Check logs
cat .unattended/logs/driver.log | tail -50
```

### Tests Keep Failing

```bash
# Run tests manually
{{TEST_COMMAND}}

# Fix issues, then restart driver
tmux kill-session -t dev-driver
tmux new-session -d -s dev-driver './driver.sh'
```

### Git Push Fails

```bash
# Check SSH key
ssh -T git@github.com

# Configure git
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

### Provider Quota Exhausted

```bash
# Check quota
python orchestrator.py --check

# Switch provider manually
nano .unattended/config.json
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

Create `.unattended/task-template.md` for custom task format.

### Custom Recovery Logic

Add `.unattended/recovery-hook.sh` for custom recovery logic.

### Notification Integration

Configure webhooks in `config.json`:
```json
{
  "notification": {
    "enabled": true,
    "webhook": "https://..."
  }
}
```

## Documentation

- **Full documentation**: `SKILL.md`
- **Quick start**: `docs/QUICKSTART.md`
- **Examples**: `docs/EXAMPLES.md`
- **Summary**: `README.md`
- **Test results**: `test-skill.sh`

---

**Version**: 1.2.0
**Last Updated**: 2026-08-23
**Based on**: AI-FanYi v7 (commit ed81d91)

## v1.2.0 changelog (completion auto-stop)

- **Auto-stop on completion (NEW)**: new `shutdown.sh.template` — one-stop, idempotent shutdown that removes watchdog/report cron entries, writes the `.unattended/STOPPED` marker, kills the driver and sends exactly ONE final notification.
- **driver.sh**: on ALL TASKS COMPLETED + tests pass it now calls `shutdown.sh` and exits (was: `break`, after which cron/watchdog would restart it forever); each round also exits silently when the STOPPED marker exists.
- **watchdog.sh**: honors the STOPPED marker (never restarts after completion) and triggers `shutdown.sh` when it detects completion in the driver log (was: silent `exit 0` while reports kept firing).
- **install.sh**: generates/chmods/syntax-checks `shutdown.sh`; fixed pre-existing bugs — bare quoted strings executed as commands in `setup_complete` (would abort under `set -e`), wrong `templates/docs/` paths for README/QUICKSTART, missing `> QUICKSTART.md` redirect.
- **test-skill.sh**: 4 new regression checks (R7–R10) covering the auto-stop wiring.

## v1.1.1 changelog (post code-review fixes)

- **Security fixes now actually enforced** (were dead code in v1.1): `validate_path` and `validate_ai_command` are now called at driver startup; rewrote `validate_ai_command` (case `|` separator bug + prefix matching).
- **Config.json now read at runtime** by both `driver.sh` and `watchdog.sh` (was written but never consumed). CLI `--dry-run` wins over config.
- **Bug fixes**: `git status --porcelain` (was invalid `git --porcelain`, commits never happened); `$REPOPO` typo in watchdog; `get_file_age` now returns *age in seconds* (was mtime); `((errors++))`/`((missing_count++))` abort under `set -e` (now `$((var+1))`); `{{PROJECT_NAME}}` now substituted into watchdog render; `set -e`/ERR-trap no longer kill the driver before exit-code handling (`timeout ... || EXIT_CODE=$?`); python version check fixed.
- **watchdog**: `detect_platform` now called; single-instance flock guard; age-based stuck detection.
