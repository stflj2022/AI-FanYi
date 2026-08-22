# Code Review Findings - Unattended Dev System Skill

**Review Date**: 2026-08-23 02:50
**Review Scope**: All skill files in `~/.pi/agent/skills/unattended-dev-system/`

---

## Standards Axis

### 🔴 High Priority

#### S-001: Missing Shell Error Handling in driver.sh.template
**File**: `templates/driver.sh.template`
**Lines**:多处
**Issue**: Script uses `set -u` which causes exit on undefined variables, but some template variables may not be defined during installation.

**Severity**: High
**Fix**: Remove `set -u` and add explicit validation for required variables.

```bash
# Current (problematic):
set -u

# Better (safe):
set -euo pipefail
# Check required variables before use
: "${REPO:?REPO not set}"
: "${LOG_DIR:?LOG_DIR not set}"
```

#### S-002: Potential Command Injection in AI Command
**File**: `templates/diple.sh.template`
**Line**: ~150
**Issue**: `{{AI_COMMAND}}` is used directly in `timeout` command without validation, could allow injection if user provides malicious input.

**Severity**: High
**Fix**: Validate and sanitize `{{AI_COMMAND}}` before use.

```bash
# Add validation function
validate_ai_command() {
    local cmd="$1"
    # Check for dangerous patterns
    if echo "$cmd" | grep -qE '[;&|>|`|\$\(|\`|\\|/dev/'; then
        log_error "Invalid characters in AI command"
        return 1
    fi
    # Validate command format
    if ! [[ "$cmd" =~ ^[a-z0-9_\-\s]+$ ]]; then
        log_error "AI command contains invalid characters"
        return 1
    fi
}
```

#### S-003: Path Traversal Risk
**File**: `templates/driver.sh.template`
**Lines**: Multiple
**Issue**: User-provided paths (REPO) are not validated, could allow directory traversal.

**Severity**: High
**Fix**: Resolve and validate paths before use.

```bash
# Add path validation
validate_path() {
    local path="$1"
    # Resolve absolute path
    path=$(realpath "$path" 2>/dev/null) || return 1
    # Check path is within allowed directories
    case "$path" in
        "$HOME"|"$HOME/"*) ;;  # Allow home directory
        *) return 1 ;;
    esac
}
```

### 🟡 Medium Priority

#### S-004: Hardcoded Timeouts
**File**: `templates/driver.sh.template`
**Lines**: 20-23
**Issue**: Timeouts are hardcoded and not configurable per project type.

**Severity**: Medium
**Fix**: Add timeout configuration to config.json, read from config in driver.

```bash
# Add to config.json
"driver": {
  "timeout": 7200,
  "test_timeout": 600
}
```

#### S-005: Incomplete Error Recovery
**File**: `templates/driver.sh.template`
**Lines**: 180-220
**Issue**: Error handling exists but doesn't categorize errors properly for targeted recovery.

**Severity**: Medium
**Fix**: Implement error categorization function:

```bash
categorize_error() {
    local exit_code="$1"
    local error_type
    
    case $exit_code in
        124) error_type="timeout" ;;
        1) error_type="generic" ;;
        2) error_type="usage" ;;
        126) error_type="command_not_found" ;;
        127) error_type="command_not_found" ;;
        *) error_type="unknown" ;;
    esac
    
    echo "$error_type"
}
```

#### S-006: Missing Platform Compatibility
**File**: `templates/watchdog.sh.template`
**Lines**: Multiple
**Issue**: Uses Linux-specific commands (`stat -c %Y`, `pgrep -f`) without fallback for macOS/Windows.

**Severity**: Medium
**Fix**: Use POSIX-compliant alternatives or detect platform.

```bash
# Platform detection
detect_platform() {
    case "$(uname -s)" in
        Linux*)  PLATFORM="linux" ;;
        Darwin*) PLATFORM="macos" ;;
        MINGW*|MSYS*) PLATFORM="windows" ;;
        *) PLATFORM="generic" ;;
    esac
}

# Platform-specific log age
get_file_age() {
    case "$PLATFORM" in
        linux|macos)
            stat -c %Y "$1" 2>/dev/null || echo "0"
            ;;
        windows)
            powershell -Command "(Get-Item \"$1\").LastWriteTime" 2>/dev/null || echo "0"
            ;;
        *)
            echo "0" ;;
    esac
}
```

#### S-007: No Log Rotation
**Files**: `templates/driver.sh.template`
**Issue**: Log files grow indefinitely without rotation.

**Severity**: Medium
**Fix**: Implement log rotation.

```bash
# Add to driver.sh
rotate_logs() {
    local max_size=10485760  # 100MB
    local current_size
    current_size=$(stat -c %s "$LOG" 2>/dev/null || echo "0")
    
    if [ "$current_size" -gt "$max_size" ]; then
        local backup
        backup="$LOG.$(date +%Y%m%d_%H%M%S)"
        mv "$LOG" "$backup"
        touch "$LOG"
        log "Rotated log to $backup"
    fi
}
```

### 🟢 Low Priority

#### S-008: Limited Testing Support
**File**: `templates/driver.sh.template`
**Lines**: 50-60
**Issue**: Test command is hardcoded, no support for multiple test suites.

**Severity**: Low
**Fix**: Allow array of test commands.

```json
{
  "testing": {
    "commands": [
      {"name": "unit", "command": "pytest tests/ -q"},
      {"name": "integration", "command": "pytest tests/integration/ -q"}
    ]
  }
}
```

#### S-009: No Dry-Run Mode
**File**: `install.sh`, `templates/driver.sh.template`
**Issue**: No way to test without actually executing.

**Severity**: Low
**Fix**: Add `--dry-run` flag.

```bash
# Add to driver.sh
DRY_RUN=false

if [ "$DRY_RUN" = "true" ]; then
    log "DRY RUN: Would execute AI agent"
    # Simulate without actual execution
    exit 0
fi
```

#### S-010: Limited Notification Options
**File**: `templates/config.json.template`
**Lines**: 30-35
**Issue**: Only supports single webhook, no multiple channels.

**Severity**: Low
**Fix**: Support multiple notification channels.

```json
{
  "notification": {
    "enabled": true,
    "channels": [
      {
        "type": "slack",
        "webhook": "https://hooks.slack.com/...",
        "on_events": ["task_complete", "error"]
      },
      {
        "type": "discord",
        "webhook": "https://discord.com/api/webhooks/...",
        "on_events": ["error", "quota_limit"]
      },
      {
        "type": "email",
        "to": "dev-team@example.com",
        "on_events": ["task_complete", "ALL_DONE"]
      }
    ]
  }
}
```

---

## Spec Axis

### 🔴 High Priority

#### SP-001: Missing Auto-Detection for Some Frameworks
**Requirement**: Skill claims to auto-detect all major languages and frameworks, but some are missing.

**Current**: Supports Python, JavaScript/TypeScript, Go, Rust, Java, generic
**Missing**: Ruby, PHP, C/C++, Swift, Kotlin, .NET

**Impact**: Users of these frameworks need manual configuration
**Status**: Incomplete
**Recommendation**: Add detection patterns for missing frameworks

#### SP-002: Install Script Doesn't Validate Environment
**Requirement**: Install script should verify prerequisites are available before installing.

**Current**: Assumes bash, curl, python3, etc. are available
**Missing**: Pre-flight checks for git, SSH, AI provider API keys

**Impact**: Installation may fail with cryptic error messages
**Status**: Incomplete
**Recommendation**: Add comprehensive environment validation

#### SP-003: No Task Dependency System
**Requirement**: Skill mentions task dependencies but doesn't implement them.

**Current**: Tasks just marked as todo/doing/done, no dependency resolution
**Missing**: Dependency graph, blocking/unblocking, circular dependency detection

**Impact**: Tasks may be executed in wrong order
**Status**: Not implemented
**Recommendation**: Implement dependency resolution

### 🟡 Medium Priority

#### SP-004: No Rollback Mechanism
**Requirement**: Ability to undo changes if a task introduces bugs.

**Current**: All commits are pushed immediately, no rollback capability
**Missing**: Commit tagging, manual/automatic rollback commands

**Impact**: Failed changes require manual git operations
**Status**: Not implemented
**Recommendation**: Add rollback commands and commit tagging

#### SP-005: Limited Platform Support
**Requirement**: Skill works on Linux, but macOS/Windows support is limited.

**Current**: Uses Linux-specific commands (flock, stat -c, pgrep)
**Status**: Partially supported
**Recommendation**: Full platform support via abstraction layer

#### SP-006: No Performance Monitoring
**Requirement**: Track performance metrics: task completion time, API usage, failure rates.

**Current**: Basic logging only, no metrics collection
**Missing**: Metrics collection and reporting

**Impact**: Can't optimize or diagnose performance issues
**Status**: Not implemented
**Recommendation**: Add metrics collection

### 🟢 Low Priority

#### SP-007: No Task Scheduling Priority
**Requirement**: Tasks can be prioritized (high/medium/low) and execution order adjusted.

**Current**: Tasks executed in order they are found
**Missing**: Priority system

**Impact**: Critical tasks may not be done first
**Status**: Not implemented
**Recommendation**: Add task priority field and sorting

#### SP-008: No Interactive Mode
**Requirement**: Ability to pause/resume, ask questions, or get human input.

**Current**: Fully autonomous, no human interaction
**Missing**: Interactive breakpoints, confirmation prompts

**Impact**: Cannot clarify ambiguities during execution
**Status**: Not implemented
**Recommendation**: Add interactive mode option

#### SP-009: Limited Documentation
**Requirement**: Comprehensive documentation for all features.

**Current**: Basic docs exist, but some advanced features are undocumented.

**Impact**: Advanced users may not discover all features
**Status**: Partial
**Recommendation: Complete missing documentation

---

## Summary

### Total Findings
- **Standards**: 10 findings (3 high, 4 medium, 3 low)
- **Spec**: 9 findings (3 high, 3 medium, 3 low)

### Worst Issues

**Standards**: 
- **S-001**: Missing shell error handling (High)
- **S-002**: Command injection risk (High)

**Spec**:
- **SP-001**: Missing auto-detection for some frameworks (High)
- **SP-002**: Install script doesn't validate environment (High)

### Priority Recommendations

1. **Fix security issues first** (S-001, S-002, S-003)
2. **Add missing auto-detection** (SP-001)
3. **Implement environment validation** (SP-002)
4. **Add error categorization** (S-005)
5. **Add platform support** (S-006)
6. **Implement rollback** (SP-004)
7. **Add metrics collection** (SP-006)

---

**Next Steps**:
1. Review and approve findings
2. Create issue tickets for each finding
3. Prioritize and implement fixes
4. Update documentation
5. Add tests for all fixes

**Review Date**: 2026-08-23
**Reviewer**: Code Review Skill (Standards + Spec)
**Skill Version**: 1.0.0
