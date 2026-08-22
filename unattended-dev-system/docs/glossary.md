# Glossary - Unattended Development System

## Core Components

### Driver
The main autonomous execution loop that repeatedly invokes the AI agent to complete development tasks. The driver orchestrates task execution, handles errors, and manages provider rotation.

**File**: `driver.sh`

### Watchdog
A monitoring process that runs periodically (typically every 10 minutes via cron) to ensure the driver is healthy and restarts it if it fails or gets stuck.

**File**: `watchdog.sh`

### Orchestrator
A Python module that manages quota monitoring, progress saving, and recovery instruction generation. It handles cross-cutting concerns like state persistence and notification.

**File**: `orchestrator.py`

### Task
A unit of work that needs to be completed. Tasks can represent features, bug fixes, refactoring, documentation, or any development work.

**Directory**: `.unattended/tasks/{todo,doing,done}/`

### Checkpoint
A snapshot of the system state at a particular point in time, used for recovery after failures. Includes timestamp, phase, message, next action, provider, and context.

**File**: `.unattended/checkpoints/checkpoint_YYYYMMDD_HHMMSS.json`

## System Behavior

### Provider Rotation
Automatic switching between AI providers when the current provider fails (quota exhausted, health check failure, etc.).

### Zero-Output Fuse
A safety mechanism that terminates the current AI agent round if no output is produced for a configured duration (default: 900 seconds). Prevents indefinite hanging.

### Context Overflow
When the AI agent's context window is exceeded, the system starts a fresh session to continue.

### Quota Limit
The API usage limit imposed by an AI provider. When reached, the system either rotates to another provider or waits for reset.

### Stuck Detection
The watchdog's mechanism to detect when the driver is not making progress (log file not updated for 45 minutes).

## Technical Terms

### Round
One iteration of the driver's main loop, including: check status → start AI agent → wait for completion → handle result → save progress.

### Session
One continuous interaction with an AI agent, including the conversation history and context. A session can span multiple rounds.

### Fresh Session
A new AI agent session started with empty or minimal context, used when the previous session has grown too large or corrupted.

###熔断
A safety mechanism that stops the current operation when a condition is met, preventing infinite loops or hanging.

### Singleton
A pattern ensuring only one instance of the driver can run at a time, implemented using file locking (flock).

## Configuration

### Provider List
The ordered list of AI providers configured for the system, e.g., `["zai-coding-cn/glX", "deepseek/deepseek-v4-flash"]`.

### Test Command
The command used to validate code changes, e.g., `pytest tests/ -q` for Python, `npm test` for JavaScript.

### Commit Prefix
The prefix used for automatic git commits, e.g., `chore(driver):`.

### Stuck Threshold
The time (in minutes) of log inactivity before the watchdog considers the driver stuck, e.g., 45 minutes.

## State Machine States

### STARTUP
Initialization phase: load config, validate environment, check prerequisites.

### RUNNING
Normal operation: executing tasks, monitoring, handling errors.

### COMPLETED
All tasks finished and tests passing.

### ERROR
Recoverable error occurred; attempting recovery.

### FATAL
Unrecoverable error; system stopping.

### RECOVERING
Attempting to recover from error; may retry, switch strategies, or abort.

## Acronyms

| Acronym | Full Name |
|---------|-----------|
| ADR | Architecture Decision Record |
| API | Application Programming Interface |
| CLI | Command Line Interface |
| JSON | JavaScript Object Notation |
| YAML | YAML Ain't Markup Language |
| SSH | Secure Shell |
| VCS | Version Control System (Git, etc.) |

## AI & Development Terms

### Sub-agent
An AI agent spawned as a child of the main agent to perform a specific task, e.g., the Standards and Spec sub-agents in code-review.

### Context Window
The amount of conversation history an AI model can "remember". When exceeded, the model cannot continue the conversation.

### Git Commit
A snapshot of the codebase at a point in time, saved to version control.

### Branch
A parallel version of the codebase for feature development.

### Merge-base
The most recent common ancestor commit between two branches.

### Diff
The difference between two versions of code, showing what changed.

---

**Last Updated**: 2026-08-23 02:30
**Skill Version**: 1.0.0
