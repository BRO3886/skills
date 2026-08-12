# Caching and Resilience Code Templates

Use these templates for hot-path caching, request coalescing, rate limiting, retry budgets, and last-known-good degradation. Keep cache policy and failure policy explicit at the caller boundary.

## Contents

- [Caching](#caching)
  - [Two-tier cache](#two-tier-cache-in-process-l1--distributed-l2)
  - [TTL jitter](#ttl-jitter--always)
  - [Request coalescing](#request-coalescing-collapse-duplicate-concurrent-loads)
  - [Pipelined batch operations](#pipelined-batch-getset)
- [Resilience](#resilience)
  - [Rate limiting](#rate-limiting)
  - [Retry budgets](#retry-split-total-vs-per-attempt-timeout)
  - [Last-known-good degradation](#graceful-degradation-serve-last-known-good)

---

## Caching

### Two-tier cache (in-process L1 + distributed L2)

Hot read paths where a network round-trip per read is too slow, but cross-instance consistency still matters. L1 absorbs repeated reads within one instance; L2 is the shared source of truth.

```go
func GetCached[T any](ctx context.Context, key string, l1 *localCache, l2 DistributedCache,
    load func(context.Context) (T, error)) (T, error) {

    if v, ok := getL1[T](l1, key); ok {
        return v, nil
    }
    var v T
    found, err := l2.Get(ctx, key, &v)
    if err != nil {
        log.WarnfWithContext(ctx, "L2 read %q: %v", key, err)
    }
    if found {
        if err := setL1(l1, key, v, l1TTL); err != nil {
            log.WarnfWithContext(ctx, "L1 write %q: %v", key, err)
        }
        return v, nil
    }
    v, err = load(ctx)
    if err != nil {
        return v, err
    }
    if err := l2.Set(ctx, key, v, l2TTL); err != nil {
        log.WarnfWithContext(ctx, "L2 write %q: %v", key, err)
    }
    if err := setL1(l1, key, v, l1TTL); err != nil {
        log.WarnfWithContext(ctx, "L1 write %q: %v", key, err)
    }
    return v, nil
}
```

Rules: L1 is instance-local — a write on one instance does not invalidate L1 elsewhere, so use it only where a few seconds of cross-instance staleness is acceptable. Keep L1 TTL well below L2 TTL or a targeted L2 invalidation still serves stale data from L1. In-process caches have hard per-value size limits — check the set error rather than failing silently. Measure serialization/compression cost; on very hot paths it can exceed the round-trip it saves.

### TTL jitter — always

Any time many keys are written together (batch refresh, prewarming, startup) they expire together without jitter, stampeding the origin. Jitter at write time, always.

```go
// TTL uniformly sampled from [base, base+jitter].
func ttlWithJitter(base, jitter time.Duration) time.Duration {
    return base + time.Duration(rand.Int63n(int64(jitter)+1))
}

cache.Set(ctx, key, val, ttlWithJitter(24*time.Hour, 4*time.Hour))
```

For data that expires at a fixed wall-clock moment, compute `expiry.Sub(time.Now())` then add jitter on top. The `+1` keeps a zero jitter window valid.

### Request coalescing (collapse duplicate concurrent loads)

When many goroutines miss the cache for the same key at once, they all hit the origin (cache stampede). `singleflight` ensures one in-flight load per key; the rest wait and share the result.

```go
import "golang.org/x/sync/singleflight"

var group singleflight.Group

func loadCoalesced(ctx context.Context, key string) (Value, error) {
    v, err, _ := group.Do(key, func() (any, error) {
        return loadFromOrigin(ctx, key)
    })
    if err != nil {
        return Value{}, err
    }
    return v.(Value), nil
}
```

`singleflight` is the idiomatic Go answer to the stampede problem — reach for it before hand-rolling a lock map.

### Pipelined batch get/set

Fetch or write many keys in one round-trip instead of one per key. Queue commands, flush once, resolve by position.

```go
func batchGet[T any](ctx context.Context, pipe Pipeliner, keys []string) ([]T, error) {
    cmds := make([]Cmd, len(keys))
    for i, k := range keys {
        cmds[i] = pipe.Get(ctx, k) // queued, not sent
    }
    if err := pipe.Exec(ctx); err != nil { // single flush
        return nil, err
    }
    out := make([]T, len(keys))
    var errs []error
    for i, c := range cmds {
        if err := c.Decode(&out[i]); err != nil {
            errs = append(errs, fmt.Errorf("decode %q: %w", keys[i], err))
        }
    }
    return out, errors.Join(errs...)
}
```

`Exec` returns one top-level error; individual command errors surface only when you decode each result — always check per-key, not just the top level. Hash-field set + TTL needs two flushes (set, then expire) since there's no atomic combined command.

---

## Resilience

### Rate limiting

In-process, single instance: a token bucket via `golang.org/x/time/rate`.

```go
limiter := rate.NewLimiter(rate.Limit(100), 200) // 100/s, burst 200
if !limiter.Allow() {
    return ErrRateLimited
}
```

Across replicas: a shared atomic check in the cache tier (sliding or fixed window). The non-negotiable rule is **fail open** — if the shared store is unavailable, allow the request:

```go
func (rl *sharedLimiter) Allow(ctx context.Context, key string) bool {
    allowed, err := rl.store.CheckAndIncrement(ctx, key, rl.limit, rl.window)
    if err != nil {
        return true // fail open — the limiter must never become a hard dependency
    }
    return allowed
}
```

A limiter that rejects traffic when its own backing store is down has inverted its risk. Choose the limit key granularity (per-user / per-IP / per-tenant) at call time to control blast radius. A sliding window avoids the burst spike a fixed window allows at its boundary.

### Retry: split total vs per-attempt timeout

A total-only timeout makes retries useless — a slow first attempt eats the whole budget. Bound each attempt and the whole operation separately, gate retries behind a flag, and never auto-retry non-idempotent calls.

```go
func callWithRetry(ctx context.Context, totalTimeout, perTry time.Duration, retry bool) (*Result, error) {
    ctx, cancel := context.WithTimeout(ctx, totalTimeout)
    defer cancel()
    return client.Call(ctx, withPerTryTimeout(perTry), withRetry(retry))
}
```

Put the retry toggle behind a runtime flag: under load, retries amplify pressure on an already-degraded dependency, and a flag lets you cut them instantly without a deploy. For background/side-effect paths, a bounded fixed-count retry (no backoff) is fine; for latency-sensitive primary paths, use backoff + jitter and check `ctx.Done()` between attempts.

### Graceful degradation (serve last-known-good)

When a critical dependency fails on a high-traffic read path, serve a pre-cached last-known-good response instead of an error. On each healthy response, snapshot it (guarded so you snapshot at most once per key per TTL); on failure, serve the snapshot.

```go
// write path (hot path stays non-blocking)
func snapshotIfStale(ctx context.Context, key string, data []byte) {
    exists, err := cache.Has(ctx, snapshotKey(key))
    if err != nil {
        log.ErrorfWithContext(ctx, "snapshot guard read: %v", err)
        return
    }
    if exists {
        return // idempotency guard — prevents a snapshot storm under load
    }
    if err := cache.Set(ctx, snapshotKey(key), true, ttlWithJitter(base, jitter)); err != nil {
        log.ErrorfWithContext(ctx, "snapshot guard write: %v", err)
        return
    }
    bg := detach(ctx) // copy values, drop the request deadline
    go func() {
        defer func() {
            if r := recover(); r != nil {
                log.Errorf("snapshot panic: %v\n%s", r, debug.Stack())
                _ = cache.Delete(bg, snapshotKey(key))
            }
        }()
        if err := store.Put(bg, key, data); err != nil {
            _ = cache.Delete(bg, snapshotKey(key)) // roll back the guard so the next request retries
            log.Errorf("snapshot write: %v", err)
        }
    }()
}

// read path
func getOrDegrade(ctx context.Context, key string) (*Result, error) {
    if shouldDegrade(ctx) { // kill switch / health signal / sampling
        return fetchSnapshot(ctx, key)
    }
    return fetchLive(ctx, key)
}
```

Key lessons: the snapshot write must run on a **detached context** (values copied, deadline dropped) so it survives after the request returns. The idempotency guard with jittered TTL prevents every request under load from spawning a write. Propagate the "degrade" decision as a typed field on a request-scoped struct, not buried in `context.Value`, so it's visible and loggable. Roll back the guard if the write fails.

---
