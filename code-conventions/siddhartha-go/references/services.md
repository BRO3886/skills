# gRPC Services, Observability & Runtime Config — Code Templates

Templates for the patterns summarized in `SKILL.md`'s gRPC, Observability, and Config sections. Extracted from production Go services that run as gRPC servers fanning out to many gRPC clients under real traffic. Read this when standing up a gRPC service, wiring interceptors, instrumenting code, or adding runtime-tunable config.

`recoverPanic(ctx)` is your panic-recovery helper (recover, log with context, swallow or convert to an error). `rconfig.GetX(ctx, key)` is your runtime-config accessor — reads a key from a config/flag store at call time.

---

# gRPC

## 1. Interceptor chain — order by dependency, not by taste

The chain order is load-bearing. Each interceptor can depend on context set up by an earlier one; getting it wrong fails silently (a later interceptor reads a zero value, or a panic escapes uncaught). First element = outermost wrapper.

```go
unary := []grpc.UnaryServerInterceptor{
    recoveryInterceptor,            // 1. outermost — catches panics in every interceptor below it
    config.Interceptor(),           // 2. loads runtime config into ctx — must precede anything reading it
    logging.Interceptor(mode),      // 3. seeds the request-scoped logger + request id — early so all layers log
    requestScopeInterceptor(),      // 4. cache-bypass / per-request settings into ctx
    headerInterceptor(),            // 5. decode inbound metadata → typed context values
    authnInterceptor(),             // 6. authentication — AFTER header so identity is in ctx
    authzInterceptor(allowlist),    // 7. authorization
    validationInterceptor(),        // 8. response validation
    tracingInterceptor(),           // 9. APM span attributes
    rateLimitInterceptor(),         // 10.
}
srv := grpc.NewServer(grpc.ChainUnaryInterceptor(unary...))
```

Rules: recovery must be first or it can't catch panics thrown by the interceptors it doesn't wrap. The config loader must precede any interceptor that reads runtime config. The header/metadata decoder must precede auth, which reads identity from context. A background/worker server uses a shorter chain (no auth, no header) but keeps recovery-first, config-second.

---

## 2. Panic recovery interceptor — named returns are the trick

A panicking handler crashes the whole process unless a recovery interceptor converts it to an error. The load-bearing detail is **named return values** — a deferred closure can only assign to the function's return if it's named.

```go
func recoveryInterceptor(ctx context.Context, req any, info *grpc.UnaryServerInfo,
    handler grpc.UnaryHandler) (resp any, err error) { // named returns
    defer func() {
        if r := recover(); r != nil {
            stack := debug.Stack()
            log.Errorf("[PANIC] %v in %s\n%s", r, info.FullMethod, stack)
            alert(ctx, fmt.Sprintf("panic in %s", info.FullMethod), string(stack)) // page on-call
            err = status.Error(codes.Internal, "internal error") // assign the named return
        }
    }()
    return handler(ctx, req)
}
```

Without named returns the deferred closure can't set the return — the caller gets `(nil, nil)`, a fake success hiding the panic. Always log the full `debug.Stack()` (the panic value alone is usually just a string), and always fire an alert: this interceptor hides the crash from the caller, so silent recovery can mask an outage.

---

## 3. Metadata propagation — inbound headers to outbound calls

A service that is both a server and a client must thread trace id, identity, and pass-through headers through the call graph so downstream services see the same request context the edge saw. Two halves: a server interceptor that decodes inbound metadata into context, and a client interceptor that re-encodes context onto outbound calls.

```go
// SERVER: decode inbound metadata into typed context values (run before auth/handlers)
func headerInterceptor() grpc.UnaryServerInterceptor {
    return func(ctx context.Context, req any, _ *grpc.UnaryServerInfo,
        handler grpc.UnaryHandler) (any, error) {
        md, ok := metadata.FromIncomingContext(ctx) // returns a copy, not live
        if ok {
            if v := md.Get("x-lang"); len(v) > 0 {
                ctx = withLang(ctx, v[0])
            }
            if v := md.Get("x-client-id"); len(v) > 0 {
                ctx = withClient(ctx, v[0])
            }
        }
        return handler(ctx, req)
    }
}

// CLIENT: re-encode derived ctx values + pass-through headers onto the outbound call
func metadataClientInterceptor() grpc.UnaryClientInterceptor {
    passthrough := []string{"x-lang", "x-device-id", "x-trace-id"}
    return func(ctx context.Context, method string, req, reply any,
        cc *grpc.ClientConn, invoke grpc.UnaryInvoker, opts ...grpc.CallOption) error {
        ctx = metadata.AppendToOutgoingContext(ctx, // Append, not New — don't clobber other interceptors' keys
            "x-trace-id", traceID(ctx),
            "x-request-source", "my-service",
        )
        if in, ok := metadata.FromIncomingContext(ctx); ok {
            for _, h := range passthrough {
                for _, v := range in.Get(h) {
                    ctx = metadata.AppendToOutgoingContext(ctx, h, v)
                }
            }
        }
        return invoke(ctx, method, req, reply, cc, opts...)
    }
}
```

Gotchas: `FromIncomingContext` returns a copy — mutating it doesn't touch the context. Its `ok` and a key's presence are independent (a valid metadata context can have zero keys), so check both. Use `AppendToOutgoingContext`, never `NewOutgoingContext`, so you don't wipe keys other interceptors set.

