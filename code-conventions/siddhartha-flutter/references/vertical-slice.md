# The repeatable feature slice

Copy this per feature. The example feature is `expense`; rename throughout. This is the **default online slice** — no local store, no sync. For offline-first, layer on `offline-first.md` after.

> Syntax reflects **freezed 3.x**, **Riverpod 3**, and **go_router_builder** with the required `with _$RouteName` mixin (all verified current as of authoring). Still re-check versions before relying — see the version warning in `SKILL.md`.

## 1. Core (once per app, not per feature)

`core/network/dio.dart` — just the client. **Interceptors are for auth/logging/retry, not error typing** (an interceptor's `reject` can only throw a `DioException`, so it can't deliver a `Failure` to the await site — that has to happen in `guard()`, below):

```dart
import 'package:dio/dio.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'dio.g.dart';

@riverpod
Dio dio(Ref ref) {
  return Dio(BaseOptions(baseUrl: const String.fromEnvironment('API_BASE_URL')));
  // add auth/logging interceptors here as needed — NOT error classification
}
```

`core/network/failure.dart` — the sealed hierarchy (see `SKILL.md` for the full class list) **plus** the classifier and guard. These two are the entire error pipe:

```dart
import 'package:dio/dio.dart';

// ... sealed class Failure + subtypes (see SKILL.md) ...

Failure mapDioException(DioException e) => switch (e.type) {
      DioExceptionType.connectionError ||
      DioExceptionType.connectionTimeout ||
      DioExceptionType.receiveTimeout => const NetworkFailure(),
      DioExceptionType.badResponse => switch (e.response?.statusCode) {
          401 => const UnauthorizedFailure(),
          422 => ValidationFailure(e.response?.data?['error']?.toString() ?? 'Invalid'),
          final code? when code >= 500 => ServerFailure('Server error', code),
          _ => const UnknownFailure(),
        },
      _ => const UnknownFailure(),
    };

/// The ONE place a DioException becomes a thrown Failure. Repositories call through this.
Future<T> guard<T>(Future<T> Function() body) async {
  try {
    return await body();
  } on DioException catch (e) {
    throw mapDioException(e);
  }
}
```

## 2. Domain model — `domain/expense.dart`

A freezed class. No JSON here — the DTO owns the wire; the domain model is pure.

```dart
import 'package:freezed_annotation/freezed_annotation.dart';

part 'expense.freezed.dart';

@freezed
abstract class Expense with _$Expense {
  const factory Expense({
    required String id,
    required String description,
    required int amountPaise,
    required String paidBy,
    required DateTime createdAt,
  }) = _Expense;
}
```

## 3. DTO — `data/expense_dto.dart`

Matches the wire exactly. Maps to the domain model so the wire shape stops here.

```dart
import 'package:json_annotation/json_annotation.dart';
import '../domain/expense.dart';

part 'expense_dto.g.dart';

@JsonSerializable()
class ExpenseDto {
  ExpenseDto({
    required this.id,
    required this.description,
    required this.amountPaise,
    required this.paidBy,
    required this.createdAt,
  });

  factory ExpenseDto.fromJson(Map<String, dynamic> json) => _$ExpenseDtoFromJson(json);

  final String id;
  final String description;
  @JsonKey(name: 'amount_paise') final int amountPaise;
  @JsonKey(name: 'paid_by') final String paidBy;
  @JsonKey(name: 'created_at') final DateTime createdAt;

  Map<String, dynamic> toJson() => _$ExpenseDtoToJson(this);

  Expense toDomain() => Expense(
        id: id,
        description: description,
        amountPaise: amountPaise,
        paidBy: paidBy,
        createdAt: createdAt,
      );
}
```

## 4. API client — `data/expense_api.dart`

retrofit generates the implementation from the annotated abstract class.

```dart
import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../../../core/network/dio.dart';
import 'expense_dto.dart';

part 'expense_api.g.dart';

@RestApi()
abstract class ExpenseApi {
  factory ExpenseApi(Dio dio) = _ExpenseApi;

  @GET('/v1/groups/{groupId}/expenses')
  Future<List<ExpenseDto>> list(@Path('groupId') String groupId);

  @POST('/v1/groups/{groupId}/expenses')
  Future<ExpenseDto> create(@Path('groupId') String groupId, @Body() ExpenseDto body);
}

@riverpod
ExpenseApi expenseApi(Ref ref) => ExpenseApi(ref.watch(dioProvider));
```

## 5. Repository — `data/expense_repository.dart`

