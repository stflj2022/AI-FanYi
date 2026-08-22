# ADR 003: Provider Rotation Mechanism

## Status
**Accepted**

## Context
The system supports multiple AI providers to ensure continuous operation. When a provider fails (quota exhausted, health check fails, etc.), the system must automatically switch to an available fallback provider.

## Decision

Provider rotation uses a **health-aware priority strategy**:

### Provider Health Check
```bash
provider_alive() {
    local provider="$1"
    local api_key="$2"
    
    # HTTP health check
    local code
    code=$(curl -sS -m 10 -o /dev/null -w "%{http_code}" \
        "https://api.$provider.com/chat/completions" \
        -H "Authorization: Bearer $api_key" \
        -d '{"model":"test","messages":[{"role":"user","content":"ping"}],"max_tokens":1}' 2>/dev/null)
    
    [ "$code" = "200" ]
}
```

### Rotation Trigger Conditions
1. **Quota Exhausted**: Response code 429 or error message about quota/limits
2. **Health Check Failed**: HTTP code not 200
3. **Zero Output**: No output for configured timeout
4. **Context Overflow**: Response indicates context length exceeded

### Rotation Algorithm
```bash
if trigger_detected; then
    FAILS=$((FAILS + 1))
    
    if provider_alive CURRENT_PROVIDER; then
        # Provider is alive but had issue, keep it
        # Just restart fresh session
        FRESH_NEXT=true
    else
        # Provider is dead, rotate to next
        CURRENT_PROVIDER=$(( (CURRENT_PROVIDER + 1) % PROVIDER_COUNT)
        FRESH_NEXT=true
    fi
    
    # Check if all providers failed
    if [ $FAILS -ge $PROVIDER_COUNT ]; then
        # All down, wait and retry
        sleep 900
        FAILS=0
    fi
fi
```

### Provider Priority
- **Primary**: First in list, used preferentially
- **Fallback**: Used when primary unavailable
- **Last Resort**: Used when all others fail
- **Cycle**: Rotate through all, then restart from primary

## Rationale

Health-aware rotation provides:
- **Efficient resource usage** - Don't waste quota on broken providers
- **Smart fallback** - Prioritize working providers
- **Self-healing** - Temporary failures don't trigger permanent rotation
- **Recovery mechanism** - Wait for all providers to recover

## Consequences

### Positive
- Maximizes uptime with multiple providers
- Minimizes wasted API calls to broken providers
- Automatic recovery without manual intervention
- Configurable provider list and priority

### Negative
- Multiple provider subscriptions increase cost
- Adds complexity to configuration
- Requires health check for each provider type

## Alternatives Considered

1. **Round-robin regardless of health** - Wastes quota on broken providers
2. **Manual provider selection** - Defeats purpose of automation
3. **Single provider with wait-for-reset** - Longer downtime

## Implementation Notes

### Provider Configuration
```json
{
  "driver": {
    "providers": [
      "zai-coding-cn/glm-4.7",
      "deepseek/deepseek-v4-flash",
      "anthropic/claude-sonnet-4-5"
    ],
    "health_check_interval": 300,
    "retry_after_all_failed": 900
  }
}
```

### Health Check Implementation
- **Zai**: Check `https://api.z.ai/api/coding/paas/v4/chat/completions`
- **DeepSeek**: Check `https://api.deepseek.com/chat/completions`
- **Anthropic**: Check `https://api.anthropic.com/v1/messages`

### Quota Detection Patterns
```bash
# HTTP 429
grep -q "429" round_output

# Error messages
grep -qiE "quota|额度|余额不足|rate limit" round_output

# Common quota errors
grep -qiE "insufficient|exceeded|balance" round_output
```

## Related Decisions
- ADR 001: Driver Loop Architecture (provider rotation in main loop)
- ADR 004: State Management and Recovery (rotation as state transition)
