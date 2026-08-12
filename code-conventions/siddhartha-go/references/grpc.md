# gRPC Service Code Templates

Use these templates for server and client boundaries. Interceptor order, metadata propagation, transport policy, and panic conversion are part of the service contract.

## Contents

- [1. Interceptor chain](#1-interceptor-chain--order-by-dependency-not-by-taste)
- [2. Panic recovery interceptor](#2-panic-recovery-interceptor--named-returns-are-the-trick)
- [3. Metadata propagation](#3-metadata-propagation--inbound-headers-to-outbound-calls)
- [4. Centralized dial wrapper](#4-centralized-dial-wrapper--synconce-singleton-client)

---

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
