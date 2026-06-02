# Code-Shape Idioms

Characteristic decomposition and data-shaping patterns — how a complex function gets structured into testable, pure pieces. Reach for these when building a processor/transformer/handler that has both an eligibility decision and a transformation, or when shaping/partitioning slices. Summarized in `SKILL.md`'s Idioms section.

---

## 1. Validator + Modifier split (decide vs do)

When a processor must both (a) decide whether it runs and (b) execute its logic, split those into two types: a **validator** that owns all eligibility, and a **modifier** that owns the transformation and assumes eligibility already passed. They become independently testable and mockable, and a shared flag check lives once in an embedded base.

```go
type Validator interface {
    Enabled(ctx context.Context) bool
    Validate(ctx context.Context) bool
}

type stageValidator struct {
    BaseValidator // embeds the shared kill-switch / flag check
    expOn      bool
    onTarget   bool
    sorted     bool
}

func NewStageValidator(expOn, onTarget, sorted bool) Validator {
    return stageValidator{expOn: expOn, onTarget: onTarget, sorted: sorted}
}

// Flat negative-guard ladder — each condition fails fast, one per line.
func (v stageValidator) Validate(ctx context.Context) bool {
    if !v.BaseValidator.Validate(ctx) { // shared gate FIRST
        return false
    }
    if !v.expOn {
        return false
    }
    if !v.onTarget {
        return false
    }
    if !v.sorted {
        return false
    }
    return true
}

// Modifier receives only what it needs; it never checks a flag.
type stageModifier struct {
    *BaseModifier
    percentile float64
    maxLen     int
}

func NewStageModifier(percentile float64, maxLen int) Modifier {
    return &stageModifier{BaseModifier: NewBaseModifier(), percentile: percentile, maxLen: maxLen}
}
```

Why: the validator answers "should I run?", the modifier never re-asks. Unit-test `Validate` with a table of booleans; unit-test `Modify` with any input, no flag mocking. The flat ladder diffs better than a long `&&` chain — each condition is one line. Gotcha: call the embedded `BaseValidator.Validate(ctx)` first, or a new subclass silently skips the kill switch.

---

## 2. Compute threshold → membership set → stable partition

To push everything below a computed cutoff to the bottom while preserving relative order within each tier: sort a work-window, compute the threshold at a percentile index (a single index calc, not a loop), mark losers into a `map[id]bool`, then rebuild as `kept[:cut] + demoted + kept[cut:]`.

```go
func partition(items []Item, percentile float64, maxLen int, cutoffDist float64) []Item {
    if len(items) == 0 {
        return items
    }
    window := items[:min(len(items), maxLen)]
    sort.SliceStable(window, func(i, j int) bool { return window[i].Score > window[j].Score })

    idx := int((percentile / 100) * float64(len(window)-1))
    threshold := window[idx].Score

    demote := make(map[int]bool, len(window))
    for _, it := range window {
        if it.Score < threshold && it.Distance > cutoffDist {
            demote[it.ID] = true
        }
    }

    kept := make([]Item, 0, len(items))
    low := make([]Item, 0, len(items))
    for _, it := range items {
        if demote[it.ID] {
            low = append(low, it)
        } else {
            kept = append(kept, it)
        }
    }
    cut := min(len(kept), maxLen)
    out := make([]Item, 0, len(items))
    out = append(out, kept[:cut]...)
    out = append(out, low...)
    out = append(out, kept[cut:]...)
    return out
}
```

Why: the membership set makes the rebuild O(n) regardless of how many were demoted; both passes are sequential appends, so relative order is preserved within each tier. Gotchas: `sort.SliceStable(window, ...)` mutates the underlying `items` up to `maxLen` — copy the window first if you need the original order. Guard the empty case before indexing `window[idx]`.

---

## 3. Chunk-and-merge with a single-call fast path

Calling a store/scoring service with a request that *might* exceed a size limit: keep the single-call fast path for the common case, chunk only when needed, and collect partial results so one failed batch doesn't abort the whole call.

