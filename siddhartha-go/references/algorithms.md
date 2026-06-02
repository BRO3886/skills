# Data-Structure & Algorithm Idioms

Reusable algorithmic patterns for list-shaping, matching, dedup, and slot placement — the kind of thing that recurs in ranking, ranked-list assembly, and feed construction. Read this when you're scoring/matching strings, deduplicating typed records, interleaving streams, or partitioning by a runtime cap. Summarized in `SKILL.md`'s Idioms section.

All sketches use neutral names (`Item`, `Entry`, `candidate`, `score`).

---

## 1. Normalized fuzzy match score (Levenshtein, 0–1, with a trim flag)

A continuous similarity signal in `[0,1]` that degrades gracefully, instead of a binary match. The `trim` flag truncates the candidate to the query length first, so a short query scores 1.0 against an exact prefix instead of being penalised for the untyped suffix (type-ahead / prefix-completion matching).

```go
import lvs "github.com/texttheater/golang-levenshtein/levenshtein"

// score returns 1.0 for identical, 0.0 for completely different.
// trim=true → prefix-match mode (compare only the leading len(query) chars).
func score(query, candidate string, trim bool) float64 {
    query = normalize(query)        // lowercase, strip punctuation
    candidate = normalize(candidate)

    qr, cr := []rune(query), []rune(candidate)
    if trim && len(cr) > len(qr) {
        cr = cr[:len(qr)]           // rune-slice, NOT byte-slice
    }
    if len(cr) == 0 {
        return 0
    }
    opts := lvs.DefaultOptions
    opts.SubCost = 1
    dist := float64(lvs.DistanceForStrings(qr, cr, opts))
    return math.Max(1.0-dist/float64(len(cr)), 0) // normalize by length
}

func bestScore(query string, candidates []string, trim bool) float64 {
    best := 0.0
    for _, c := range candidates {
        if s := score(query, c, trim); s > best {
            best = s
        }
    }
    return best
}
```

Why: dividing by length normalizes — one edit in a 3-char name matters far more than in a 20-char one. `math.Max(_, 0)` floors short-candidate cases. The same function serves prefix vs full-word semantics via the flag. Layer decision rules on top from most to least discriminating (exact match → trimmed-prefix gap → score ratio) so each rule tunes independently. Gotchas: **always slice on `[]rune`, never bytes** — `candidate[:len(query)]` panics on multi-byte input. Levenshtein is O(m×n); cache scores if called in a hot loop.

---

## 2. Bitmask-pruned trie for fuzzy / subsequence lookup

When you have a fixed vocabulary (hundreds of strings) and need fast subsequence lookups with early pruning, without a full edit-distance scan of the whole trie. Each node stores a `uint64` bitmask of every letter reachable in its subtree; a single bitwise AND prunes entire branches that can't contain the remaining query characters.

```go
type node struct {
    children map[rune]*node
    mask     uint64 // bit i set = letter 'a'+i appears somewhere in this subtree
    terminal bool
}

func maskOf(rs []rune) uint64 {
    var m uint64
    for _, r := range rs {
        m |= 1 << uint64(r-'a')
    }
    return m
}

// during traversal: skip a subtree that can't supply all remaining chars
func (n *node) find(remaining []rune, out *[]string) {
    need := maskOf(remaining)
    if n.mask&need != need {
        return // provably cannot contain the subsequence — prune
    }
    // ... descend children, consuming runes ...
}
```

Build the trie once at startup, set each node's `mask` on insert (zero per-lookup cost). Why: the prune check is one `AND` — branch elimination before recursion. Gotchas: this layout is a-z/ASCII only (26 bits of a uint64); other scripts need a different reachability hash. The trie is read-only after init — concurrent writes need external locking.

---

## 3. Rotate-to-front promotion

Promote one element to index 0 based on a runtime condition while preserving the relative order of everything else (leader election, pinning, priority promotion).

```go
func rotateToFront[T any](items []T, idx int) []T {
    if idx <= 0 || idx >= len(items) {
        return items
    }
    out := make([]T, 0, len(items))
    out = append(out, items[idx])
    out = append(out, items[:idx]...)
    out = append(out, items[idx+1:]...)
    return out
}
```

Why: clear and order-preserving. Return `([]T, bool)` from the heuristic that picks `idx` so the caller decides whether to commit the promotion. Gotcha: the in-place variant `append(items[:idx], items[idx+1:]...)` mutates the original backing array — if anything else holds the slice, it sees the change. Assign back to the same variable and don't keep the old reference; the allocating version above is safer when in doubt.

---

## 4. Composite-key seen-set dedup (with alias keys)

Deduplicate a slice of typed records in one O(n) order-preserving pass — keying on `type+id`, and optionally suppressing records that alias the same real-world entity through a second field (e.g. a parent/group id).

```go
func dedup(records []Record) []Record {
    seen := make(map[string]bool, len(records))
    out := records[:0] // reuse backing array
    for _, r := range records {
        key := r.Type + "\x00" + r.ID // separator avoids "a"+"bc" == "ab"+"c"
        if seen[key] {
            continue
        }
        if r.ParentID != "" { // alias: also suppress same-parent dups
            alias := "parent\x00" + r.ParentID
            if seen[alias] {
                continue
            }
            seen[alias] = true
        }
        seen[key] = true
        out = append(out, r)
    }
    return out
}
```

Why: one map handles both the primary key and the alias path; adding a new alias dimension is one check-and-register block, no nested passes. Gotchas: **always use a separator byte** in composite keys, or `type="a",id="bc"` collides with `type="ab",id="c"`. Prefix alias keys (`"parent\x00"`) so a parent id can't collide with a primary id.

