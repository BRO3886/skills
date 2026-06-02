---
name: siddhartha-go
description: "Siddhartha's Go backend coding conventions and architecture patterns. Use when writing Go backend code, designing APIs, setting up new Go services, or making architecture decisions in Go projects. Also use when reviewing Go PRs, scaffolding new packages, or when someone asks about project structure conventions. Also use when parallelizing work, designing concurrency (worker pools, fan-out/fan-in, rate limiting, caching, graceful degradation), or reviewing goroutine-heavy Go for races and leaks."
---

# Siddhartha's Go Backend Style Guide

Coding style, architecture, and conventions extracted from Siddhartha's production Go projects (rem, gtasks, healthsync, go-eventkit, voice-agent, blay-tui, flexprice) and high-throughput backend services he's worked on. Follow these for all Go backend work; consistency across projects is the goal.

This file carries the **principles, decision rules, and gotchas** — the part that must stay in context. Worked code examples live in `references/` and load on demand:
- `references/conventions.md` — architecture, errors, API, HTTP, database, testing, config examples
- `references/concurrency.md` — worker pools, fan-out/fan-in, caching, resilience templates
- `references/services.md` — gRPC, observability, runtime-config templates
- `references/idioms.md` — code-shape / decomposition sketches
- `references/algorithms.md` — matching, dedup, interleave, scoring, slot-placement idioms

## Design Philosophy

The instincts behind the specific patterns below. Language-agnostic — when a concrete rule doesn't cover the situation, reason from these. They apply when writing or reviewing code in any language, not just Go.

- **Separate the decision from the action.** Keep core logic pure; push every "should this run?" and "what value?" out to the boundary. The unit that decides eligibility is distinct from the unit that does the work; config and feature flags are read at the edge and threaded in, not deep inside the logic; tunables arrive as constructor parameters, not reach-outs to a global. The payoff is logic you can test in isolation.
- **Design for testability first.** Shape code to be unit-testable without mocks: pure functions of their inputs, dependencies injected as interfaces, predicates that take plain values you can drive from a table. If a function needs a mock to test, the dependency probably belongs at the boundary.
- **Default to graceful partial results.** When an operation has independent parts that can each fail, collect what succeeds and return best-effort plus the error — don't abort the whole thing on one failure. All-or-nothing is a deliberate choice for the cases that truly need it, not the default.
- **Fail fast with flat control flow.** Prefer a negative-guard ladder (one condition per line, early return) over a compound boolean. Each line diffs cleanly and is independently breakpoint-able. Readability and debuggability beat cleverness.
- **Never leak inconsistent state.** A caller should never get a non-nil error alongside a half-written result. Ensure outputs — and any timing/metadata — are fully assigned on every return path, including early and error returns.
- **Code for the on-call engineer, not just correctness.** Build in kill switches and runtime levers, return sentinel errors so deliberate shutoffs are distinguishable from real failures, and keep expected conditions out of the alerting path. Operability is a feature.
- **Keep it simple until forced otherwise.** Concrete types over `any`, positional args over an options struct, no abstraction layer until the variation actually demands one. Add complexity in response to a real second case, not an anticipated one.

## Project Structure

```
cmd/<app>/main.go           # thin entry point — set build vars, load config, start
internal/
  api/v1/                   # HTTP handlers, one file per domain entity
  api/dto/                  # request/response types (separate from domain models)
  api/router.go             # all route registration in one file
  domain/<entity>/          # model.go (struct) + repository.go (interface, lives WITH the model)
  service/<entity>.go       # business logic — takes repo interface, returns service interface
  repository/postgres/      # (or ent/, sqlite/) implements the domain repository interfaces
  config/config.go          # single Configuration struct, env-specific YAML
  errors/errors.go          # sentinel errors + builder (larger projects)
```

The `internal/` boundary is load-bearing — everything goes inside it; the only things outside are `cmd/` and maybe a root `embed.go`. `main.go` stays under ~30 lines (set build vars, load config, start — no business logic, routing, or middleware). Example in `references/conventions.md`.

## Naming

