---
name: siddhartha-go
description: "Siddhartha's Go backend coding conventions and architecture patterns. Use when writing Go backend code, designing APIs, setting up new Go services, or making architecture decisions in Go projects. Also use when reviewing Go PRs, scaffolding new packages, or when someone asks about project structure conventions. Ensures consistency between Siddhartha and Gagan on Settld and any shared Go backend work."
---

# Siddhartha's Go Backend Style Guide

This guide encodes the coding style, architecture patterns, and conventions extracted from Siddhartha's production Go projects (rem, gtasks, healthsync, go-eventkit, voice-agent, blay-tui, flexprice). Follow these patterns for all Go backend work on Settld and shared projects.

The goal is consistency between collaborators. These patterns come from production Go systems built at scale — billing platforms, CLI tools, voice agents, TUI clients. When in doubt, follow the conventions in this guide.

## Project Structure

```
cmd/<app>/main.go           # thin entry point — set build vars, call Execute() or start server
internal/
  api/
    v1/                     # HTTP handlers, one file per domain entity
    dto/                    # request/response types (separate from domain models)
    router.go               # all route registration in one file
  domain/
    <entity>/
      model.go              # domain struct
      repository.go         # repository interface (lives WITH the model, not with the impl)
  service/
    <entity>.go             # business logic — takes repository interface, returns service interface
  repository/
    postgres/               # or sqlite/, etc. — implements domain repository interfaces
      <entity>.go
  config/
    config.go               # single Configuration struct, env-specific YAML
  errors/
    errors.go               # sentinel errors + builder (for larger projects)
```

The `internal/` boundary is load-bearing — everything goes inside it. The only thing outside `internal/` is `cmd/` and maybe a root `embed.go`.

### Entry Point

`main.go` should be under 30 lines. It sets build-time variables, loads config, and starts the app. No business logic, no routing, no middleware setup.

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

## Naming

### Packages
Short, lowercase, single word. No hyphens, no underscores, no plurals.

Good: `api`, `config`, `service`, `storage`, `dto`
Bad: `services`, `api-handlers`, `expense_service`

### Types and Functions
- Types: `PascalCase` — `ExpenseService`, `QueryParams`, `SplitType`
- Exported functions: `PascalCase` — `NewExpenseService`, `ParsePriority`
- Unexported functions: `camelCase` — `parseDate`, `buildQuery`, `fromDBModel`
- Variables: `camelCase`, short and contextual — `db`, `cfg`, `rows`, `rec`, `tx`

### Enums
Always a named type with iota, a `String()` method, and a `Parse*()` function:

```go
type SplitType int

const (
    SplitEqual SplitType = iota
    SplitExact
    SplitPercent
)

func (s SplitType) String() string { ... }
func ParseSplitType(s string) (SplitType, error) { ... }
```

### Boundary Translation
Use `from*` for incoming conversions and `to*` for outgoing:

```go
func fromDBExpense(row *ent.Expense) *expense.Expense { ... }
func toDBCreateInput(e *expense.CreateInput) *ent.ExpenseCreate { ... }
```

### Interfaces
No `I` prefix. The interface name is the concept; the struct is the implementation detail:

```go
type ExpenseService interface { ... }   // not IExpenseService
type expenseService struct { ... }      // unexported struct
```

### Files
Lowercase. Underscores for multi-word (`huh_helpers.go`, `model_test.go`). One file per domain entity in handler/service/repository layers.

## Service/Repository Pattern

This is the core architecture. The repository interface belongs to the domain — it describes what storage operations the domain needs, not how they're implemented.

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

type CreateInput struct { ... }
type ListFilter struct { ... }
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

The service is a public interface with an unexported struct. The constructor returns the interface. This lets tests swap in a fake repository without touching the service code.

### Dependency Injection

Use Uber Fx. Every constructor is registered with `fx.Provide`. When a struct has many deps, use `fx.In` parameter objects:

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

Fx lifecycle hooks for startup/shutdown:

```go
fx.Lifecycle.OnStart(func(ctx context.Context) error { return srv.ListenAndServe() })
fx.Lifecycle.OnStop(func(ctx context.Context) error { return srv.Shutdown(ctx) })
```

### Deployment Mode Switching

For services that run multiple roles (API, worker, consumer), use a mode switch at startup — same binary, different behavior:

```go
switch cfg.Mode {
case ModeAPI:             // HTTP server only
case ModeTemporalWorker:  // Temporal worker only
case ModeConsumer:         // Kafka consumer only
case ModeLocal:           // all of the above in one process (dev mode)
}
```

## Error Handling

### Wrapping
Every error gets context about what operation failed:

```go
func (s *expenseService) GetExpense(ctx context.Context, id string) (*expense.Expense, error) {
    e, err := s.repo.GetByID(ctx, id)
    if err != nil {
        return nil, fmt.Errorf("getting expense %s: %w", id, err)
    }
    return e, nil
}
```

### Error Builder Pattern

Build an `internal/errors/` package with sentinel errors + a fluent builder that separates internal messages from user-facing hints:

```go
// internal/errors/errors.go
var (
    ErrNotFound   = new(ErrCodeNotFound, "resource not found")
    ErrValidation = new(ErrCodeValidation, "validation error")
    ErrForbidden  = new(ErrCodeForbidden, "forbidden")
)

// Fluent builder — Mark wraps with a sentinel so errors.Is works
ierr.NewError("split percentages sum to 97, not 100").
    WithHint("Split percentages must add up to exactly 100").
    Mark(ierr.ErrValidation)
```

`WithHint` is the user-facing message (goes to the API response). The raw error message is for internal logs. This separation matters — internal errors can be detailed, user-facing ones should be helpful.

Check with `errors.Is(err, ierr.ErrNotFound)`.

### HTTP Error Mapping

One centralized error middleware maps sentinels to HTTP status codes. Handlers never write status codes for errors:

```go
func ErrorHandler() gin.HandlerFunc {
    return func(c *gin.Context) {
        c.Next()
        if len(c.Errors) == 0 { return }
        err := c.Errors.Last().Err
        status := ierr.HTTPStatusFromErr(err) // walks error chain against statusCodeMap
        hint := ierr.GetHint(err)             // extracts user-facing message
        c.JSON(status, gin.H{"error": hint})
    }
}
```

Handlers call `c.Error(err)` and return. That's it.

### Best-Effort Operations
Cache writes, background update checks, and non-critical side effects silently swallow errors:

```go
if err := cache.Set(key, val); err != nil {
    return // silently fail — cache is best-effort
}
```

## API Design

### Input Structs
Named structs for any operation with 3+ parameters:

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

### Partial Updates
Pointer fields — nil means "don't change this field":

```go
type UpdateExpenseInput struct {
    Description *string  `json:"description,omitempty"`
    Amount      *float64 `json:"amount,omitempty"`
}
```

In the handler, check `cmd.Flags().Changed("field")` (CLI) or check for nil (API) before applying.

### Filtering
Functional options for complex queries:

```go
type ListOption func(*listOptions)

func WithGroup(id string) ListOption {
    return func(o *listOptions) { o.groupID = id }
}

func WithSettled(settled bool) ListOption {
    return func(o *listOptions) { o.settled = &settled }
}
```

## HTTP Layer

### Framework
Gin. Always `gin.New()`, not `gin.Default()` — control your middleware stack explicitly.

### Middleware Order
```
RequestID → Logging → CORS → Auth → ErrorHandler
```

### Context Propagation
Auth middleware sets tenant/user into context with typed keys:

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

Downstream code calls the typed getter, never raw `ctx.Value`.

### DTOs
Request/response types live in `internal/api/dto/`, separate from domain models. The handler converts between them:

```go
func (h *ExpenseHandler) Create(c *gin.Context) {
    var req dto.CreateExpenseRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.Error(ierr.NewValidation(err.Error()))
        return
    }
    input := req.ToDomain()
    result, err := h.svc.CreateExpense(c.Request.Context(), input)
    if err != nil {
        c.Error(err)
        return
    }
    c.JSON(201, dto.FromExpense(result))
}
```

## Database

### ORM: Ent

