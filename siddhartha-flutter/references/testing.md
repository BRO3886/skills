# Testing patterns

The seam is always the same: **override providers** in a `ProviderContainer` (logic tests) or `ProviderScope` (widget tests). What you put behind the override is the decision below.

## What to fake, and how

- **Repositories → hand-written in-memory fakes.** Stateful, backed by a `Map`, so create-then-list genuinely works. Written once per feature, reused across every test. A fake `implements` the concrete repository class (no abstract interface needed — Dart lets you implement a concrete class's interface).
- **Leaf boundaries → mocktail.** The retrofit api client, platform plugins, anything you only need a canned response from or want to assert a call against.

Rule of thumb: if a test exercises a *flow* (do X, then assert Y reflects it), use the stateful fake. If it just needs "this call returns this value" or "this call happened", use mocktail.

## In-memory fake repository

```dart
class FakeExpenseRepository implements ExpenseRepository {
  final _store = <String, Expense>{};

  void seed(List<Expense> expenses) {
    for (final e in expenses) _store[e.id] = e;
  }

  @override
  Future<List<Expense>> list(String groupId) async => _store.values.toList();

  @override
  Future<Expense> create(String groupId, ExpenseDto body) async {
    final e = body.toDomain();
    _store[e.id] = e;
    return e;
  }
}
```

## ViewModel test (logic, through the fake)

```dart
void main() {
  late FakeExpenseRepository repo;
  late ProviderContainer container;

  setUp(() {
    repo = FakeExpenseRepository();
    container = ProviderContainer(
      overrides: [expenseRepositoryProvider.overrideWithValue(repo)],
    );
    addTearDown(container.dispose);
  });

  test('add() creates then reflects in the list', () async {
    repo.seed([]);
    // await the initial build
    await container.read(expenseListProvider('g1').future);

    await container.read(expenseListProvider('g1').notifier).add(
          ExpenseDto(id: 'e1', description: 'Chai', amountPaise: 4000, paidBy: 'u1', createdAt: DateTime(2026)),
        );

    final state = await container.read(expenseListProvider('g1').future);
    expect(state.map((e) => e.id), contains('e1'));
  });
}
```

## Repository test (real repo, mocktail at the boundary)

Here the *repository* is under test, so the API client — the boundary — is mocked.

```dart
class MockExpenseApi extends Mock implements ExpenseApi {}

void main() {
  test('list maps DTOs to domain', () async {
    final api = MockExpenseApi();
    when(() => api.list('g1')).thenAnswer((_) async => [
          ExpenseDto(id: 'e1', description: 'Chai', amountPaise: 4000, paidBy: 'u1', createdAt: DateTime(2026)),
        ]);

    final repo = ExpenseRepository(api);
    final result = await repo.list('g1');

    expect(result.single.description, 'Chai');
    expect(result.single, isA<Expense>()); // wire shape did not leak
  });
}
```

## Widget test

Pump the screen inside a `ProviderScope` with the same overrides.

```dart
testWidgets('shows expenses', (tester) async {
  final repo = FakeExpenseRepository()..seed([
    Expense(id: 'e1', description: 'Chai', amountPaise: 4000, paidBy: 'u1', createdAt: DateTime(2026)),
  ]);

  await tester.pumpWidget(ProviderScope(
    overrides: [expenseRepositoryProvider.overrideWithValue(repo)],
    child: const MaterialApp(home: ExpenseListScreen(groupId: 'g1')),
  ));
  await tester.pumpAndSettle();

  expect(find.text('Chai'), findsOneWidget);
});
```

## Error-path tests — two distinct levels

These are different tests and a common place to write a fake that passes for the wrong reason. Keep them separate.

**(a) The repository converts `DioException` → `Failure`.** The real api client throws `DioException`, *not* `Failure` — so to exercise `guard()`, the mock must throw a `DioException`. Asserting the repo rethrows the mapped `Failure` is the test that proves the error pipe actually connects.

```dart
test('network error maps to NetworkFailure', () async {
  final api = MockExpenseApi();
  when(() => api.list(any())).thenThrow(
    DioException(requestOptions: RequestOptions(), type: DioExceptionType.connectionError),
  );
  final repo = ExpenseRepository(api);

  expect(() => repo.list('g1'), throwsA(isA<NetworkFailure>()));
});
```

> Do **not** make the api mock throw a `Failure` directly here — the real api never does, so it would skip `guard()` entirely and pass over a broken pipe.

**(b) The View renders the right branch for a given `Failure`.** Here the *fake repository* throws a `Failure` directly — and that is correct, because the repository's public contract (post-`guard()`) *is* "throws `Failure`." So the fake matches the real contract.

```dart
class _ThrowingRepo implements ExpenseRepository {
  @override
  Future<List<Expense>> list(String groupId) async => throw const NetworkFailure();
  @override
  Future<Expense> create(String g, ExpenseDto b) async => throw const NetworkFailure();
}

testWidgets('offline shows the offline branch', (tester) async {
  await tester.pumpWidget(ProviderScope(
    overrides: [expenseRepositoryProvider.overrideWithValue(_ThrowingRepo())],
    child: const MaterialApp(home: ExpenseListScreen(groupId: 'g1')),
  ));
  await tester.pumpAndSettle();
  expect(find.text("You're offline"), findsOneWidget);
});
```

## Golden tests (optional)

Use `alchemist` for golden/snapshot tests of leaf widgets and key screens. Keep them for visually load-bearing components, not every widget. Optional — don't gate a feature on goldens.

## What not to do

- Don't mock the repository when you're testing a *flow* — use the stateful fake so the flow is real.
- Don't mock drift/the database in a test whose job is to verify a query — use an in-memory drift instance.
- Don't assert on generated provider internals — drive through the public `AsyncValue`/state.
