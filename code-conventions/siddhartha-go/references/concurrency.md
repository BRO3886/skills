# Concurrency, Caching & Resilience — Code Templates

Full templates for the patterns summarized in `SKILL.md`'s Concurrency section. These are extracted from production Go backend services that fan out to many dependencies on the hot path under real traffic. Read this when implementing a worker pool, a parallel fan-out, per-call timeouts, a cache layer, rate limiting, or graceful degradation.

Throughout: `recoverPanic(ctx)` is your panic-recovery helper — it recovers, logs with context, and swallows. Every goroutine gets one as its first deferred call.

---

## 1. Bounded fan-out via a semaphore channel

Process N items concurrently while capping simultaneous goroutines at K (K ≪ N). The classic shape for batching expensive outbound calls across a large input set without a pool library.

```go
func processAll(ctx context.Context, items []Item, maxWorkers int) map[int]Result {
    var wg sync.WaitGroup
    results := make(chan Result, len(items)) // sized to senders — never parks
    guard := make(chan struct{}, maxWorkers) // the semaphore

    for i := range items {
        guard <- struct{}{} // acquire a slot (blocks at the limit)
        wg.Add(1)
        item := items[i]
        go func() {
            defer recoverPanic(ctx)
            defer func() {
                wg.Done()
                <-guard // release the slot
            }()
            r, err := process(ctx, item)
            if err != nil {
                log.Errorf("process: %v", err)
                return
            }
            results <- r
        }()
    }

    wg.Wait()
    close(results) // safe only after Wait — all senders are done

    merged := make(map[int]Result)
    for r := range results {
        merged[r.ID] = r
    }
    return merged
}
```

Notes: release the slot inside the deferred close so a panic (recovered above it — defers run LIFO) still frees the slot. If you never release on panic, the pool starves.

---

## 2. Fixed worker pool (long-lived workers, jobs + results channels)

When you have a stream of jobs and want a stable goroutine count rather than spawning per item — especially when each worker holds an expensive resource (a connection, a client). Tolerates partial failure by returning both results and errors.

```go
type job struct{ items []Item }
type result struct {
    out         []Item
    unprocessed []Item // returned on panic so the caller can retry
    err         error
}

func runPool(ctx context.Context, all []Item, workers, batchSize int) ([]Item, []error) {
    n := min(len(all)/batchSize+1, workers) // never more workers than jobs
    jobs := make(chan job, n)
    results := make(chan result, len(all)) // large enough that workers never park

    var wg sync.WaitGroup
    wg.Add(n)
    for i := 0; i < n; i++ {
        go func() {
            var cur job
            defer func() {
                if r := recover(); r != nil {
                    results <- result{unprocessed: cur.items, err: fmt.Errorf("panic: %v", r)}
                }
                wg.Done()
            }()
            for cur = range jobs { // assign to the outer var so the recover sees the live job
                out, err := process(ctx, cur.items)
                results <- result{out: out, err: err}
            }
        }()
    }

    for i := 0; i < len(all); i += batchSize {
        jobs <- job{items: all[i:min(i+batchSize, len(all))]}
    }
    close(jobs) // signal workers to drain and exit

    wg.Wait()
    close(results)

    var out []Item
    var errs []error
    for r := range results {
        out = append(out, r.out...)
        if r.err != nil {
            errs = append(errs, r.err)
        }
    }
    return out, errs
}
```

Notes: the `cur` variable is declared outside the `range` so the deferred `recover` can hand back the in-flight job's items. Accumulate errors, never drop them — the caller decides retry-vs-fail.

---

## 3. Parallel fan-out tolerating partial failure (WaitGroup + buffered result channel)

The default shape for request enrichment: split one logical call into N concurrent pieces, fire them, merge after. A single piece failing is logged and skipped — it must not abort the rest. This is what most fan-outs actually want.

