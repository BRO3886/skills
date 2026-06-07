---
name: siddhartha-flutter
description: "Siddhartha's Flutter app conventions and architecture patterns. Use when writing Flutter/Dart app code, scaffolding a new Flutter feature or whole project, designing state management, networking, offline-first sync, or dependency injection, or making architecture decisions in a Flutter project. Also use when reviewing Flutter PRs, structuring packages, or when someone asks about Flutter project conventions. Ensures consistency between Siddhartha and Gagan on Settld and shared Flutter work."
---

# Siddhartha's Flutter Style Guide

This guide encodes the architecture, conventions, and preferred stack for Siddhartha's Flutter apps. Follow these patterns for all Flutter work on Settld and shared projects. The goal is a single, repeatable shape so that building a new feature is mechanical and an agent can clone the pattern without re-deciding architecture each time.

This is a Flutter-native guide. It does not borrow backend layering — Flutter is a reactive, declarative widget tree, and the patterns here are built for that, not translated from server code.

## ⚠️ Verify current versions before scaffolding

The Flutter ecosystem moves fast and several of these libraries have had breaking API changes. **Before writing or scaffolding code, confirm the current syntax** — do not trust the snippets here as eternal truth.

- Prefer **context7**: call `resolve-library-id` then `query-docs` for `freezed`, `riverpod` / `riverpod_generator`, `retrofit`, `drift`, `go_router_builder`.
- Fall back to **web search** on pub.dev for the latest version and migration notes.
- The code in this skill's `references/` reflects **freezed 3.x** (`abstract`/`sealed` class keywords) and **Riverpod 3** (unified `Ref` type) as of authoring. Confirm these still hold, and adjust if a newer major has shipped.

## Preferred stack

| Concern | Choice | Why |
|---|---|---|
| State + DI | **Riverpod 3 + riverpod_generator** (both) | One library covers reactive state *and* the dependency graph; provider overrides are the test seam; the graph is analyzer-checked, unlike a runtime service locator |
| Local widget state | **flutter_hooks + hooks_riverpod** | Ephemeral controllers / focus / animation without `StatefulWidget` boilerplate; composes with Riverpod via `HookConsumerWidget` (same author) |
| Models / JSON | **freezed + json_serializable** | Immutable classes, `copyWith`, value equality, sealed unions, JSON — one annotation per type |
| Networking | **dio + retrofit** | dio for interceptors/retries/cancellation; retrofit generates the typed client from an annotated abstract class |
| Errors | **sealed `Failure` + dio interceptor** | Mapped once, thrown, caught by `AsyncValue`; exhaustive typed handling without a second error channel |
| Routing | **go_router + go_router_builder** (typed) | Compile-safe navigation; a typed route class is a clean per-feature template slot |
| Local / offline | **drift** (opt-in) | Reactive SQLite as local source of truth — only when the app is offline-first (see below) |
| Testing | **mocktail + in-memory fakes** | Stateful fakes for repositories, mocktail for leaf boundaries |
| Animation | **flutter_animate** (+ the `flutter-animations` skill if installed) | Easy-mode common animations; the companion skill covers explicit/physics/Hero |

## Dependency philosophy

Judge a dependency by how much it **entangles** with the others (n²), not by the raw count (n+1). A focused, well-aligned dep with one clean integration seam is close to free; a dep that overlaps responsibilities with something you already run is expensive no matter how small, because it multiplies the "which one owns this?" decision across the whole codebase.

- A **good (n+1)** dep is self-contained, has one intentional integration point, and doesn't fight the rest of the stack. `flutter_hooks` qualifies — it touches only Riverpod, through the first-class `HookConsumerWidget`.
- A **bad (n²)** dep competes with a tool you already have. That — not "fewer deps" — is the real reason these are out:
  - `get_it` — a second DI system racing Riverpod's provider graph.
  - `bloc` — a second state system racing notifiers.
  - `fpdart` by default — a second error channel racing `AsyncValue` (worth it only *locally* inside a chaining-heavy repository; see the error escape hatch).
  - `GetX` — competes with routing, DI, *and* state at once. The worst kind of n².

When weighing any new package, ask: does it have one clean seam, or does it overlap with two things I already have?

## Architecture: MVVM, feature-first

Every feature is a self-contained folder with three layers. Data flows up as state; events flow down as commands.

```
View (widget)  →  ViewModel (Riverpod Notifier)  →  Repository  →  data-sources (retrofit / drift)
```

- **View** — a dumb widget. It `watch`es one provider and renders. No logic, no http, no DTOs.
- **ViewModel** — a `@riverpod` `Notifier`/`AsyncNotifier`. Holds UI state, exposes commands (`refresh()`, `addExpense()`).
- **Repository** — the source of truth for a domain concept. Calls data-sources, maps DTO → domain, throws `Failure`.
- **Data-sources** — the retrofit API client (remote) and, when offline-first, the drift database (local).

