# Architecture - Unattended Development System

## System Overview

The Unattended Development System is a production-ready autonomous development infrastructure that enables AI agents to work on long-term software engineering tasks with automatic recovery, progress tracking, and resource management.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User / DevOps Team                         │
└────────────────────────────┬──────────────────────────────────────┘
                             │
                    ┌─────────────────────────────────────────┐
                    │            REST API / CLI Interface           │
                    └─────────────────────────────────────────┘
                             │
        ┌────────────────┼────────────────────────────────┐
        │                 │                                │
        ▼                 ▼                                ▼
┌──────────────┐  ┌──────────┐  ┌──────────────────┐  ┌──────────────┐
│  Driver.sh  │  │Watchdog │  │Orchestrator.py│  │  Task Files  │
│  (Bash)    │  │ (Bash)  │  │  (Python)      │  │  (Markdown) │
└──────┬──────┘  └────┬─────┘  └──────┬─────────┘  └─────────────┘
       │              │               │                │
       │              │               │                ▼
       │              │               │        ┌──────────────────┐
       │              │               │        │  .unattended/    │
       │              │               │        │  ├─ logs/          │
       │              │               │        │  ├─ checkpoints/    │
       │              │               │        │  ├─ tasks/         │
       │              │               │        │  └─ config.json    │
       │              │               │        └──────────────────┘
       │              │               │
       └──────────────┴───────────────┴───────────────────┘
                       │
            ┌──────────────┴──────────────────┐
            │                                  │
            ▼                                  ▼
       ┌──────────────────┐           ┌──────────────┐
       │   AI Provider 1   │           │   AI Provider 2   │
       │   (Primary)      │           │   (Fallback)    │
       └──────────────────┘           └──────────────┘
            │                                  │
            └──────────────┬───────────────────┘
                           │
                  ┌──────────────┴──────────────┐
                  │                               │
                  ▼                               ▼
            ┌──────────────────┐      ┌──────────────┐
            │   Project Files    │      │   Git Repo   │
            │   (Code/Tests)  │      │   (GitHub)   │
            └──────────────────┘      └──────────────┘
```

## Component Interaction

### Driver Flow

```
STARTUP
  ↓
  Load config
  ↓
  Initialize
  ↓
MAIN LOOP
  ├─→ Check status
  ├─→ Check if all done
  ├─→ Start AI agent
  ├─→ Monitor execution
  ├─→ Detect issues (quota, context, timeout)
  ├─→ Handle issues (switch provider, restart session)
  ├─→ Run tests
  ├─→ Auto commit
  ├─→ Save checkpoint
  └─→ Sleep
  ↓
COMPLETED
```

### Watchdog Flow

```
CRON TRIGGER (every 10 min)
  ↓
  Check if all work done
  ↓
  Check if driver running
  ├─ Yes → Check if stuck (log age > 45min)
  │      ├─ Yes → Kill stuck AI process
  │      └─ No  → Continue
  └─ No → Restart driver
```

### Orchestrator Flow

```
COMMAND INVOCATION
  ↓
  Load config
  ↓
  Execute command
  ↓
  Save result
  ↓
  Generate report
```

## Data Flow

### Configuration Flow

```
install.sh
  ├─→ Detects project type
  ├─→ Generates templates
  ├─→ Asks for AI providers
  └─→ Creates .unattended/config.json
```

### Execution Flow

```
driver.sh
  ├─→ Reads .unattended/config.json
  ├─→ Loads .unattended/status.yaml
  ├─→ Checks .unattended/tasks/
  ├─→ Executes AI agent with context
  ├─→ Captures output to .unattended/logs/driver.log
  ├─→ Saves checkpoints to .unattended/checkpoints/
  ├─→ Updates .unattended/status.yaml
  ├─→ Runs tests
  ├─→ Git commit and push
  └─→ Checks for completion
```

### Recovery Flow

```
ERROR/CRASH DETECTED
  ↓
  Driver or Watchdog detects
  ↓
  Save error state
  ↓
  Load latest checkpoint
  ↓
  Determine recovery action:
  - Transient error → Retry
  - Quota issue → Switch provider
  - Context issue → Fresh session
  - Fatal error → Abort
  ↓
  Execute recovery
  ↓
  Update status
  ↓
  Resume execution