Use [Ent](https://entgo.io/) for all backend projects. It gives you typed queries, generated code, and a clean schema definition. Repository implementations live in `internal/repository/ent/`:

```go
// internal/repository/ent/expense.go
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

For analytics or high-volume event storage where Ent is too slow, use a specialized store (ClickHouse, raw SQL) alongside Ent — same repository interface, different implementation.

### Migrations
Use Ent's built-in migration with `WithDropColumn` and `WithDropIndex` for development. For production, use versioned migrations via Atlas.

### Raw SQL (CLIs only)
For CLI tools (not backend services), hand-written SQL with a thin `type DB struct { conn *sql.DB }` wrapper is fine. No ORM overhead for simple query-and-display tools.

SQLite pragmas on every `Open()`:
```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;
```

## Testing

### Style
Standard library `testing`. Table-driven with subtests:

```go
func TestParseSplitType(t *testing.T) {
    tests := []struct {
        name  string
        input string
        want  SplitType
        err   bool
    }{
        {"equal", "equal", SplitEqual, false},
        {"exact", "exact", SplitExact, false},
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

### Test Location
Same package (white-box). Not `_test` suffix packages.

### Helpers
Use `t.Helper()`, `t.TempDir()`, `t.Cleanup()`:

```go
func testDB(t *testing.T) *sql.DB {
    t.Helper()
    db, err := sql.Open("sqlite", filepath.Join(t.TempDir(), "test.db"))
    if err != nil { t.Fatalf("opening test db: %v", err) }
    t.Cleanup(func() { db.Close() })
    return db
}
```

### Assertions
`t.Fatalf` when the test can't continue (setup failures). `t.Errorf` when it can (assertion failures). No test helper libraries that hide the assertion logic.

### Backend Service Tests

Use testify/suite with a `BaseServiceTestSuite` that wires all in-memory repositories. Every repository interface gets an in-memory implementation in `internal/testutil/`:

```go
// internal/testutil/base_suite.go
type BaseServiceTestSuite struct {
    suite.Suite
    ctx    context.Context
    stores Stores
}

type Stores struct {
    ExpenseRepo *InMemoryExpenseRepository
    GroupRepo   *InMemoryGroupRepository
    UserRepo    *InMemoryUserRepository
}

func (s *BaseServiceTestSuite) SetupTest() {
    s.ctx = context.WithValue(context.Background(), types.CtxUserID, "test-user")
    s.stores = Stores{
        ExpenseRepo: NewInMemoryExpenseRepository(),
        GroupRepo:   NewInMemoryGroupRepository(),
        UserRepo:    NewInMemoryUserRepository(),
    }
}
```

```go
// internal/service/expense_test.go
type ExpenseTestSuite struct {
    testutil.BaseServiceTestSuite
    svc ExpenseService
}

func (s *ExpenseTestSuite) SetupTest() {
    s.BaseServiceTestSuite.SetupTest()
    s.svc = NewExpenseService(s.stores.ExpenseRepo, s.stores.GroupRepo)
}

func (s *ExpenseTestSuite) TestCreateExpense_ValidInput() {
    result, err := s.svc.CreateExpense(s.ctx, expense.CreateInput{...})
    s.NoError(err)
    s.Equal("dinner", result.Description)
}

func TestExpenseService(t *testing.T) {
    suite.Run(t, new(ExpenseTestSuite))
}
```

Each test gets a fresh context with tenant/user IDs and cleared stores via `SetupTest`. Tests never need a real database. This pattern scales — adding a new service test is just embedding `BaseServiceTestSuite` and wiring the service.

### Integration Tests
When testing actual DB behavior (Ent queries, migrations, constraints), use a real database. Insert then query — don't mock the thing you're testing.

## Config

### Structure
Single `Configuration` struct with nested structs per concern:

```go
type Configuration struct {
    Server   ServerConfig   `mapstructure:"server"`
    Database DatabaseConfig `mapstructure:"database"`
    Auth     AuthConfig     `mapstructure:"auth"`
}
```

### Loading
Viper + godotenv. `.env` loaded first, then YAML config, then env vars override:

```go
godotenv.Load(".env")
viper.SetConfigFile(fmt.Sprintf("configs/config.%s.yaml", env))
viper.AutomaticEnv()
```

### Build-Time Variables
Version, commit, build time injected via ldflags:

```go
var (
    version   = "dev"
    commit    = "none"
    buildTime = "unknown"
)
```

## Comments

Sparse. The code should explain itself through naming. Only comment when the WHY is non-obvious:

```go
// Bone-in weight includes ~30% bone mass — adjust for edible portion
edible := weight * 0.7
```

Every exported symbol gets a one-line doc comment. No file headers, no "Step 1/Step 2" process comments, no comments that describe what the code does (the code already does that).

## Preferred Stack

| Concern | Backend | CLI |
|---------|---------|-----|
| HTTP | Gin | N/A |
| Database | Ent ORM (Postgres) | raw SQL, modernc.org/sqlite |
| Config | Viper + godotenv | Koanf |
| DI | Uber Fx | manual |
| Testing | testify/suite + in-memory repos | stdlib testing |
| Workflows | Temporal | N/A |
| Auth | OAuth2 + PKCE | zalando/go-keyring |
| Logging | structured logger (zap/zerolog) | fatih/color to stderr |
| CLI framework | N/A | Cobra |

## Anti-Patterns

These are things that have been deliberately avoided across all of Siddhartha's projects:

- Global singletons or package-level mutable state
- `interface{}` / `any` when a concrete type works
- `I` prefix on interfaces (`IExpenseService` — just use `ExpenseService`)
- `panic` in production code
- Hand-written SQL in backend services (use Ent)
- Logging to stdout in library/service code (log to a structured logger, let the caller decide output)
- Test helpers that hide assertions behind abstraction layers
- Mocking the database in tests that are supposed to test database behavior