There is **no Clean Architecture use-case layer** — single-action interactor classes are almost always one-line pass-throughs. The ViewModel calls the repository directly.

### Feature folder layout

```
lib/
  core/                       # cross-cutting, app-wide
    network/dio.dart          # dioProvider + the Failure interceptor
    network/failure.dart      # sealed class Failure + subtypes
    router/router.dart        # go_router config (typed routes aggregated)
    theme/
  features/<feature>/
    data/
      <feature>_dto.dart      # @JsonSerializable — wire shape
      <feature>_api.dart      # @RestApi abstract — retrofit endpoints (+ provider)
      <feature>_repository.dart  # maps DTO → domain, throws Failure (+ provider)
    domain/
      <feature>.dart          # @freezed — canonical domain model
    presentation/
      <feature>_view_model.dart  # @riverpod Notifier/AsyncNotifier
      <feature>_state.dart    # @freezed view state — ONLY when composed (see below)
      <feature>_screen.dart   # View — watches provider, switches AsyncValue
      widgets/                # dumb leaf widgets
    <feature>_routes.dart     # @TypedGoRoute typed route(s)
```

**The dependency chain is pure Riverpod**, one generated provider per link:

```
dioProvider → <feature>ApiProvider → <feature>RepositoryProvider → <feature>Provider (the ViewModel)
```

Full code for this slice — copy it per feature — is in **[references/vertical-slice.md](references/vertical-slice.md)**.

## The three model types

Keep wire data, domain data, and view data separate. The wire shape must never reach a widget.

1. **DTO** (`data/`) — matches the JSON exactly. `@JsonSerializable` (or a freezed class with `fromJson`).
2. **Domain model** (`domain/`) — the app's canonical entity, a `@freezed` class. The repository maps DTO → domain.
3. **View state** (`presentation/`) — what the ViewModel exposes to the View.

**Rules:**
- The DTO ↔ domain wall is **always** enforced. A backend field rename stops at the repository; it never ripples to the UI.
- A **dedicated view-state class is minted only when the screen composes or derives** — merges multiple entities, adds UI-only fields (a filter, a selection), or computes values. For a straight list, `AsyncValue<List<Expense>>` *is* the view state; a wrapper class would be empty ceremony.

Flow: `JSON → DTO → domain (repo maps) → view state (ViewModel composes) → View`.

## Error handling

A `sealed class Failure` lives in `core/network/failure.dart`:

```dart
sealed class Failure implements Exception {
  const Failure(this.message);
  final String message;
}
class NetworkFailure extends Failure { const NetworkFailure([super.m = 'No connection']); }
class ServerFailure extends Failure { const ServerFailure(super.m, this.statusCode); final int statusCode; }
class UnauthorizedFailure extends Failure { const UnauthorizedFailure([super.m = 'Session expired']); }
class ValidationFailure extends Failure { const ValidationFailure(super.m, [this.fields = const {}]); final Map<String, String> fields; }
class UnknownFailure extends Failure { const UnknownFailure([super.m = 'Something went wrong']); }
```

Errors are converted to a thrown `Failure` by **two small pieces** in `core/network/`:

```dart
// classifier — DioException → Failure
Failure mapDioException(DioException e) => switch (e.type) {
      DioExceptionType.connectionError ||
      DioExceptionType.connectionTimeout ||
      DioExceptionType.receiveTimeout => const NetworkFailure(),
      DioExceptionType.badResponse => switch (e.response?.statusCode) {
          401 => const UnauthorizedFailure(),
          422 => ValidationFailure(e.response?.data?['error']?.toString() ?? 'Invalid'),
          final c? when c >= 500 => ServerFailure('Server error', c),
          _ => const UnknownFailure(),
        },
      _ => const UnknownFailure(),
    };

// the one place DioException is unwrapped — repositories call through this
Future<T> guard<T>(Future<T> Function() body) async {
  try {
    return await body();
  } on DioException catch (e) {
    throw mapDioException(e);
  }
}
```

- **Repositories call through `guard()`.** That is the single place `DioException` becomes a `Failure`. (A dio interceptor *cannot* do this alone: `ErrorInterceptorHandler.reject` only accepts a `DioException`, so the type that escapes an `await` is always `DioException`, never your `Failure`. The conversion must happen in a Dart `try/catch`. Use interceptors for auth/logging/retry, not for error typing.)
- The ViewModel does **not** try/catch — the repository already throws `Failure`, and Riverpod's `AsyncValue` captures it.
- The View handles errors by **switching the `Failure`** in the error branch (exhaustive, compiler-checked).

```dart
ref.watch(expenseListProvider).when(
  data: (expenses) => ExpenseList(expenses),
  loading: () => const LoadingView(),
  error: (e, _) => switch (e) {
    NetworkFailure() => const OfflineBanner(),
    UnauthorizedFailure() => const ReloginPrompt(),
    Failure(:final message) => ErrorView(message),
    _ => const ErrorView('Something went wrong'),
  },
);
```