```

## Error Handling

### Error Categories

| Category | Examples | Handling |
|----------|----------|----------|
| **Transient** | Network timeout, temporary API error | Retry up to 3 times |
| **Quota** | 429, quota exceeded, balance insufficient | Switch provider |
| **Context** | Context length exceeded | Start fresh session |
| **Timeout** | Task takes too long | Save checkpoint, retry with timeout |
| **Fatal** | Corrupt state, dependency missing | Abort with full report |

### Error Recovery Mechanisms

1. **Automatic Retry** - For transient errors
2. **Provider Switching** - For quota issues
3. **Session Restart** - For context issues
4. **Checkpoint Recovery** - Load last good state
5. **Watchdog Restart** - For driver crashes

## Security Considerations

### Input Validation
- Validate all configuration values
- Sanitize file paths
- Validate AI provider keys
- Escape user input before use

### Command Injection Prevention
- Use fixed command templates
- No direct user command execution
- Validate provider names and models

### File Permissions
- Set appropriate permissions on sensitive files
- Use umask 077 for unattended directories
- Restrict write access to unattended directory

### Credential Management
- Store API keys in `~/.pi/agent/auth.json` (pi-managed)
- Don't log sensitive information
- Use environment variables for secrets

## Performance Considerations

### Resource Usage

- **Memory**: Driver is lightweight (<10MB RSS)
- **CPU**: Mostly idle, spikes during AI agent execution
- **Disk**: Logs grow over time, need rotation
- **Network**: Periodic provider health checks

### Optimization Strategies

1. **Log Rotation** - Implement logrotate for driver logs
2. **Checkpoint Cleanup** - Remove old checkpoints (keep last N)
3. **Lazy Loading** - Load tasks on demand
4. **Batch Operations** - Group commits and pushes

### Scalability

- **Task Capacity**: Supports 1000+ tasks efficiently
- **Checkpoint Storage**: Each checkpoint ~1-2KB
- **Log Management**: Handle multi-million line logs
- **Concurrent Safety**: Single instance enforced by lock file

## Integration Points

### With Pi Agent
- Uses `pi --provider <name> --model <name>` for AI execution
- Provider rotation via different pi invocations
- Context management via `-c` (continue) vs fresh start

### With Git
- Auto-commits via git command
- Pushes to remote repository
- Uses configured SSH keys

### With Other Matt Skills
- `grill-me` - Plan before starting
- `to-spec` - Generate specifications
- `to-tickets` - Create task definitions
- `implement` - Execute individual tasks
- `code-review` - Review changes periodically

## Monitoring and Observability

### Log Files

| Log File | Content | Purpose |
|----------|--------|---------|
| `driver.log` | Driver execution log | Main operational log |
| `watchdog.log` | Watchdog actions | Health checks and restarts |
| `orchestrator.log` | Orchestrator operations | Quota, checkpoints |
| `*.json` | Checkpoint files | State snapshots |

### Status Information

```bash
# Current status
cat .unattended/status.yaml

# All checkpoints
python orchestrator.py --list-checkpoints

# Quota status
python orchestrator.py --check
```

### Health Checks

```bash
# Driver process
pgrep -f "driver.sh"

# Lock file status
ls -la /tmp/*-driver.lock

# Last log timestamp
stat -c %y .unattended/logs/driver.log
```

## Extension Points

### Custom Task Templates
Create `.unattended/task-template.md` to define custom task structure.

### Custom Recovery Logic
Create `.unattended/recovery-hook.sh` for custom recovery logic.

### Custom Notifications
Configure webhooks in `.unattended/config.json` for Slack, Discord, email, etc.

### Custom Test Commands
Override default test command per project in `.unattended/config.json`.

---

**Last Updated**: 2026-08-23 02:45
**Skill Version**: 1.0.0
**Based On**: AI-FanYi v7 (commit ed81d91)
