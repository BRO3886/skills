# Concurrency Code Templates

Use these templates after choosing the result contract and lifecycle owner. Every goroutine must report completion or failure to its owner. If a boundary recovers a panic, convert it to an error, record the incident, and unblock every waiter.

## Contents

- [1. Bounded fan-out via a semaphore channel](#1-bounded-fan-out-via-a-semaphore-channel)
- [2. Fixed worker pool](#2-fixed-worker-pool-long-lived-workers-jobs--results-channels)
- [3. Parallel fan-out with partial results](#3-parallel-fan-out-tolerating-partial-failure-waitgroup--buffered-result-channel)
- [4. All-or-nothing fan-out with errgroup](#4-errgroup-for-all-or-nothing-fan-out)
- [5. Typed async loader](#5-typed-async-loader-fire-early-await-later)
- [6. Generic one-shot future](#6-generic-one-shot-future)
- [7. Per-call timeout](#7-per-call-timeout-with-select-on-ctxdone)
- [8. Typed private context keys](#8-typed-private-context-keys-for-request-scoped-values)
- [9. Lazy singleton with sync.Once](#9-lazy-singleton-with-synconce)
- [10. Startup waves and shutdown ordering](#10-graceful-startup-waves-and-shutdown-ordering)

Use one non-recovering helper to record the stack and construct the error that each owning boundary delivers:

```go
func panicError(ctx context.Context, operation string, recovered any) error {
    log.ErrorfWithContext(ctx, "%s panic: %v\n%s", operation, recovered, debug.Stack())
    return fmt.Errorf("%s panic: %v", operation, recovered)
}
```

---

## 1. Bounded fan-out via a semaphore channel

Process N items concurrently while capping simultaneous goroutines at K (K ≪ N). The classic shape for batching expensive outbound calls across a large input set without a pool library.

```go
type itemResult struct {
    result Result
    err    error
}

func processAll(ctx context.Context, items []Item, maxWorkers int) (map[int]Result, error) {
    var wg sync.WaitGroup
    results := make(chan itemResult, len(items)) // sized to senders — never parks
    guard := make(chan struct{}, maxWorkers) // the semaphore

    for i := range items {
        guard <- struct{}{} // acquire a slot (blocks at the limit)
        wg.Add(1)
        item := items[i]
        go func() {
            defer func() {
                if r := recover(); r != nil {
                    results <- itemResult{err: panicError(ctx, "process", r)}
                }
                wg.Done()
                <-guard // release the slot
            }()
            r, err := process(ctx, item)
            results <- itemResult{result: r, err: err}
        }()
    }

    wg.Wait()
    close(results) // safe only after Wait — all senders are done

    merged := make(map[int]Result)
    var errs []error
    for r := range results {
        if r.err != nil {
            errs = append(errs, r.err)
            continue
        }
        merged[r.result.ID] = r.result
    }
    return merged, errors.Join(errs...)
}
```

Notes: one deferred boundary owns panic conversion, completion, and semaphore release. The caller receives every successful result plus an aggregated error for failed items.

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
                    results <- result{unprocessed: cur.items, err: panicError(ctx, "worker", r)}
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

The default shape for request enrichment: split one logical call into N concurrent pieces, fire them, then merge every success. A failed piece does not abort its siblings, but its error remains part of the result contract.

```go
type piece struct {
    idx  int
    data *Partial
    err  error
}

func fetchInParallel(ctx context.Context, chunks [][]Item) (*Aggregate, error) {
    var wg sync.WaitGroup
    out := make(chan piece, len(chunks)) // capacity == number of goroutines

    for i, chunk := range chunks {
        wg.Add(1)
        go func(idx int, chunk []Item) { // pass loop vars explicitly
            defer func() {
                if r := recover(); r != nil {
                    out <- piece{idx: idx, err: panicError(ctx, "chunk", r)}
                }
                wg.Done()
            }()
            data, err := callDependency(ctx, chunk)
            out <- piece{idx: idx, data: data, err: err}
        }(i, chunk)
    }

    wg.Wait()
    close(out)

    agg := newAggregate()
    var errs []error
    for p := range out {
        if p.err != nil {
            errs = append(errs, fmt.Errorf("chunk %d: %w", p.idx, p.err))
            continue
        }
        agg.merge(p.data)
    }
    return agg, errors.Join(errs...)
}
```

Notes: channel capacity must equal the number of senders or `wg.Wait()` deadlocks. The function returns a complete aggregate of successful pieces plus an aggregated error for failures.

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
    result chan loadResult
    mu     sync.Mutex
    done   bool
    res    *Result
    resErr error
}

type loadResult struct {
    value *Result
    err   error
}

func (l *Loader) LoadAsync(ctx context.Context) {
    l.result = make(chan loadResult, 1) // buffered-1: goroutine finishes without a reader
    go func() {
        defer func() {
            if r := recover(); r != nil {
                l.result <- loadResult{err: panicError(ctx, "dependency", r)}
            }
            close(l.result)
        }()
        res, err := call(ctx, l.Input)
        l.result <- loadResult{value: res, err: err}
    }()
}

func (l *Loader) Await() (*Result, error) {
    l.mu.Lock()
    defer l.mu.Unlock()
    if l.done {
        return l.res, l.resErr // idempotent second await
    }
    l.done = true
    result := <-l.result
    l.res = result.value
    l.resErr = result.err
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
func CallAsync(ctx context.Context, p Params) <-chan loadResult {
    result := make(chan loadResult, 1)
    go func() {
        defer func() {
            if r := recover(); r != nil {
                result <- loadResult{err: panicError(ctx, "dependency", r)}
            }
            close(result)
        }()
        res, err := call(ctx, p)
        result <- loadResult{value: res, err: err}
    }()
    return result // receive-only return type prevents callers sending
}
```

The cap-1 buffer guarantees the goroutine finishes even if the caller returns without reading. One result channel also keeps value and error delivery atomic.

---

## 6. Generic one-shot future

The lightest explicit future: wrap any `func() (T, error)` and collect its value and failure later. Use when one cheap but non-trivial step can overlap the remaining synchronous work.

```go
type asyncResult[T any] struct {
    value T
    err   error
}

func Async[T any](ctx context.Context, fn func() (T, error)) <-chan asyncResult[T] {
    ch := make(chan asyncResult[T], 1)
    go func() {
        defer func() {
            if r := recover(); r != nil {
                ch <- asyncResult[T]{err: panicError(ctx, "async", r)}
            }
            close(ch)
        }()
        value, err := fn()
        ch <- asyncResult[T]{value: value, err: err}
    }()
    return ch
}

// caller
mapCh := Async(ctx, func() (map[int][]uint64, error) { return buildMapping(ctx, ids) })
// ... other work ...
result := <-mapCh
if result.err != nil {
    return result.err
}
m := result.value
```

Use the typed loader in section 5 when the operation needs idempotent repeated awaits.

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
        defer func() {
            if r := recover(); r != nil {
                ch <- Result{Err: panicError(ctx, "work", r)}
            }
        }()
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
func startup(ctx context.Context) error {
    // wave 1: infrastructure, in parallel
    if err := wave(ctx, initDatastore, initCache, initQueue, initObjectStore); err != nil {
        return fmt.Errorf("infrastructure startup: %w", err)
    }
    // wave 2: clients that depend on wave 1
    if err := wave(ctx, initClientA, initClientB); err != nil {
        return fmt.Errorf("client startup: %w", err)
    }
    return nil
}

func wave(ctx context.Context, fns ...func(context.Context) error) error {
    var wg sync.WaitGroup
    errs := make(chan error, len(fns))
    wg.Add(len(fns))
    for _, fn := range fns {
        fn := fn
        go func() {
            defer func() {
                if r := recover(); r != nil {
                    errs <- panicError(ctx, "startup", r)
                }
                wg.Done()
            }()
            if err := fn(ctx); err != nil {
                errs <- err
            }
        }()
    }
    wg.Wait()
    close(errs)
    var failures []error
    for err := range errs {
        failures = append(failures, err)
    }
    return errors.Join(failures...)
}

func main() {
    ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
    defer stop()
    if err := startup(ctx); err != nil {
        log.Fatalf("startup: %v", err)
    }

    go server.Serve()
    <-ctx.Done() // block until SIGINT/SIGTERM

    server.GracefulStop()   // 1. stop accepting new work FIRST
    closeClients()          // 2. then tear down dependencies (reverse of startup)
    closeInfrastructure()   // 3.
}
```

Do not use `errgroup.WithContext` for startup waves when every initializer must finish and report independently. Aggregate all failures, then stop before serving traffic.

---
