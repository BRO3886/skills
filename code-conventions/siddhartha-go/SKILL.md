---
name: siddhartha-go
description: "Siddhartha's backend engineering conventions. Use when writing, reviewing, or designing Go backend or CLI code, including APIs, persistence, testing, gRPC, observability, caching, resilience, and goroutine safety. Also use when Siddhartha asks to apply his language-agnostic architecture principles in another backend language. Do not use for parallel-agent orchestration or unrelated non-Go concurrency."
---

# Siddhartha's Go Backend Style Guide

Use this skill to apply conventions extracted from Siddhartha's production Go projects and high-throughput backend services. The main file carries the decision process and cross-cutting rules. Load detailed patterns from `references/` only when the task needs them.

## Apply the skill

1. **Inspect before prescribing.** Read the repository instructions, current architecture, and nearby code. An established local convention wins unless the task explicitly changes it.
2. **Classify the task.** Use the reference router below. Read only the references needed for the current branch.
3. **Define the contract first.** State result semantics, error semantics, dependency boundaries, lifecycle ownership, and verification before choosing an implementation.
4. **Implement a vertical slice.** Make the smallest coherent change that crosses every required layer. Do not build one horizontal layer across the whole system before proving the end-to-end path.
5. **Verify every consumer.** Run the repository's canonical checks and the branch-specific checks below. Inspect callers, configuration readers, schemas, jobs, and shutdown paths affected by the change.

Use these leading terms consistently in plans and reviews: **boundary-first**, **explicit contract**, **vertical slice**, and **ownership before concurrency**.

## Reference router

| Task | Read |
| --- | --- |
| Project layout, naming, service/repository boundaries, dependency injection, errors, APIs, HTTP, database, testing, static config, comments, or stack choices | `references/conventions.md` |
| Goroutines, fan-out, worker pools, async loaders, contexts, timeouts, or startup/shutdown | `references/concurrency.md` |
| Caching, request coalescing, rate limiting, retry, or graceful degradation | `references/caching-resilience.md` |
| gRPC servers or clients, interceptor ordering, metadata, or transport policy | `references/grpc.md` |
| Structured logging, metrics, latency measurement, or tracing | `references/observability.md` |
| Runtime config, feature flags, kill switches, safe defaults, or gradual rollout | `references/runtime-config.md` |
| Complex function decomposition, eligibility versus transformation, branch unification, result assembly, or sticky errors | `references/idioms.md` |
| Matching, ranking, deduplication, interleaving, scoring, quotas, or list placement | `references/algorithms.md` |

Do not load a reference only because it exists. A CLI parser change does not need the gRPC, caching, or algorithm references.

## Design philosophy

- **Boundary-first.** Separate decisions from actions. Keep core logic pure, read flags and configuration at the edge, and inject dependencies and tunables rather than reaching into global state.
- **Design for testability.** Prefer pure functions of explicit inputs, dependencies injected behind narrow interfaces, and predicates driven by plain table-test values. If a unit needs a large mock graph, move the dependency boundary outward.
- **Use an explicit result contract.** Choose one of two contracts before implementation:
  - **All-or-nothing:** return no usable result when any required operation fails.
  - **Partial result:** return a complete result that represents every successful independent operation, plus an aggregated error describing failures.
  Never return a partially mutated value that violates its invariants.
- **Fail fast with flat control flow.** Use a negative-guard ladder with one condition per line and early returns. Each branch must be independently readable, testable, and breakpointable.
- **Code for the on-call engineer.** Add lifecycle ownership, safe runtime levers, and distinct errors for deliberate shutoffs. Expected conditions must not enter the paging path.
- **Keep it simple until a real second case appears.** Prefer concrete types over `any`, direct arguments over premature option objects, and one implementation over an abstraction that predicts future variation.

## Cross-cutting Go rules

- Wrap returned errors with operation context and `%w` so `errors.Is` and `errors.As` keep working.
- Accept the narrowest interface the function consumes. Put repository interfaces beside the domain or consumer that defines the required operations.
- Keep mutable process state out of package globals. Construct dependencies explicitly and keep runtime reads at composition or request boundaries.
- A best-effort side effect must not fail the primary operation. Record an operationally meaningful failure through a bounded log or metric. Silence it only when the failure is intentionally unobservable.
- Return sentinel or typed errors for expected control states. Keep internal diagnostic detail separate from user-facing hints.
- Do not use `panic` for ordinary production errors. A boundary that recovers a panic must preserve the failure as an error and make the incident observable.
- Keep comments sparse. Comment only a hidden constraint, invariant, or workaround. Every exported symbol still needs its normal Go documentation comment.

## Verification

- Use expected values from an external contract, real engine, schema, or captured behavior. Do not derive the expected value from the implementation under test.
- Run the repository's formatter, static analysis, and full test suite. If the repository has no documented commands, run `gofmt -w` on the changed Go files, then run `go vet ./...` and `go test ./...`.
- For concurrency or lifecycle changes, also run `go test -race ./...` and test cancellation, timeout, panic, shutdown, and partial-failure paths.
- For persistence behavior, test against the real database engine. An in-memory repository can test service logic but cannot prove SQL, migrations, constraints, or transaction behavior.
- Verify both ends of every runtime-resolved value: producer, consumer, and the configuration or transport wire between them.
- Re-read the changed diff after checks. Remove abstractions, comments, or branches that do not change behavior.

## Non-Go backend work

When Siddhartha explicitly asks to apply this skill in another backend language, use only the application workflow, design philosophy, and verification rules. Preserve that language's idioms and the repository's architecture. Do not import Gin, Ent, Uber Fx, Go interface patterns, or goroutine rules by analogy.