---

## 5. Fixed-slot interleave of two streams

Place priority items (sponsored, pinned) at designated positions while preserving the organic stream's relative order, and drain any surplus from either stream rather than dropping it.

```go
func interleave(items, priority []Item, slots map[int]bool) ([]Item, map[int]bool) {
    out := make([]Item, 0, len(items)+len(priority))
    filled := map[int]bool{}
    var pi, oi int
    for i := 0; i < len(items); i++ {
        if slots[i] && pi < len(priority) {
            out = append(out, priority[pi]); pi++
            filled[len(out)-1] = true
        } else if oi < len(items) {
            out = append(out, items[oi]); oi++
        }
    }
    out = append(out, items[oi:]...)    // drain leftovers — organic first
    out = append(out, priority[pi:]...) // then unused priority
    return out, filled
}
```

Why: single O(n) pass, organic order intact, no silent data loss (surplus is appended, not dropped), and the returned position map lets callers mark which slots are priority for tracking. Gotcha: this is a *layout* concern — feed it an already-ranked organic slice; don't let it double as the ranker.

---

## 6. Multi-factor weighted scoring in a comparator

Rank by a weighted combination of several signals where the weights must be tunable at runtime. Pre-normalize each signal into a `map[id]float64`, read the weights **once outside the comparator**, and combine linearly.

```go
func rank(ctx context.Context, items []Item, sig signals) {
    // read tunable weights ONCE — never inside the sort closure (it runs O(n log n) times)
    wQ := rconfig.GetFloat(ctx, "rank.w_quality")
    wD := rconfig.GetFloat(ctx, "rank.w_distance")
    wS := rconfig.GetFloat(ctx, "rank.w_sim")

    qN := normalize(sig.quality)  // max-normalize each signal to [0,1]
    dN := normalize(sig.distance)
    sN := normalize(sig.sim)

    score := func(id int) float64 {
        s := wQ*qN[id] + wS*sN[id]
        if dN[id] != 0 {
            s += wD * (1.0 / dN[id]) // inverse: smaller distance → higher score
        }
        return s
    }
    sort.SliceStable(items, func(i, j int) bool { return score(items[i].ID) > score(items[j].ID) })
}
```

Why: no code change to re-tune weights; `normalize` and `score` are pure and testable; inverse distance keeps "closer is better" inside one linear model. Gotcha: the load-bearing fix is reading the config weights **before** the sort, not inside the comparator — a flag read per comparison is a real cost on large slices.

---

## 7. Exclusion-set membership with a self-include guard

Compute a final inclusion set from candidates minus exclusions, gated by a feature check, always including the caller's own id, and returning `nil` (not empty slice) so callers gate on `len(result) > 0`.

```go
func inclusionSet(enabled []string, candidates []string, exclude []uint64, selfID uint64) []string {
    self := strconv.FormatUint(selfID, 10)
    if !contains(enabled, self) || len(candidates) == 0 {
        return nil // feature off or nothing to do
    }
    ex := make(map[string]bool, len(exclude))
    for _, id := range exclude {
        if id != selfID { // never exclude self from its own set
            ex[strconv.FormatUint(id, 10)] = true
        }
    }
    var out []string
    for _, id := range candidates {
        if id == self || ex[id] {
            continue
        }
        out = append(out, id)
    }
    if len(out) == 0 {
        return nil
    }
    return append(out, self) // always include self, at the end
}
```

Why: O(n), single exclusion-map allocation. The "never exclude self" guard is easy to miss and prevents an entity dropping out of its own scope. Returning `nil` makes the idiomatic `len() > 0` gate work. Gotcha: standardize id formatting (int vs string) at the package boundary, or the `enabled` string check silently fails.

---

## 8. Per-type quota in a single collect pass

Cap items of a given category at a config-driven limit while collecting, routing the surplus to an explicit overflow bucket rather than dropping it.

```go
func collect(ctx context.Context, items []Item) (primary, overflow []Item) {
    limit := rconfig.GetInt(ctx, "quota.special_max") // tunable, no deploy
    var special int
    for _, it := range items {
        if it.Type == TypeSpecial {
            if special < limit {
                primary = append(primary, it); special++
            } else {
                overflow = append(overflow, it)
            }
            continue
        }
        primary = append(primary, it)
    }
    return
}
```

Why: the cap is visible at the call site (from config), the loop is one pass with separated buckets, and the overflow is returned for the caller to use rather than silently dropped. Gotcha: past ~5-6 per-type branches, split into sub-collectors.

---

## 9. Offset-day trick for branchless cross-midnight lookup

Find the next upcoming slot from a per-day schedule when the answer may roll past midnight — without a midnight special-case. Offset the next day's slots by a full day (`+2400` in HHMM, or `+24h`) so today and tomorrow form one continuous 48-hour timeline.

```go
// times in HHMM (2200 = 10pm). nextSlots are tomorrow's, offset into a 48h day.
func nextSlot(now int, today, tomorrow []Slot) (s Slot, opensToday, found bool) {
    all := append([]Slot{}, today...)
    for _, t := range tomorrow {
        all = append(all, Slot{Start: t.Start + 2400, End: t.End + 2400})
    }
    for _, sl := range all {
        if sl.Start > now {
            return sl, sl.Start < 2400, true // opensToday falls out of the offset
        }
    }
    return Slot{}, false, false
}
```

Why: the loop is uniform whether the next slot is today or tomorrow — no branch at the midnight boundary, and `opensToday` is just `start < 2400`. Gotcha: handles today+tomorrow only; for N days ahead, chain offsets (4800, 7200, …).