```go
type piece struct {
    idx  int
    data *Partial
    err  error
}

func fetchInParallel(ctx context.Context, chunks [][]Item) *Aggregate {
    var wg sync.WaitGroup
    out := make(chan piece, len(chunks)) // capacity == number of goroutines

    for i, chunk := range chunks {
        wg.Add(1)
        go func(idx int, chunk []Item) { // pass loop vars explicitly
            defer recoverPanic(ctx)
            defer wg.Done()
            data, err := callDependency(ctx, chunk)
            out <- piece{idx: idx, data: data, err: err}
        }(i, chunk)
    }

    wg.Wait()
    close(out)

    agg := newAggregate()
    for p := range out {
        if p.err != nil {
            log.Errorf("chunk %d failed: %v", p.idx, p.err) // tolerate, keep merging
            continue
        }
        agg.merge(p.data)
    }
    return agg
}
```

Notes: channel capacity must equal the number of senders or `wg.Wait()` deadlocks. The function returns a best-effort aggregate with no top-level error — degraded results are the contract.

---

## 4. errgroup for all-or-nothing fan-out

Use only when every sub-call must succeed and you want the first error to abort the rest. The distinction below is the whole point:

```go
import "golang.org/x/sync/errgroup"

// WANT early cancellation on first error → WithContext, and thread the derived ctx in.
func loadAllStrict(ctx context.Context, loaders []func(context.Context) error) error {
    g, ctx := errgroup.WithContext(ctx)
    for _, load := range loaders {
        load := load
        g.Go(func() error { return load(ctx) }) // each loader must respect ctx cancellation
    }
    if err := g.Wait(); err != nil {
        return fmt.Errorf("loader failed: %w", err)
    }
    return nil
}
```

Gotcha: a plain `errgroup.Group{}` (no `WithContext`) collects the first non-nil error but does **not** cancel the other goroutines — it still waits for all of them. If you want sibling cancellation, you must use `WithContext` and pass the derived context into each func. Reach for errgroup only when all-or-nothing is the real contract; otherwise pattern 3 gives you partial results.

---

## 5. Typed async loader: fire early, await later

A single dependency call you want to kick off early and drain after doing other work. The struct variant is idempotent on re-await (safe when more than one code path may await the same instance).

```go
type Loader struct {
    Input  Params
    respCh chan *Result
    errCh  chan error
    mu     sync.Mutex
    done   bool
    res    *Result
    resErr error
}

func (l *Loader) LoadAsync(ctx context.Context) {
    l.respCh = make(chan *Result, 1) // buffered-1: goroutine always finishes even with no reader
    l.errCh = make(chan error, 1)
    go func() {
        defer recoverPanic(ctx) // before the close defer (LIFO) so channels still close on panic
        defer func() { close(l.respCh); close(l.errCh) }()
        res, err := call(ctx, l.Input)
        l.respCh <- res
        l.errCh <- err
    }()
}

func (l *Loader) Await() (*Result, error) {
    l.mu.Lock()
    defer l.mu.Unlock()
    if l.done {
        return l.res, l.resErr // idempotent second await
    }
    l.done = true
    l.res = <-l.respCh
    l.resErr = <-l.errCh
    return l.res, l.resErr
}

// caller
l := &Loader{Input: p}
l.LoadAsync(ctx)
// ... other synchronous work overlaps the call ...
res, err := l.Await()
if err != nil {
    log.Warnf("dependency failed, degrading: %v", err)
    // continue with a fallback — don't abort
}
```

Stateless variant when the result is consumed exactly once and you don't need the idempotency guard:

```go
func CallAsync(ctx context.Context, p Params) (<-chan *Result, <-chan error) {
    respCh := make(chan *Result, 1)
    errCh := make(chan error, 1)
    go func() {
        defer recoverPanic(ctx)
        defer func() { close(respCh); close(errCh) }()
        res, err := call(ctx, p)
        respCh <- res
        errCh <- err
    }()
    return respCh, errCh // receive-only return types prevent callers sending
}
```

The cap-1 buffer guarantees the goroutine finishes even if the caller takes an early-return branch and never reads — it won't leak. Draining both channels anyway keeps callsites uniform.

---

## 6. Generic one-shot future

The lightest possible parallelism: wrap any `func() T` and collect later. No error channel — the function handles its own errors and returns a zero value on failure. Use when one cheap-but-non-trivial step can overlap the remaining synchronous work.

