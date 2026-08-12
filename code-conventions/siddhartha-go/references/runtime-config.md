# Runtime Configuration and Feature Flag Templates

Use these templates when a value must change without a deploy. Read runtime values at the decision boundary, guard dangerous zero values, and keep rollout gates deterministic.

## Contents

- [1. Per-call kill switch](#1-per-call-kill-switch-with-a-sentinel-error)
- [2. Runtime number with a safe default](#2-runtime-tunable-number-with-an-inline-safe-default)
- [3. Two-level feature gate](#3-two-level-feature-gate-master-toggle-then-sub-params)
- [4. Tiered gradual rollout](#4-tiered-gradual-rollout)

---

The runtime accessor reads a key from a config/flag store at call time (ctx-scoped), so changes take effect on the next request with no redeploy. The whole value is that flags are tunable live; the whole risk is a missing key returning a zero value.

## 1. Per-call kill switch with a sentinel error

```go
var errKilled = errors.New("killed")

func (c *client) call(ctx context.Context) (*Result, error) {
    if rconfig.GetBool(ctx, "thing_service.kill_switch") {
        return nil, errKilled // checked at the top — short-circuits before any allocation
    }
    return c.downstream(ctx)
}
```

Use one consistent naming convention for every switch (`<subsystem>.kill_switch`) so on-call can find them. Return a *sentinel* (not a generic error) so callers and metrics distinguish a deliberate kill from a real failure. A subsystem-wide switch checked in several functions gives you atomic blast-radius control.

## 2. Runtime-tunable number with an inline safe default

`GetInt` returns 0 for a missing key — and 0 is dangerous for a batch size (infinite loop) or a TTL (zero-second cache). Guard immediately, inline, with the conservative value.

```go
batch := rconfig.GetInt(ctx, "ranking.batch_size")
if batch <= 0 {
    batch = 50 // safe default, co-located with the read
}
```

The safe default is the conservative choice (smaller batch, longer TTL). Keep the fallback at the read site, not in a distant init function, so the reasoning is where the value is used.

## 3. Two-level feature gate (master toggle, then sub-params)

Gate sub-parameter reads behind the master toggle, so defaults from an absent sub-param can't silently take effect when the feature is off.

```go
func featureEnabled(ctx context.Context, name, sub string) bool {
    if !rconfig.GetBool(ctx, "feature."+name+".enabled") {
        return false // master gate first
    }
    if sub == "" {
        return true
    }
    return rconfig.GetBool(ctx, "feature."+name+"."+sub)
}
```

Keep naming rigid: `feature.<name>.enabled` for the master, `feature.<name>.<param>` for sub-params. Never gate correctness-critical logic on a flag — flags are for rollout and kill switches, not for choosing a right vs wrong answer.

## 4. Tiered gradual rollout

Layer the gates in a fixed order so an internal override, a geographic scope, a named allowlist, and a percentage sample all compose under one master toggle.

```go
func enabledFor(ctx context.Context, region, userID int, internal bool) bool {
    if !rconfig.GetBool(ctx, "feature.x.enabled") {
        return false // master gate — always first, stops config noise from activating early
    }
    if internal && rconfig.GetBool(ctx, "feature.x.force_internal") {
        return true // test/benchmark traffic against prod without touching real users
    }
    if inIntSlice(region, rconfig.GetIntSlice(ctx, "feature.x.regions")) {
        return true
    }
    if inIntSlice(userID, rconfig.GetIntSlice(ctx, "feature.x.user_allowlist")) {
        return true
    }
    return hashSample(ctx, "feature.x.sample_bps") // e.g. (md5(session) % 10000) < bps
}
```

Always check the master `enabled` first. If your config store is remote (not in-process), cache slice reads on the hot path and accept a short propagation delay. Keep the internal/test override tier in every non-trivial gate — it's what lets you reliability-test against production safely.