- **Packages:** short, lowercase, single word, no plurals. `api`, `config`, `service`, `dto` — not `services`, `api-handlers`, `expense_service`.
- **Types:** `PascalCase` (`ExpenseService`, `SplitType`). **Exported funcs:** `PascalCase` (`NewExpenseService`, `ParsePriority`). **Unexported:** `camelCase` (`parseDate`, `fromDBModel`). **Vars:** short, contextual (`db`, `cfg`, `tx`, `rows`).
- **Enums:** named type with iota, a `String()` method, and a `Parse*()` constructor — always all three.
- **Boundary translation:** `from*` for incoming conversions, `to*` for outgoing (`fromDBExpense`, `toDBCreateInput`).
- **Interfaces:** no `I` prefix. The interface is the concept (`ExpenseService`), the unexported struct is the implementation (`expenseService`).
- **Files:** lowercase, underscores for multi-word (`huh_helpers.go`). One file per domain entity in each layer.

## Architecture: Service / Repository

The core pattern. Full code in `references/conventions.md`.

- **The repository interface belongs to the domain**, not the implementation — it describes the storage operations the domain needs. It lives in the domain package alongside the model.
- **A service is a public interface + an unexported struct; the constructor returns the interface.** This lets tests swap a fake repository in without touching service code.
- **DI via Uber Fx.** Register every constructor with `fx.Provide`; use `fx.In` parameter objects for many-dependency structs; wire it all in `main.go`; use `fx.Lifecycle` hooks for startup/shutdown.
- **Deployment mode switch** for multi-role services — one binary, a `switch cfg.Mode` selecting API / worker / consumer / local-all-in-one.

## Error Handling

Code in `references/conventions.md`.

- **Wrap every error with operation context**: `fmt.Errorf("getting expense %s: %w", id, err)` — always `%w` so the chain stays inspectable.
- **Sentinel errors + a fluent builder** in `internal/errors/`. The builder separates an internal message (detailed, for logs) from a `WithHint` user-facing message (helpful, for the API response), and `Mark`s a sentinel so `errors.Is` works.
- **One centralized HTTP error middleware** maps sentinels to status codes; handlers just call `c.Error(err)` and return — they never write error status codes themselves.
- **Best-effort operations** (cache writes, background side effects) swallow their errors silently.

## API Design

Code in `references/conventions.md`.

- **Named input structs** for any operation with 3+ parameters, with `binding` tags for validation.
- **Partial updates use pointer fields** — nil means "don't change this field"; check `Changed()` (CLI) or nil (API) before applying.
- **Functional options** (`WithGroup(id)`, `WithSettled(b)`) for complex/optional query filters.

## HTTP Layer

Code in `references/conventions.md`.

- **Gin, always `gin.New()` not `gin.Default()`** — control the middleware stack explicitly. Order: `RequestID → Logging → CORS → Auth → ErrorHandler`.
- **Typed context keys** (`type ctxKey string`) set by auth middleware, read via typed getters — never raw `ctx.Value` downstream.
- **DTOs live in `internal/api/dto/`**, separate from domain models; the handler converts between them (`req.ToDomain()`, `dto.FromExpense(result)`).

## gRPC Services

Templates in `references/services.md` — read it when standing up a gRPC service or wiring interceptors.