Calls the API through `guard()`, maps DTO → domain. `guard()` converts any `DioException` into a thrown `Failure`, so the rest of the app only ever sees `Failure`.

```dart
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../../../core/network/failure.dart';
import '../domain/expense.dart';
import 'expense_api.dart';

part 'expense_repository.g.dart';

class ExpenseRepository {
  ExpenseRepository(this._api);
  final ExpenseApi _api;

  Future<List<Expense>> list(String groupId) => guard(() async {
        final dtos = await _api.list(groupId);
        return dtos.map((d) => d.toDomain()).toList();
      });

  Future<Expense> create(String groupId, ExpenseDto body) => guard(() async {
        final dto = await _api.create(groupId, body);
        return dto.toDomain();
      });
}

@riverpod
ExpenseRepository expenseRepository(Ref ref) =>
    ExpenseRepository(ref.watch(expenseApiProvider));
```

## 6. ViewModel — `presentation/expense_list_view_model.dart`

A `@riverpod` class is the ViewModel. `build()` returns the initial async state; commands mutate it.

```dart
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../domain/expense.dart';
import '../data/expense_repository.dart';

part 'expense_list_view_model.g.dart';

@riverpod
class ExpenseList extends _$ExpenseList {
  @override
  Future<List<Expense>> build(String groupId) {
    return ref.watch(expenseRepositoryProvider).list(groupId);
  }

  Future<void> add(ExpenseDto body) async {
    final repo = ref.read(expenseRepositoryProvider);
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      await repo.create(groupId, body);
      return repo.list(groupId);
    });
  }
}
```

`build(String groupId)` is a **family** — `expenseListProvider(groupId)`. With **riverpod_generator**, the build args are exposed as fields on the generated base, so `add()` reads `groupId` via `this.groupId` directly — no constructor needed. (The *manual* Riverpod 3 API removed family Notifier variants and instead takes the arg through a constructor field; don't conflate the two — this skill uses codegen.)

A view-state class is unnecessary here; `AsyncValue<List<Expense>>` is the view state. Mint a `@freezed ExpenseListState` only if the screen also needs a filter, selection, or computed totals.

## 7. View — `presentation/expense_list_screen.dart`

Dumb. Watches one provider, switches the `AsyncValue`, switches the `Failure` on error.

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/failure.dart';
import 'expense_list_view_model.dart';
import 'widgets/expense_tile.dart';

class ExpenseListScreen extends ConsumerWidget {
  const ExpenseListScreen({required this.groupId, super.key});
  final String groupId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final expenses = ref.watch(expenseListProvider(groupId));
    return Scaffold(
      appBar: AppBar(title: const Text('Expenses')),
      body: expenses.when(
        data: (items) => ListView.builder(
          itemCount: items.length,
          itemBuilder: (_, i) => ExpenseTile(expense: items[i]),
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => switch (e) {
          NetworkFailure() => const _Retry(message: 'You\'re offline'),
          UnauthorizedFailure() => const _Retry(message: 'Please sign in again'),
          Failure(:final message) => _Retry(message: message),
          _ => const _Retry(message: 'Something went wrong'),
        },
      ),
    );
  }
}
```

Leaf widgets (`ExpenseTile`, `_Retry`) live in `widgets/` and are `const` where possible.

## 8. Typed route — `expense_routes.dart`

```dart
import 'package:flutter/widgets.dart';
import 'package:go_router/go_router.dart';
import 'presentation/expense_list_screen.dart';

part 'expense_routes.g.dart';

@TypedGoRoute<ExpenseListRoute>(path: '/groups/:groupId/expenses')
class ExpenseListRoute extends GoRouteData with _$ExpenseListRoute {
  const ExpenseListRoute({required this.groupId});
  final String groupId;

  @override
  Widget build(BuildContext context, GoRouterState state) =>
      ExpenseListScreen(groupId: groupId);
}

// Navigate: const ExpenseListRoute(groupId: id).go(context);
```

## Checklist for "add a feature"

1. `domain/<feature>.dart` — freezed model.
2. `data/<feature>_dto.dart` — JSON + `toDomain()`.
3. `data/<feature>_api.dart` — retrofit endpoints + provider.
4. `data/<feature>_repository.dart` — maps, throws `Failure`, + provider.
5. `presentation/<feature>_view_model.dart` — `@riverpod` Notifier.
6. `presentation/<feature>_screen.dart` — View, `AsyncValue.when` + `Failure` switch.
7. `presentation/widgets/` — `const` leaf widgets.
8. `<feature>_routes.dart` — typed route.
9. `dart run build_runner build -d`.
10. Tests per `testing.md`.