**Escape hatch:** a feature with genuine multi-step domain logic (validate → transform → persist → sync) may use `Either`/`Result` (fpdart) *locally inside its repository*, then collapse it to a throw at the ViewModel boundary (`result.fold((f) => throw f, (d) => d)`) so it re-enters the single `AsyncValue` pipe. fpdart is **not** a default dependency — pull it in only for the feature that needs chaining.

## Offline-first (opt-in)

**Most apps are not offline-first, and the offline machinery is real, ongoing complexity.** So:

> **Before scaffolding any local store, mutation queue, or sync engine, ASK the developer: "Is this app offline-first?"** Only build it if the answer is yes.

When it is yes, follow **[references/offline-first.md](references/offline-first.md)**: drift becomes the local source of truth (the UI reads drift, writes hit drift instantly), a mutation-outbox table queues changes, and a pluggable sync engine drains the queue against a delta endpoint with **last-write-wins + surface-conflicts** resolution. The default online slice does not load any of this.

## UI layer

- Views are **dumb**. Logic lives in the ViewModel.
- Widgets are `HookConsumerWidget` (or `ConsumerWidget` when no hooks are needed). They `watch` providers and render — nothing else.
- **State ownership — the bright line that keeps hooks at n+1:** hooks hold **ephemeral, widget-local** state that dies with the widget (`useTextEditingController`, `useFocusNode`, `useAnimationController`, `useState` for a local toggle). **Riverpod holds anything shared or longer-lived than the widget.** If state must survive a rebuild-from-scratch or be read elsewhere, it's a provider, never a hook.
- Split a big `build()` into small, named, **`const`** leaf widgets in `widgets/` — never one 300-line `build()`.
- A widget that doesn't depend on a `BuildContext` value should be `const`.
- Scope rebuilds with `ref.watch(provider.select(...))` so a widget rebuilds only when the slice it uses changes — don't watch a whole object to read one field.
- Use `ListView.builder` / `SliverList` for any list of unknown length — lazy by default, builds only visible items.
- Add `Key`s where widget identity matters (reorderable / filtered lists).
- **Platform-adaptive look** by default — Cupertino-flavoured on iOS, Material 3 on Android. *All* platform branching lives in one adaptive layer (`core/ui/`: `AppButton`, `AppScaffold`, …); feature code never sees `Platform.isIOS`.
- **Theming:** Material 3 `ThemeData` + `ThemeExtension` for brand tokens. No literal colors / spacing / radii in a `build()` — pull from the theme or a token.
- **iOS Liquid Glass is not in core Flutter** (design updates paused in 2025); only young community packages bridge it. Opt-in, and isolated behind `core/ui/` so it's swappable later.

Full UI treatment — adaptive-layer code, the `ThemeExtension` token example, the Liquid Glass libraries, and widget organization — is in **[references/ui-layer.md](references/ui-layer.md)**.

## Codegen workflow

- Run `dart run build_runner watch -d` during development.
- **Generated files (`*.g.dart`, `*.freezed.dart`) are gitignored.** CI runs `dart run build_runner build --delete-conflicting-outputs` before analyze/test.
- A fresh clone shows errors until the first generate — this is expected; running build_runner is step one (the project-setup reference makes this explicit).

## Naming

- Files: `snake_case.dart`. One file per layer-piece per feature.
- Types: `PascalCase`. ViewModels named for the screen (`ExpenseList`, not `ExpenseListViewModel` — the `@riverpod class ExpenseList` generates `expenseListProvider`).
- Providers: `<thing>Provider` (generated automatically from the annotated name).

## Starting a new project

For zero → first running feature (pubspec with the stack, folder skeleton, `analysis_options.yaml`, build_runner, run commands), follow **[references/project-setup.md](references/project-setup.md)**.

## Testing

In-memory fakes for repositories, mocktail at the boundaries, `ProviderScope`/`ProviderContainer` overrides as the seam. Full patterns in **[references/testing.md](references/testing.md)**.

## Anti-patterns

- `get_it` for DI — Riverpod's provider graph is the DI, and it's analyzer-checked.
- `bloc` — Riverpod is the state solution here; don't mix two.
- `fpdart` by default — only inside a chaining-heavy repository (see escape hatch).
- `GetX` — magic, global state, poor testability. Never.
- Letting a DTO / JSON map reach a widget — always map to a domain model first.
- Wrapping `Either` inside `AsyncValue` — two competing error channels; throw instead.
- Business logic in a `build()` method or a widget — it belongs in the ViewModel/repository.
- A 300-line `build()` — split into `const` leaf widgets.
- Building offline/sync machinery without asking whether the app is even offline-first.
- Committing generated `*.g.dart` / `*.freezed.dart` — they're gitignored.