- **Order the interceptor chain by dependency, not taste.** First element = outermost. Recovery first (catches panics in everything below it), then the runtime-config loader (before anything that reads config), then logging + request-id, then inbound-metadata→context decode, then auth (after metadata so identity is in ctx), then validation/tracing/rate-limit. Wrong order fails silently.
- **The panic-recovery interceptor uses named returns** — a deferred `recover()` can only set the error if the signature is `(resp any, err error)`. Without it the caller gets a fake `(nil, nil)` success. Log the full `debug.Stack()` and fire an alert; silent recovery masks outages.
- **Propagate metadata both ways.** A server interceptor decodes inbound metadata into typed context values (before auth); a client interceptor re-encodes trace/identity + pass-through headers onto outbound calls with `metadata.AppendToOutgoingContext` (never `New...`, which clobbers other interceptors' keys).
- **One Dial wrapper + one `sync.Once` singleton per dependency.** The wrapper holds shared transport policy (keepalive `Time ≥ 10s` with `PermitWithoutStream`, the client interceptor chain, credentials). Retry interceptor outermost so metrics/metadata fire per attempt; kill-switch innermost returning a sentinel the error-reporter skips via `errors.As` (so a tripped kill doesn't page). `sync.Once` doesn't retry on dial failure — methods must nil-check the client.
- **Split total deadline from per-attempt timeout** on every call (see Caching & Resilience).

## Observability

Templates in `references/services.md` (§5–8).

- **Seed a context-bound logger at the boundary**, then pass only `ctx`. The edge interceptor attaches a logger carrying request id / RPC / client; downstream code logs via `*WithContext` helpers that pull it from ctx — no logger threaded through signatures. Copy the logger explicitly when spawning a goroutine with a fresh context.
- **Metrics carry a closed tag allowlist.** Define each metric as a typed struct declaring its valid tag keys; a shared factory rejects missing/extra/empty tags before the wire. Bucket high-cardinality dimensions (ids, URLs) into ≤~20 string buckets before tagging — unbounded tag values blow up the backend.
- **Time segments with `defer metrics.Latency(ctx, name, time.Now())`** — defer args evaluate at registration, so `time.Now()` captures entry time. The closure form `defer func(){ ...time.Now() }()` measures nothing. Don't emit per-item in a tight loop.
- **Tracing returns a NoOp span when off, never nil**, so call sites never nil-check. Gate the span on a runtime flag; make the tracer an interface so tests inject a no-op backend.

## Database

Code in `references/conventions.md`.

- **Ent ORM for backend projects** — typed queries, generated code, clean schema. Repository implementations live in `internal/repository/ent/`; map `ent.IsNotFound` to the domain's `ErrNotFound`.
- **Specialized store behind the same interface** (ClickHouse, raw SQL) for analytics / high-volume where Ent is too slow.
- **Migrations:** Ent built-in (`WithDropColumn`/`WithDropIndex`) in dev, versioned via Atlas in prod.
- **Raw SQL for CLIs only** — thin `type DB struct { conn *sql.DB }`, no ORM. SQLite pragmas on every `Open()`: `journal_mode=WAL`, `synchronous=NORMAL`, `foreign_keys=ON`.

## Concurrency

Go's core strength, and where the subtle bugs live. Rules below are non-negotiable; templates (worker pools, fan-out variants, async loaders, per-call timeouts, graceful shutdown) are in `references/concurrency.md`.

### Picking the primitive

| Need | Use |
|------|-----|
| Small fixed set of calls, all must succeed, abort on first error | `errgroup.WithContext` |
| Fan-out where one failure must NOT fail the request (partial/degraded) | `sync.WaitGroup` + buffered result channel |
| N items, cap simultaneous goroutines at K | buffered channel as a semaphore (`make(chan struct{}, K)`) |
| Long-lived stream of jobs, stable goroutine count | fixed worker pool (jobs channel + workers ranging over it) |
| Fire one call early, await later | typed async loader (`LoadAsync`/`Await`) or `func() (<-chan T, <-chan error)` |
| Trivial one-shot "future", no error | generic `Async[T any](fn func() T) <-chan T` |
| Collapse duplicate concurrent loads of one key | `golang.org/x/sync/singleflight` |

Default to `errgroup` only when all-or-nothing is the real contract. Most request fan-outs want partial degradation — use WaitGroup + buffered channel.

### Non-negotiable rules

- **Every goroutine recovers its own panic** — `defer recoverPanic(ctx)` as the first deferred call in any `go func()`. An unrecovered panic in a goroutine crashes the whole process.
- **Buffer result channels to the number of senders** (`make(chan T, len(items))`). Undersized → senders park → `wg.Wait()` never returns → deadlock.
- **Close after `Wait`, never before**, then `range` to drain. Closing early panics on the next send.
- **Always `defer cancel()`** on the line after `context.WithTimeout`/`WithCancel` — skipping it leaks the timer goroutine.
- **Buffer to cap 1** any "goroutine + `select` on `ctx.Done()`" timeout channel, so a late goroutine has somewhere to write instead of leaking.
- **Pass loop variables as explicit args** to goroutines (`go func(i int){...}(i)`).
- **Defers run LIFO** — put `defer recoverPanic(ctx)` before `defer close(ch)` so recover fires first and the channel still closes on panic.

### Gotchas

- `errgroup.Group{}` without `WithContext` collects the first error but does NOT cancel siblings — it waits for all. Use `WithContext` and thread the derived ctx in for early cancellation.
- A request `ctx` carries a deadline; fire-and-forget work that must outlive the request needs a **detached context** (copy values, drop the deadline). Never hand a request ctx to a goroutine that must finish after the response returns.
- Never store mutable types (maps, slices) in `context.Value` and read them across goroutines — data race. Context is for immutable request identity only.
- Background fire-and-forget pools need a "pool healthy" sentinel: if a worker dies, stop accepting pushes, or tasks pile into a queue no one drains.

### Graceful lifecycle

Parallelize independent startup with `sync.WaitGroup` in waves — infrastructure first, then dependent clients — each goroutine recovering its own panic. `signal.NotifyContext` turns SIGINT/SIGTERM into a cancelled context. On shutdown, **stop accepting new work before tearing down its dependencies** (reverse of startup). Don't use `errgroup` for startup — it cancels siblings on the first init error.

## Caching & Resilience

Code in `references/concurrency.md` (§11–12).

- **Two-tier cache** (in-process L1 + distributed L2) on hot read paths. L1 is instance-local — only for data tolerant of a few seconds' cross-instance staleness; keep L1 TTL well below L2's.
- **Always jitter cache TTLs at write time** (`base + rand(jitter)`). Keys written together expire together and stampede the origin otherwise.
- **Coalesce duplicate concurrent loads** with `singleflight` — one in-flight load per key, the rest share the result. Don't hand-roll a lock map.
- **Rate limiters fail open.** In-process: `golang.org/x/time/rate`. Cross-replica: a shared atomic check that *allows* the request when its store is unavailable — a limiter must never be a hard dependency.
- **Split total vs per-attempt timeout** on retried calls — a total-only budget makes retries useless. Gate retries behind a runtime flag and never auto-retry non-idempotent operations.
- **Graceful degradation:** on critical read paths, snapshot the last-known-good response (idempotency-key-guarded, jittered TTL, written on a detached context) and serve it when the dependency is down.

## Idioms

Decomposition and data-shaping patterns. Code-shape sketches in `references/idioms.md`; data-structure/algorithm idioms (fuzzy match scoring, bitmask trie, composite-key dedup, fixed-slot interleave, weighted scoring, per-type quota) in `references/algorithms.md`.

- **Split decide-vs-do.** A processor that must both decide whether it runs and do the work splits into a `Validator` (all eligibility, shared flag check in an embedded base) and a `Modifier` (the transform, never checks a flag). Write `Validate` as a flat negative-guard ladder, not a long `&&` chain.
- **Pure logic, flags at the edge.** Promote magic constants to constructor params, and extract read-only receiver fields into explicit function params, instead of reading config or closing over state deep inside a method; the controller reads the flag once and threads it in. The method becomes a pure, goroutine-safe, table-testable function.
- **Unify branching, don't duplicate it.** Collapse a forest of boolean-flag branches into one dispatch with a **control-params struct** (named fields beat positional bools); for a stable loop over varied item types, resolve a typed **builder per type via a strategy** so adding a type never touches the loop.
- **Always-write result assembly.** When a function builds a response in steps and must record timing/fields on every return path, assign them in a `defer` that captures the result by reference and takes `time.Now()` as a value argument.
- **Nil-receiver-safe accessors.** On a request/context struct threaded as a pointer through deep chains, make getters nil-safe (`if r == nil { return zero }`) so callers never guard; use a distinct sentinel (`-1`, not `0`) where the zero value is itself valid.
- **Partition / dedup / prune with membership sets.** Rearrange by a computed threshold via a `map[id]bool` (`kept[:cut] + low + kept[cut:]`, O(n), order-preserving); dedup typed records on a separator-joined composite key; prune an allowlist at the call site so the callee stays general.

## Testing

Code in `references/conventions.md`.

- **Standard library `testing`, table-driven with subtests.** White-box (same package, not `_test` suffix).
- **`t.Fatalf` for setup failures, `t.Errorf` for assertions.** No helper libraries that hide the assertion logic.
- **Helpers use `t.Helper()`, `t.TempDir()`, `t.Cleanup()`.**
- **Backend service tests:** testify/suite with a `BaseServiceTestSuite` wiring in-memory repositories (one per repository interface, in `internal/testutil/`). Each test gets a fresh context + cleared stores via `SetupTest`; no real DB.
- **Integration tests use a real database** — insert then query; don't mock the thing under test.

## Config

Code in `references/conventions.md`.

- **Single `Configuration` struct**, nested structs per concern.
- **Viper + godotenv**, load order: `.env` → YAML → env vars override.
- **Build-time vars** (version, commit, buildTime) injected via ldflags.

### Runtime Config & Feature Flags

Distinct from the static struct above: tunables/flags read from a flag store **at call time** (ctx-scoped), so they change behavior on the next request with no redeploy. Patterns in `references/services.md` (§9–12).

- **Always supply a safe default inline at the read.** A missing key returns the zero value — and 0 is dangerous for a batch size or TTL. `if n <= 0 { n = <conservative default> }` at the read site, not a distant init.
- **Kill switches return a sentinel error**, checked at the top of the entry function. Name them consistently (`<subsystem>.kill_switch`).
- **Gate sub-params behind a master toggle** (`feature.<name>.enabled` then `feature.<name>.<param>`).
- **Never gate correctness-critical logic on a flag** — flags are for rollout and kill switches, not right-vs-wrong answers. The store being unavailable must not break the request.

## Comments

Sparse — code explains itself through naming. Comment only when the WHY is non-obvious (a hidden constraint, a workaround, surprising behavior):

```go
// Bone-in weight includes ~30% bone mass — adjust for edible portion
edible := weight * 0.7
```

Every exported symbol gets a one-line doc comment. No file headers, no "Step 1/Step 2" process comments, no comments restating what the code does.

## Preferred Stack

| Concern | Backend | CLI |
|---------|---------|-----|
| HTTP / RPC | Gin; gRPC + chained interceptors (recovery-first) | N/A |
| Database | Ent ORM (Postgres) | raw SQL, modernc.org/sqlite |
| Config | Viper + godotenv; ctx-scoped runtime flag store | Koanf |
| DI | Uber Fx | manual |
| Testing | testify/suite + in-memory repos | stdlib testing |
| Concurrency | errgroup, x/sync/semaphore, singleflight, stdlib sync | stdlib sync |
| Caching | in-process L1 + Redis L2, TTL jitter | N/A |
| Rate limiting | x/time/rate (in-proc); shared-store fail-open (cross-replica) | N/A |
| Observability | context-bound logger, typed metrics (statsd-style), tracer interface | N/A |
| Workflows | Temporal | N/A |
| Auth | OAuth2 + PKCE | zalando/go-keyring |
| Logging | structured logger (zap/zerolog) | fatih/color to stderr |
| CLI framework | N/A | Cobra |

## Anti-Patterns

Deliberately avoided across all of Siddhartha's projects:

- Global singletons or package-level mutable state
- `interface{}` / `any` when a concrete type works
- `I` prefix on interfaces (`IExpenseService` — just `ExpenseService`)
- `panic` in production code
- Hand-written SQL in backend services (use Ent)
- Logging to stdout in library/service code (use a structured logger; let the caller decide output)
- Test helpers that hide assertions behind abstraction layers
- Mocking the database in tests meant to test database behavior
- Spawning a goroutine without `defer recoverPanic(ctx)` — one panic crashes the process
- Unbuffered or undersized result channels in a fan-out (senders park, `Wait` deadlocks)
- Closing a channel before all senders have finished (panic on next send)
- Forgetting `defer cancel()` after `context.WithTimeout` (timer goroutine leak)
- Plain `errgroup` when partial results are required — it waits-all, and `WithContext` aborts siblings on first error
- Mutable types (maps/slices) in `context.Value` read across goroutines (data race)
- Bare string `context.Value` keys (collisions) — use an unexported typed key
- Rate limiters that fail closed — the limiter becomes a hard dependency on its own store
- gRPC panic-recovery interceptor without named returns (the panic returns a fake `(nil, nil)` success)
- Interceptor chain ordered arbitrarily — recovery not outermost, or config loaded after its readers
- `metadata.NewOutgoingContext` in a client interceptor (clobbers other interceptors' keys) — use `AppendToOutgoingContext`
- Unbounded/high-cardinality metric tag values (raw ids, URLs) — bucket before tagging
- `defer func(){ ...time.Now() }()` for latency timing (measures function return, not entry)
- Reading a runtime flag without a safe default for the zero-value case
- Gating correctness-critical logic on a feature flag (flags are for rollout/kill, not right-vs-wrong)
- Returning a nil span or nil logger that forces nil-checks at call sites — return a NoOp instead