```go
func Async[T any](ctx context.Context, fn func() T) <-chan T {
    ch := make(chan T, 1)
    go func() {
        defer recoverPanic(ctx)
        defer close(ch)
        ch <- fn()
    }()
    return ch
}

// caller
mapCh := Async(ctx, func() map[int][]uint64 { return buildMapping(ctx, ids) })
// ... other work ...
m := <-mapCh
```

If you need to propagate an error, use the channel-pair variant in §5 instead.

---

## 7. Per-call timeout with select on ctx.Done()

Bound the latency of an optional/degradable call and distinguish "timed out" from "errored" (so you can meter timeouts separately).

```go
func callWithTimeout(ctx context.Context, timeout time.Duration) Result {
    if timeout > 0 {
        var cancel context.CancelFunc
        ctx, cancel = context.WithTimeout(ctx, timeout)
        defer cancel() // always — leaks the timer otherwise
    }

    ch := make(chan Result, 1) // MUST be buffered: late goroutine still needs to write
    go func() {
        defer recoverPanic(ctx)
        ch <- doWork(ctx)
    }()

    select {
    case r := <-ch:
        return r
    case <-ctx.Done():
        recordTimeout()
        return Result{Err: ctx.Err()}
    }
}
```

Read the timeout from config at call time, not as a compile-time constant — it lets you tune per-path latency budgets without a deploy. `context.WithTimeout` only ever shortens: the effective deadline is `min(parent, now+timeout)`.

---

## 8. Typed private context keys for request-scoped values

Propagate request identity (user, tenant, trace, resolved feature flags) without threading parameters through every signature.

```go
package reqscope

type ctxKey string // unexported — no other package can collide with this key

const scopeKey ctxKey = "scope"

func Inject(ctx context.Context, s *Scope) context.Context {
    return context.WithValue(ctx, scopeKey, s)
}

func From(ctx context.Context) (*Scope, bool) {
    s, ok := ctx.Value(scopeKey).(*Scope)
    return s, ok
}
```

Rules:
- The private key type is the point. A bare `string` key collides with any other package using the same literal.
- **Never store mutable types (maps, slices) in a context value that goroutines read concurrently** — it's a data race. Only primitives and immutable value types belong in request scope; anything mutable needs its own mutex and shouldn't ride in context.
- Don't put optional call parameters (pagination, sort order) in context — they become invisible to callers, untestable, and unanalyzable. Context is for cross-cutting identity, not arguments.
- When you fork a context for a fire-and-forget goroutine, copy the values you need into a detached context (see §10) — the request context's deadline will cancel work that must outlive the request.

---

## 9. Lazy singleton with sync.Once

A package wrapping a single expensive resource (a client, a connection pool) initialized exactly once, race-safe, with no per-call mutex after startup.

```go
var (
    instance Client
    once     sync.Once
)

func Init(ctx context.Context) {
    once.Do(func() {
        conn, err := dial(ctx)
        if err != nil {
            log.Errorf("init: %v", err) // instance stays nil
            return
        }
        instance = &client{conn: conn}
    })
}

func Get() Client { return instance } // callers MUST handle nil
```

Gotchas: if `dial` errors, `instance` is nil and `Once` never retries for the process lifetime — every callsite must nil-check (return a sentinel `ErrNotInitialised`). Appropriate for stable dependencies; a flaky dependency that needs reconnection wants a different mechanism. Concurrent `Init` calls from parallel startup are safe — each package owns its own `once`.

---

## 10. Graceful startup waves and shutdown ordering

Parallelize independent startup with WaitGroup in dependency waves; on shutdown, stop accepting work before tearing down what it depends on.

```go
func startup(ctx context.Context) {
    // wave 1: infrastructure, in parallel
    wave(ctx, initDatastore, initCache, initQueue, initObjectStore)
    // wave 2: clients that depend on wave 1
    wave(ctx, initClientA, initClientB)
}

func wave(ctx context.Context, fns ...func(context.Context)) {
    var wg sync.WaitGroup
    wg.Add(len(fns))
    for _, fn := range fns {
        fn := fn
        go func() {
            defer wg.Done()
            defer recoverPanic(ctx) // per-goroutine — a panic here is otherwise silent
            fn(ctx)
        }()
    }
    wg.Wait()
}

func main() {
    ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
    defer stop()
    startup(ctx)

    go server.Serve()
    <-ctx.Done() // block until SIGINT/SIGTERM

    server.GracefulStop()   // 1. stop accepting new work FIRST
    closeClients()          // 2. then tear down dependencies (reverse of startup)
    closeInfrastructure()   // 3.
}
```

