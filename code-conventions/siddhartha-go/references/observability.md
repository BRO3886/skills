# Observability Code Templates

Use these templates for request-scoped logging, cardinality-safe metrics, latency measurement, and runtime-gated tracing.

## Contents

- [1. Context-bound structured logger](#1-context-bound-structured-logger-seeded-at-the-boundary)
- [2. Typed metric tag allowlist](#2-typed-metric-with-a-closed-tag-allowlist-cardinality-control)
- [3. Defer-based latency histogram](#3-defer-based-latency-histogram)
- [4. Feature-gated tracing](#4-feature-gated-tracing-with-a-noop-span-fallback)

---

## 1. Context-bound structured logger, seeded at the boundary

Seed a logger with request-scoped fields once at the edge (interceptor/middleware); every downstream call just passes `ctx` and logs through `*WithContext` helpers that pull the logger back out. No logger argument threaded through signatures.

```go
// at the edge (interceptor):
func seedLogger(ctx context.Context, info *grpc.UnaryServerInfo, md metadata.MD) context.Context {
    reqID := first(md, "x-request-id")
    if reqID == "" {
        reqID = newID()
    }
    logger := log.FromContext(ctx).With(
        "request_id", reqID, "rpc", info.FullMethod, "client", first(md, "x-client-id"),
    )
    ctx = context.WithValue(ctx, requestIDKey, reqID) // also as a raw value for the tracer
    return log.NewContext(ctx, logger)
}

// everywhere downstream — no logger parameter:
func process(ctx context.Context, id int) {
    log.InfofWithContext(ctx, "processing %d", id) // helper calls log.FromContext(ctx) internally
}
```

Gotchas: `context.WithCancel`, `context.WithDeadline`, and `context.WithTimeout` preserve parent values. A fresh or detached context does not, so copy the logger explicitly when constructing one. Keep the request id in both the logger fields and a raw context value, so the tracer can stamp spans without going through the logger. Pay cross-cutting costs (e.g. a per-level log counter) inside the shared helper, not at call sites.

## 2. Typed metric with a closed tag allowlist (cardinality control)

Define each metric as a named type that declares exactly which tag keys are valid. A shared factory rejects calls with missing, extra, or empty tags before they hit the wire — you get a `metric_errors` bump instead of an unbounded time series.

```go
type CounterMetric interface {
    Name() string
    ValidTags() []string
    Increment() error
}

type UpstreamErrors struct{ counterCore }

func (*UpstreamErrors) Name() string        { return "upstream_errors_total" }
func (*UpstreamErrors) ValidTags() []string { return []string{"method", "code"} } // closed set

func recordErr(ctx context.Context, method, code string) {
    m, err := metrics.Counter(ctx, &UpstreamErrors{}, map[string]string{"method": method, "code": code})
    if err != nil {
        return // validation failed; metric_errors already incremented
    }
    _ = m.Increment()
}
```

Gotchas: cardinality blowup is *enforced*, not hoped for — `validate()` requires every `ValidTags()` key present and non-empty and rejects extras, so you can't accidentally tag with a user id or a raw URL. Bucket any high-cardinality dimension into ≤~20 string buckets before it becomes a tag. Provide a kill switch / no-op mode so tests don't panic on an uninitialised metrics client.

## 3. Defer-based latency histogram

Time a segment by passing `time.Now()` at the `defer` site — Go evaluates defer arguments when the `defer` is declared, not when it fires.

```go
func fetch(ctx context.Context, key string) ([]byte, error) {
    defer metrics.Latency(ctx, "cache_lookup", time.Now()) // time.Now() captured here, at entry
    // ... work ...
}
```

Gotcha: write `defer metrics.Latency(ctx, name, time.Now())`, NOT `defer func(){ metrics.Latency(ctx, name, time.Now()) }()` — the closure form evaluates `time.Now()` at function *return*, measuring nothing. `Milliseconds()` truncates sub-ms work to 0; use `Microseconds()` for tight paths. Don't emit a histogram per item inside a tight loop (each emit locks the client buffer) — record aggregate elapsed once after the loop.

## 4. Feature-gated tracing with a NoOp span fallback

Wrap operations in spans that can be toggled at runtime, with a NoOp span when tracing is off so call sites never nil-check.

```go
type Tracer interface {
    Start(ctx context.Context, name string) (context.Context, Span)
}

func (t *tracer) Start(ctx context.Context, name string) (context.Context, Span) {
    if !rconfig.GetBool(ctx, "tracing.enabled") {
        return ctx, noopSpan{} // every method empty; End() is a no-op
    }
    return t.real.Start(ctx, name)
}

// call site — identical whether tracing is on or off
ctx, span := tracer.Start(ctx, "fetch")
defer span.End()
```

Gotchas: the factory returns a real span or a NoOp, **never nil** — that's what lets call sites skip `if span != nil`. Put `defer span.End()` on the line right after `Start`. Make the tracer an interface so tests inject a no-op backend without build tags. Reading the flag per call lets you raise tracing depth on one canary without a deploy.

---