---

## 4. Centralized Dial wrapper + sync.Once singleton client

Every downstream dependency dials through one wrapper that encodes shared transport policy (keepalive, interceptor chain, credentials). The client is a `sync.Once` singleton — connected once at startup, reused for the process lifetime.

```go
func Dial(service string, opts ...grpc.DialOption) (*grpc.ClientConn, error) {
    addr := config.GetString("services." + service + ".addr")
    chain := []grpc.UnaryClientInterceptor{
        retryInterceptor(),            // OUTERMOST — retries re-invoke all inner interceptors per attempt
        metadataClientInterceptor(),   // propagate trace/identity
        errorReportingInterceptor(),   // wrap errors, report to the tracer
        metricsInterceptor(),          // latency + throughput
        killSwitchInterceptor(service + ".kill_switch"), // innermost — per-service circuit breaker
    }
    base := []grpc.DialOption{
        grpc.WithTransportCredentials(insecure.NewCredentials()), // internal mesh
        grpc.WithChainUnaryInterceptor(chain...),
        grpc.WithKeepaliveParams(keepalive.ClientParameters{
            Time: 10 * time.Second, Timeout: 5 * time.Second, PermitWithoutStream: true,
        }),
    }
    return grpc.NewClient(addr, append(base, opts...)...)
}

type Client interface {
    Do(ctx context.Context, r *Request) (*Response, error)
}

var (
    instance Client
    once     sync.Once
)

func Init() {
    once.Do(func() {
        conn, err := Dial("thing-service")
        if err != nil {
            log.Errorf("thing-service connect: %v", err) // instance stays nil
            return
        }
        instance = &client{conn: conn, pb: pb.NewThingClient(conn)}
    })
}

func Get() Client { return instance } // callers MUST nil-check

// per-call: split total deadline from per-attempt timeout
func (c *client) Do(ctx context.Context, r *Request) (*Response, error) {
    ctx, cancel := context.WithTimeout(ctx, msToDur("thing-service.timeout_ms"))
    defer cancel()
    resp, err := c.pb.Do(ctx, r.toProto(),
        withPerTryTimeout(msToDur("thing-service.per_try_timeout_ms")),
        withRetry(config.GetBool(ctx, "thing-service.retry_enabled")),
    )
    if err != nil {
        return nil, fmt.Errorf("thing-service Do: %w", err)
    }
    return fromProto(resp), nil
}
```

Gotchas: `sync.Once` does not retry on failure — if the first dial errors, `instance` is nil for the process lifetime, so every method must nil-check and return a "not initialised" sentinel. Put the retry interceptor outermost so metrics/metadata/error-reporting fire per attempt. `PermitWithoutStream: true` pings with no active RPCs — keep `Time ≥ 10s` or a strict server returns `GOAWAY ENHANCE_YOUR_CALM`. The kill-switch interceptor returns a sentinel error that the error-reporting interceptor skips via `errors.As`, so tripping a kill switch doesn't page on-call.

---

# Observability

## 5. Context-bound structured logger, seeded at the boundary

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

Gotchas: when you spawn a goroutine with a fresh/derived context, copy the logger across explicitly (a `CopyLogger(from, to)` helper) — a derived context with a new deadline won't carry the seeded logger automatically. Keep the request id in both the logger fields and a raw context value, so the tracer can stamp spans without going through the logger. Pay cross-cutting costs (e.g. a per-level log counter) inside the shared helper, not at call sites.

## 6. Typed metric with a closed tag allowlist (cardinality control)

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

## 7. Defer-based latency histogram

Time a segment by passing `time.Now()` at the `defer` site — Go evaluates defer arguments when the `defer` is declared, not when it fires.

```go
func fetch(ctx context.Context, key string) ([]byte, error) {
    defer metrics.Latency(ctx, "cache_lookup", time.Now()) // time.Now() captured here, at entry
    // ... work ...
}
```

Gotcha: write `defer metrics.Latency(ctx, name, time.Now())`, NOT `defer func(){ metrics.Latency(ctx, name, time.Now()) }()` — the closure form evaluates `time.Now()` at function *return*, measuring nothing. `Milliseconds()` truncates sub-ms work to 0; use `Microseconds()` for tight paths. Don't emit a histogram per item inside a tight loop (each emit locks the client buffer) — record aggregate elapsed once after the loop.

## 8. Feature-gated tracing with a NoOp span fallback

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

# Runtime config & feature flags

The accessor reads a key from a config/flag store at call time (ctx-scoped), so changes take effect on the next request with no redeploy. The whole value is that flags are tunable live; the whole risk is a missing key returning a zero value.

## 9. Per-call kill switch with a sentinel error

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

## 10. Runtime-tunable number with an inline safe default

`GetInt` returns 0 for a missing key — and 0 is dangerous for a batch size (infinite loop) or a TTL (zero-second cache). Guard immediately, inline, with the conservative value.

```go
batch := rconfig.GetInt(ctx, "ranking.batch_size")
if batch <= 0 {
    batch = 50 // safe default, co-located with the read
}
```

The safe default is the conservative choice (smaller batch, longer TTL). Keep the fallback at the read site, not in a distant init function, so the reasoning is where the value is used.

## 11. Two-level feature gate (master toggle, then sub-params)

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

## 12. Tiered gradual rollout

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