Don't use errgroup for startup waves: it cancels the shared context on the first error, which would abort sibling inits. You want every init to complete and report its own failure independently.

---

## 11. Caching

### Two-tier cache (in-process L1 + distributed L2)

Hot read paths where a network round-trip per read is too slow, but cross-instance consistency still matters. L1 absorbs repeated reads within one instance; L2 is the shared source of truth.

```go
func GetCached[T any](ctx context.Context, key string, l1 *localCache, l2 DistributedCache,
    load func(context.Context) (T, error)) (T, error) {

    if v, ok := getL1[T](l1, key); ok {
        return v, nil
    }
    var v T
    if found, _ := l2.Get(ctx, key, &v); found {
        _ = setL1(l1, key, v, l1TTL) // write-back to L1
        return v, nil
    }
    v, err := load(ctx)
    if err != nil {
        return v, err
    }
    _ = l2.Set(ctx, key, v, l2TTL)
    _ = setL1(l1, key, v, l1TTL)
    return v, nil
}
```

Rules: L1 is instance-local — a write on one instance does not invalidate L1 elsewhere, so use it only where a few seconds of cross-instance staleness is acceptable. Keep L1 TTL well below L2 TTL or a targeted L2 invalidation still serves stale data from L1. In-process caches have hard per-value size limits — check the set error rather than failing silently. Measure serialization/compression cost; on very hot paths it can exceed the round-trip it saves.

### TTL jitter — always

Any time many keys are written together (batch refresh, prewarming, startup) they expire together without jitter, stampeding the origin. Jitter at write time, always.

```go
// TTL uniformly sampled from [base, base+jitter).
func ttlWithJitter(base, jitter time.Duration) time.Duration {
    return base + time.Duration(rand.Int63n(int64(jitter)+1))
}

cache.Set(ctx, key, val, ttlWithJitter(24*time.Hour, 4*time.Hour))
```

For data that expires at a fixed wall-clock moment, compute `expiry.Sub(time.Now())` then add jitter on top. Guard against a zero jitter window (`rand.Int63n(0)` panics).

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
    for i, c := range cmds {
        _ = c.Decode(&out[i]) // per-key errors are visible only here, not from Exec
    }
    return out, nil
}
```

`Exec` returns one top-level error; individual command errors surface only when you decode each result — always check per-key, not just the top level. Hash-field set + TTL needs two flushes (set, then expire) since there's no atomic combined command.

---

## 12. Resilience

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
    if exists, _ := cache.Has(ctx, snapshotKey(key)); exists {
        return // idempotency guard — prevents a snapshot storm under load
    }
    _ = cache.Set(ctx, snapshotKey(key), true, ttlWithJitter(base, jitter))
    bg := detach(ctx) // copy values, drop the request deadline
    go func() {
        defer recoverPanic(bg)
        if err := store.Put(bg, key, data); err != nil {
            _ = cache.Delete(bg, snapshotKey(key)) // roll back the guard so the next request retries
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

## Choosing fast — summary

| You need | Reach for |
|----------|-----------|
| Cap simultaneous goroutines | semaphore channel (§1) |
| Stable goroutine count over a job stream | fixed worker pool (§2) |
| Fan-out, tolerate partial failure | WaitGroup + buffered channel (§3) |
| Fan-out, all-or-nothing, cancel on first error | `errgroup.WithContext` (§4) |
| Fire one call early, await later | typed async loader (§5) |
| One-line "future", no error | generic `Async[T]` (§6) |
| Bound one call's latency | `context.WithTimeout` + select (§7) |
| Collapse duplicate concurrent loads | `singleflight` (§11) |
| Survive a dependency outage on a read path | last-known-good degradation (§12) |
