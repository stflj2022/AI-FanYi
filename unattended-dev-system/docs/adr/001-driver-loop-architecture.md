# ADR 001: Driver Loop Architecture

## Status
**Accepted**

## Context
The unattended-dev-system skill's core functionality is the driver loop (`driver.sh`), which autonomously executes development tasks with AI agent assistance. The design needs to support multiple use cases, ensure robustness, and allow for easy customization.

## Decision
The driver loop will follow a **state machine pattern** with the following states:

```
STARTUP → RUNNING → COMPLETED | ERROR | RECOVERING
        ↓           ↑            ↓          ↑
      RETRY ← ← FAIL        ← TIMEOUT    ← FATAL
```

### State Definitions

**STARTUP**
- Initialize all components
- Load configuration
- Check prerequisites
- Validate environment

**RUNNING**
- Execute AI agent task
- Monitor for timeouts and output
- Detect quota/context issues
- Handle provider switching

**COMPLETED**
- All tasks finished
- All tests passing
- Final cleanup

**ERROR**
- Recoverable error occurred
- Log and attempt recovery
- May retry or switch strategies

**FATAL**
- Unrecoverable error
- Stop and notify

**RECOVERING**
- Attempt to recover from error
- May involve cleanup, restart, or fallback
- If recovery fails, move to ERROR or FATAL

### Key Components

1. **Task Queue Manager** - Manages task dependencies and execution order
2. **Provider Manager** - Handles AI provider health and rotation
3. **Health Monitor** - Tracks driver, watchdog, and orchestrator health
4. **Progress Tracker** - Saves checkpoints and status
5. **Error Handler** - Categorizes and responds to errors
6. **Git Integrator** - Handles commits and pushes

## Rationale

A state machine provides:
- **Clear separation of concerns** - Each state has well-defined entry/exit conditions
- **Easier testing** - Each state can be tested independently
- **Better error handling** - State transitions are explicit
- **Observability** - State is logged at each transition
- **Extensibility** - New states can be added without affecting existing logic

## Consequences

- Positive:
  - More maintainable and testable code
  - Better error recovery paths
  - Clearer debugging (can trace state transitions)
  - Easier to add new features

- Negative:
  - Slightly more complex than simple loop
  - Requires careful state transition testing

## Alternatives Considered

1. **Simple Loop** (current) - Simple but harder to reason about
2. **Event-Driven** - More flexible but overkill for this use case
3. **Actor Model** - Too complex for the current needs

## Implementation Notes

- State transitions logged with timestamps
- Each state has entry validation and exit cleanup
- State persisted in `$STATUS_FILE` for recovery
- `driver.sh --state STATUS_NAME` command for state inspection
- `driver.sh --force-state STATUS_NAME` for manual state transitions

## Related Decisions
- ADR 002: Watchdog Strategy
- ADR 003: Provider Rotation Mechanism
- ADR 004: State Management and Recovery
