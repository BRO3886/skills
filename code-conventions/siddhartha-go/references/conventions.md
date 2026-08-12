# Foundational Conventions — Code Examples

Detailed rules and code examples for project structure, architecture, errors, API, HTTP, database, testing, configuration, comments, and stack choices. Read only the sections needed for the current task. The examples use a simple expense/group domain for illustration.

## Contents

- [Project structure and naming](#project-structure-and-naming)
- [Entry point](#entry-point)
- [Service and repository pattern](#service--repository-pattern)
- [Dependency injection](#dependency-injection-uber-fx)
- [Error handling](#error-handling)
- [API design](#api-design)
- [HTTP layer](#http-layer-gin)
- [Database](#database-ent)
- [Testing](#testing)
- [Configuration](#config)
- [Comments](#comments)
- [Preferred stack](#preferred-stack)

---

## Project structure and naming

Keep application code inside `internal/`. Root-level Go code is limited to `cmd/` entry points and an optional `embed.go`.

```text
cmd/<app>/main.go
internal/
  api/v1/
  api/dto/
  api/router.go
  domain/<entity>/
  service/<entity>.go
  repository/<store>/
  config/config.go
  errors/errors.go
```

- Packages are short, lowercase, singular words such as `api`, `config`, `service`, and `dto`.
- Types and exported functions use PascalCase. Unexported identifiers use camelCase. Variables stay short and contextual.
- Enums include a named type, constants, a `String()` method, and a `Parse*()` constructor.
- Incoming conversions use `from*`; outgoing conversions use `to*`.
- Interfaces have concept names without an `I` prefix. Implementations are unexported when callers only need the interface.
- Files use lowercase names and underscores for multiple words. Keep one domain entity per file in each layer.

---

## Entry point

`main.go` stays under ~30 lines: set build vars, load config, start the app. No business logic, routing, or middleware setup here.

```go
func main() {
    cfg, err := config.Load()
    if err != nil {
        log.Fatalf("loading config: %v", err)
    }
    if err := server.Run(cfg); err != nil {
        log.Fatalf("server: %v", err)
    }
}
```

---

## Service / Repository pattern

The repository interface belongs to the **domain** — it describes the storage operations the domain needs, not how they're implemented.

```go
// internal/domain/expense/repository.go
package expense

type Repository interface {
    Create(ctx context.Context, input CreateInput) (*Expense, error)
    GetByID(ctx context.Context, id string) (*Expense, error)
    List(ctx context.Context, filter ListFilter) ([]*Expense, error)
}
```

```go
// internal/domain/expense/model.go
package expense

type Expense struct {
    ID          string
    GroupID     string
    PaidBy      string
    Amount      float64
    SplitType   SplitType
    Description string
    CreatedAt   time.Time
}

type CreateInput struct { /* ... */ }
type ListFilter struct { /* ... */ }
```

```go
// internal/service/expense.go
package service

type ExpenseService interface {
    CreateExpense(ctx context.Context, input expense.CreateInput) (*expense.Expense, error)
    GetExpense(ctx context.Context, id string) (*expense.Expense, error)
    SettleUp(ctx context.Context, groupID string, between [2]string) error
}

type expenseService struct {
    repo expense.Repository
}

func NewExpenseService(repo expense.Repository) ExpenseService {
    return &expenseService{repo: repo}
}
```

The service is a public interface with an unexported struct; the constructor returns the interface. Tests swap in a fake repository without touching service code.

---

## Dependency injection (Uber Fx)

Every constructor is registered with `fx.Provide`. When a struct has many deps, use `fx.In` parameter objects.

```go
type RepositoryParams struct {
    fx.In
    Logger    *logger.Logger
    EntClient *ent.Client
    Cache     cache.Cache
}

func NewExpenseRepository(p RepositoryParams) expense.Repository {
    return entRepo.NewExpenseRepository(p.EntClient, p.Logger, p.Cache)
}
```

Wire everything in `main.go`:

```go
fx.New(
    fx.Provide(
        config.Load,
        postgres.NewClient,
        repository.NewExpenseRepository,
        service.NewExpenseService,
        api.NewExpenseHandler,
    ),
    fx.Invoke(server.Start),
)
```

Lifecycle hooks for startup/shutdown:

```go
fx.Lifecycle.OnStart(func(ctx context.Context) error { return srv.ListenAndServe() })
fx.Lifecycle.OnStop(func(ctx context.Context) error { return srv.Shutdown(ctx) })
```

**Deployment mode switch** — one binary, multiple roles:

```go
switch cfg.Mode {
case ModeAPI:            // HTTP server only
case ModeTemporalWorker: // Temporal worker only
case ModeConsumer:       // queue consumer only
case ModeLocal:          // all of the above in one process (dev)
}
```

---

## Error handling

Wrap every error with context about the operation:

```go
func (s *expenseService) GetExpense(ctx context.Context, id string) (*expense.Expense, error) {
    e, err := s.repo.GetByID(ctx, id)
    if err != nil {
        return nil, fmt.Errorf("getting expense %s: %w", id, err)
    }
    return e, nil
}
```

**Error builder** — sentinel errors plus a fluent builder that separates internal detail from a user-facing hint:

```go
// internal/errors/errors.go
var (
    ErrNotFound   = newCode(ErrCodeNotFound, "resource not found")
    ErrValidation = newCode(ErrCodeValidation, "validation error")
    ErrForbidden  = newCode(ErrCodeForbidden, "forbidden")
)

ierr.NewError("split percentages sum to 97, not 100"). // internal message (logs)
    WithHint("Split percentages must add up to exactly 100"). // user-facing (API)
    Mark(ierr.ErrValidation) // wraps a sentinel so errors.Is works
```

Check with `errors.Is(err, ierr.ErrNotFound)`. Internal messages can be detailed; user-facing hints should be helpful.

**Centralized HTTP error middleware** maps sentinels to status codes — handlers never write error status codes themselves:

```go
func ErrorHandler() gin.HandlerFunc {
    return func(c *gin.Context) {
        c.Next()
        if len(c.Errors) == 0 {
            return
        }
        err := c.Errors.Last().Err
        c.JSON(ierr.HTTPStatusFromErr(err), gin.H{"error": ierr.GetHint(err)})
    }
}
```

Handlers just call `c.Error(err)` and return.

**Best-effort operations** do not fail the primary operation. Record an operationally meaningful failure through a bounded log or metric. Silence it only when the failure is intentionally unobservable:

```go
if err := cache.Set(key, val); err != nil {
    metrics.CacheWriteFailure(ctx, "expense")
}
```

---

## API design

**Named input structs** for any operation with 3+ parameters:

```go
type CreateExpenseInput struct {
    GroupID     string    `json:"group_id" binding:"required"`
    PaidBy      string    `json:"paid_by" binding:"required"`
    Amount      float64   `json:"amount" binding:"required,gt=0"`
    SplitType   SplitType `json:"split_type" binding:"required"`
    Description string    `json:"description"`
    Splits      []Split   `json:"splits" binding:"required,min=1"`
}
```

**Partial updates** — pointer fields, nil means "don't change":

```go
type UpdateExpenseInput struct {
    Description *string  `json:"description,omitempty"`
    Amount      *float64 `json:"amount,omitempty"`
}
```

Check `cmd.Flags().Changed("field")` (CLI) or nil (API) before applying.

**Filtering** — functional options for complex queries:

```go
type ListOption func(*listOptions)

func WithGroup(id string) ListOption   { return func(o *listOptions) { o.groupID = id } }
func WithSettled(s bool) ListOption     { return func(o *listOptions) { o.settled = &s } }
```

---

## HTTP layer (Gin)

Always `gin.New()`, never `gin.Default()` — control the middleware stack explicitly. Order: `RequestID → Logging → CORS → Auth → ErrorHandler`.

Expose the service health check at `GET /health`. Do not use `/healthz`.

**Typed context keys** — set in auth middleware, read via typed getters (never raw `ctx.Value`):

```go
type ctxKey string
const (
    CtxUserID  ctxKey = "user_id"
    CtxGroupID ctxKey = "group_id"
)

func GetUserID(ctx context.Context) string {
    v, _ := ctx.Value(CtxUserID).(string)
    return v
}
```

**DTOs** live in `internal/api/dto/`, separate from domain models; the handler converts:

```go
func (h *ExpenseHandler) Create(c *gin.Context) {
    var req dto.CreateExpenseRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.Error(ierr.NewValidation(err.Error()))
        return
    }
    result, err := h.svc.CreateExpense(c.Request.Context(), req.ToDomain())
    if err != nil {
        c.Error(err)
        return
    }
    c.JSON(201, dto.FromExpense(result))
}
```

---

## Database (Ent)

Use [Ent](https://entgo.io/) for backend projects — typed queries, generated code, clean schema. Repository implementations live in `internal/repository/ent/`:

```go
type expenseRepository struct {
    client *ent.Client
    logger *logger.Logger
    cache  cache.Cache
}

func (r *expenseRepository) GetByID(ctx context.Context, id string) (*expense.Expense, error) {
    row, err := r.client.Expense.Get(ctx, id)
    if err != nil {
        if ent.IsNotFound(err) {
            return nil, expense.ErrNotFound
        }
        return nil, fmt.Errorf("querying expense %s: %w", id, err)
    }
    return fromEntExpense(row), nil
}
```

For analytics or high-volume event storage where Ent is too slow, use a specialized store (ClickHouse, raw SQL) behind the same repository interface. Migrations: Ent's built-in (`WithDropColumn`/`WithDropIndex`) in dev, versioned via Atlas in prod.

**Raw SQL for CLIs only** — a thin `type DB struct { conn *sql.DB }` wrapper, no ORM. SQLite pragmas on every `Open()`:

```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;
```

---

## Testing

Standard library `testing`. Table-driven with subtests, white-box (same package, not `_test` suffix). `t.Fatalf` for setup failures, `t.Errorf` for assertions. No helper libs that hide the assertion logic.

```go
func TestParseSplitType(t *testing.T) {
    tests := []struct {
        name  string
        input string
        want  SplitType
        err   bool
    }{
        {"equal", "equal", SplitEqual, false},
        {"invalid", "bogus", 0, true},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got, err := ParseSplitType(tt.input)
            if (err != nil) != tt.err {
                t.Fatalf("ParseSplitType(%q) error = %v, want error: %v", tt.input, err, tt.err)
            }
            if got != tt.want {
                t.Errorf("ParseSplitType(%q) = %v, want %v", tt.input, got, tt.want)
            }
        })
    }
}
```

Helpers use `t.Helper()`, `t.TempDir()`, `t.Cleanup()`:

```go
func testDB(t *testing.T) *sql.DB {
    t.Helper()
    db, err := sql.Open("sqlite", filepath.Join(t.TempDir(), "test.db"))
    if err != nil {
        t.Fatalf("opening test db: %v", err)
    }
    t.Cleanup(func() { db.Close() })
    return db
}
```

**Backend service tests** — testify/suite with a `BaseServiceTestSuite` wiring in-memory repositories. Every repository interface gets an in-memory impl in `internal/testutil/`:

```go
type BaseServiceTestSuite struct {
    suite.Suite
    ctx    context.Context
    stores Stores
}

type Stores struct {
    ExpenseRepo *InMemoryExpenseRepository
    GroupRepo   *InMemoryGroupRepository
}

func (s *BaseServiceTestSuite) SetupTest() {
    s.ctx = context.WithValue(context.Background(), types.CtxUserID, "test-user")
    s.stores = Stores{
        ExpenseRepo: NewInMemoryExpenseRepository(),
        GroupRepo:   NewInMemoryGroupRepository(),
    }
}
```

```go
type ExpenseTestSuite struct {
    testutil.BaseServiceTestSuite
    svc ExpenseService
}

func (s *ExpenseTestSuite) SetupTest() {
    s.BaseServiceTestSuite.SetupTest()
    s.svc = NewExpenseService(s.stores.ExpenseRepo, s.stores.GroupRepo)
}

func (s *ExpenseTestSuite) TestCreateExpense_ValidInput() {
    result, err := s.svc.CreateExpense(s.ctx, expense.CreateInput{ /* ... */ })
    s.NoError(err)
    s.Equal("dinner", result.Description)
}

func TestExpenseService(t *testing.T) { suite.Run(t, new(ExpenseTestSuite)) }
```

Each test gets a fresh context + cleared stores via `SetupTest`; no real database needed. Adding a service test is just embedding `BaseServiceTestSuite` and wiring the service. For real DB behavior (Ent queries, migrations, constraints), use a real database — insert then query, don't mock the thing under test.

---

## Config

Single `Configuration` struct, nested per concern:

```go
type Configuration struct {
    Server   ServerConfig   `mapstructure:"server"`
    Database DatabaseConfig `mapstructure:"database"`
    Auth     AuthConfig     `mapstructure:"auth"`
}
```

Load order (Viper + godotenv): `.env` first, then YAML, then env vars override.

```go
godotenv.Load(".env")
viper.SetConfigFile(fmt.Sprintf("configs/config.%s.yaml", env))
viper.AutomaticEnv()
```

Build-time vars via ldflags: `var ( version = "dev"; commit = "none"; buildTime = "unknown" )`.

---

## Comments

Comment only a hidden constraint, invariant, workaround, or surprising tradeoff. Do not add file headers, numbered process comments, or comments that restate the code. Every exported symbol still gets its normal one-line Go documentation comment.

---

## Preferred stack

| Concern | Backend | CLI |
| --- | --- | --- |
| HTTP / RPC | Gin; gRPC with dependency-ordered interceptors | N/A |
| Database | Ent with Postgres | `modernc.org/sqlite` through raw SQL |
| Static config | Viper and godotenv | Koanf |
| Dependency injection | Uber Fx | Manual construction |
| Testing | Standard library plus testify/suite and in-memory repositories | Standard library |
| Concurrency | `errgroup`, `x/sync/semaphore`, `singleflight`, and standard library sync | Standard library sync |
| Caching | In-process L1 plus Redis L2 with TTL jitter | N/A |
| Rate limiting | `x/time/rate`; shared-store checks fail open | N/A |
| Observability | Context-bound structured logger, typed metrics, tracer interface | N/A |
| Workflows | Temporal | N/A |
| Authentication | OAuth2 with PKCE | `zalando/go-keyring` |
| Logging | zap or zerolog | fatih/color to stderr |
| CLI framework | N/A | Cobra |
