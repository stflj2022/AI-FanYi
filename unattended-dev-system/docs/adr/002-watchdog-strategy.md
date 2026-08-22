# ADR 002: Watchdog Strategy

## Status
**Accepted**

## Context
The watchdog (`watchdog.sh`) monitors the driver process and ensures system reliability. It needs to detect various failure modes and trigger appropriate recovery actions without interfering with normal operation.

## Decision

The watchdog implements a **three-tier detection and recovery strategy**:

### Tier 1: All Work Done Check
```bash
if all_work_done; then
    exit 0  # No intervention needed
fi
```
- Check if `driver.log` contains "ALL TASKS COMPLETED"
- If true, permanent success, stop all monitoring

### Tier 2: Process Health Check
```bash
if driver_running; then
    if driver_stuck; then
        kill_stuck_ai_process()
        # Driver should recover on its own
    fi
else
    restart_driver()
fi
```
- Check if driver process is running
- If running, check if stuck (log not updated for 45+ minutes)
- If stuck, kill only the AI subprocess, let driver recover
- If not running, restart entire driver

### Tier 3: Stuck Detection Threshold

**Current**: 45 minutes (2700 seconds)
**Rationale**: 
- Long enough to detect real hangs
- Short enough to catch issues within a working session
- Balances responsiveness vs false positives

**Detection Method**:
```bash
AGE=$(( $(date +%s) - $(stat -c %Y "$LOG" ))
if [ $AGE -gt 2700 ]; then
    # Considered stuck
fi
```

## Rationale

Three-tier strategy provides:
1. **Early exit** - Don't waste resources on completed work
2. **Minimal intervention** - Only interfere when necessary
3. **Smart recovery** - Kill only what's stuck, preserve what works
4. **Preventive** - Threshold set to catch issues before they cause major delays

## Consequences

### Positive
- Watchdog is non-intrusive
- False positives are rare (45min threshold)
- Recovery is automatic and requires no manual intervention
- Completed work is preserved

### Negative
- If driver hangs without updating logs, watchdog may not detect it
- Multiple concurrent instances (blocked by lock file)

## Alternatives Considered

1. **Every 10min restart regardless** - Too aggressive, loses progress
2. **Heartbeat mechanism** - Would require driver modifications
3. **Separate watchdog service** - Overkill for current needs

## Implementation Notes

### Watchdog Cron Schedule
```bash
*/10 * * * * /path/to/watchdog.sh
```

### Stuck Process Detection
```bash
# Pattern matching for AI subprocess
PIPID=$(pgrep -f "^timeout 7200 pi" | head -1)
```

### Log Age Calculation
```bash
# Cross-platform compatible
LOG_AGE=$(($(date +%s) - $(stat -c %Y "$DRIVER_LOG")))
```

## Related Decisions
- ADR 001: Driver Loop Architecture (watchdog is part of external supervision)
- ADR 003: Provider Rotation Mechanism (watchdog monitors health)