```go
func fetch(ctx context.Context, req Request, batchSize int) (Response, error) {
    if len(req) == 0 {
        return Response{}, nil // empty-input guard avoids a vacuous call
    }
    if len(req) <= batchSize {
        return client.Get(ctx, req) // fast path
    }
    out := Response{}
    var lastErr error
    for i, batch := range chunkify(req, batchSize) {
        resp, err := client.Get(ctx, batch)
        if err != nil {
            log.ErrorfWithContext(ctx, "batch %d: %v", i, err)
            lastErr = err
            continue // collect what we can
        }
        for k, v := range resp {
            out[k] = v
        }
    }
    return out, lastErr
}
```

Why: common case pays no chunking overhead; partial results beat a full abort on one bad batch; `batchSize` is a parameter so tests control it. Gotcha: this returns the *last* batch error — wrap in a multi-error if the caller needs all of them. (For concurrent batches see `concurrency.md` §3 — don't fan these out and also accumulate sequentially, pick one.)

---

## 4. Deferred result-assembly with a captured pointer

When a function builds its response in steps and must always write timing/output fields — even on an early error return — assign them in a `defer` that captures the result by reference and takes `time.Now()` as a value argument.

```go
func (m *stageModifier) Modify(ctx context.Context, items []Item) (resp Response, err error) {
    var final []Item
    defer func(start time.Time) { // start captured at defer-registration time
        resp.ElapsedMs = time.Since(start).Milliseconds()
        resp.Items = final // always written, on every return path
    }(time.Now())

    if m.maxLen == 0 {
        return resp, nil // defer still fires; final is a nil slice → safe
    }
    final = m.transform(ctx, items)
    return resp, nil
}
```

Why: timing is wall-clock-accurate from entry regardless of when the defer fires, and the caller never receives an inconsistent struct (a non-nil error alongside half-written fields). Gotchas: the captured variable must be the named return or a local the closure assigns to from the outer scope — reassigning a fresh variable inside the closure gives you the zero value. The `(time.Time)` argument is evaluated at defer registration (intentional), which reads like a bug if you're not expecting it.

---

## 5. Promote a magic constant to a constructor parameter

When a hardcoded constant needs to vary across callers (tests, experiments), thread it through the constructor rather than reaching for a config read deep inside the method. The method stays a pure function of its fields; the edge (controller) is the single place that reads the flag.

```go
// Before: buried constant, untestable boundary
const maxLen = 250
func (m *modifier) Modify(items []Item) Response { w := items[:min(len(items), maxLen)]; /* ... */ }

// After: caller supplies it; method is pure
func NewModifier(percentile float64, maxLen int) Modifier { // maxLen promoted
    return &modifier{percentile: percentile, maxLen: maxLen}
}
func (m *modifier) Modify(items []Item) Response { w := items[:min(len(items), m.maxLen)]; /* ... */ }
// controller reads the flag once: NewModifier(p, rconfig.GetInt(ctx, "feature.x.max_len"))
```

Why: no hidden config reads inside the logic, so tests pass boundary values (0 to hit the early-return guard) without mocking a config layer; flags are read at the edge. Gotcha: this grows constructors with many positional args — fine to ~5-6 with clear names; past that, switch to a config struct (not functional options for plain data).

---

## 6. Strategy + typed-builder hierarchy for a stable loop over varied item types

When a fixed loop (iterate items, produce output per item) must build each item differently by type, and you want to add new types without touching the loop. A `Strategy` resolves a typed `Builder` per item; each builder is a zero-value struct implementing a one-method interface.

```go
type Strategy interface {
    elementsFor(ctx context.Context, items []Item) []Element
    builderFor(ctx context.Context, e Element) (Builder, error)
}

type Builder interface {
    build(ctx context.Context, e Element) ([]*Output, error)
}

type headerBuilder struct{} // zero-value, no shared state
func (headerBuilder) build(_ context.Context, e Element) ([]*Output, error) { /* ... */ }

func (d *Renderer) Render(ctx context.Context) []*Output {
    var out []*Output
    skipped := 0
    for _, e := range d.strategy.elementsFor(ctx, d.items) {
        e.rank -= skipped // keep rank contiguous when items are skipped
        b, err := d.strategy.builderFor(ctx, e)
        if err != nil { skipped++; continue }
        cards, err := b.build(ctx, e)
        if err != nil { skipped++; continue }
        out = append(out, cards...)
    }
    return out
}
```

Why: the loop is stable; a new type is a new builder struct + one case in the strategy. Skipped items don't corrupt rank because it's corrected in-loop. Zero-value builders mean no per-render allocation. Gotcha: the strategy switch becomes a god-list past ~15 types — move to a `map[type]Builder` registry initialised at startup.

---

## 7. Control-params struct to unify boolean-flag branches

When a function is called from several branches that each differ in a handful of booleans, bundle the variation into an explicit struct instead of positional bool args or duplicated call sites.

```go
type buildParams struct {
    Indexed  bool
    Scoped   bool
    OnlyX    bool
    ScopeID  int
}

func build(ctx context.Context, p *buildParams) string { /* one dispatch point */ }

// call sites are self-documenting — named fields, not positional bools:
clause := build(ctx, &buildParams{Indexed: true, Scoped: true, ScopeID: id})
```

Why: call sites read as `{Indexed: true, Scoped: true}` instead of `build(ctx, true, false, true, ...)`; adding a flag is a one-field change with no signature churn. Gotcha: past ~6 fields it's a smell the function is doing too much — split it.

---

## 8. Extract closed-over state into explicit params (method → pure function)

When a method only *reads* a few receiver fields (doesn't mutate state), pull those fields out as parameters. The function becomes testable in isolation and safe to call from a goroutine without capturing a pointer to mutable shared state.

```go
// Before: closes over rc.request — needs the whole receiver to test
func (rc *curator) withinRadius(items []Item) []Item { r := rc.request.Radius(); /* ... */ }

// After: pure, explicit inputs
func withinRadius(items []Item, center Coord, radius float64) []Item { /* ... */ }
// call: withinRadius(items, rc.request.Center(), rc.request.Radius())
```

Why: pairs with "pure logic, flags at the edge" — the logic is a pure function of its inputs, tested with synthetic values, and goroutine-safe (no captured mutable receiver). Gotcha: if you'd pass 8 fields from the same struct, the method form is probably clearer — don't over-extract.

---

## 9. Nil-receiver-safe accessors with a sentinel

On a request/context struct threaded as a pointer through a deep call chain, make every getter nil-safe so callers never guard before a read. Use a distinct sentinel (not the zero value) where zero is itself valid.

```go
func (r *Req) Query() string { if r == nil { return "" }; return r.query }
func (r *Req) CityID() int   { if r == nil { return -1 }; return r.cityID } // -1, not 0 — 0 is a valid id
func (r *Req) Filtered() bool { return r != nil && r.filtered }
func (r *Req) Set(k, v string) { if r == nil { return }; r.meta[k] = v } // setters no-op on nil
```

Why: eliminates a whole class of nil-pointer panics in deep chains; private fields force all access through these methods, giving one place to add logging/metrics later. The `-1` sentinel surfaces "unknown id" bugs that a silent `0` would hide. Gotchas: nil-receiver *setters* silently swallow writes — fine, but log on nil-set during development to catch unexpected nil receivers; it's a lot of boilerplate, so codegen it past ~50 fields. (A team-wide idiom — it showed up independently across several authors.)

---

## 10. Prune the allowlist at the call site

When a caller holds a broad allowlist and must constrain it by runtime context, do the subtraction at the call site so the callee stays general and context-unaware.

```go
allowed := req.AllowedTypes()
if !req.SecondaryMode() {
    allowed = setDifference(allowed, []string{"premium"})
}
if req.StrictFilter() {
    allowed = setDifference(allowed, []string{"broad"})
}
apply(ctx, allowed) // callee receives a clean, already-trimmed list

func setDifference(all, remove []string) []string {
    rm := make(map[string]struct{}, len(remove))
    for _, v := range remove { rm[v] = struct{}{} }
    out := all[:0:0]
    for _, v := range all {
        if _, drop := rm[v]; !drop { out = append(out, v) }
    }
    return out
}
```

Why: the callee stays testable with arbitrary lists; the caller is explicit about what it removes and why. Gotcha: if the same removal recurs across many callers, promote it to a method on the request object instead of repeating it.
