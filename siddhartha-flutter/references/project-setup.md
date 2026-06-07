# Starting a Flutter project from scratch

Zero → first running feature. Run the version check first.

> **Verify versions before pinning anything.** Use context7 (`resolve-library-id` → `query-docs`) or `flutter pub outdated` / pub.dev for the current major of each package. The versions below are illustrative, not pinned truth. Add caret ranges that match the current majors.

## 1. Create the app

```bash
flutter create --org com.heymanlabs --platforms=ios,android my_app
cd my_app
```

## 2. Add dependencies

```bash
# runtime
flutter pub add flutter_riverpod riverpod_annotation \
  freezed_annotation json_annotation \
  dio retrofit \
  go_router \
  flutter_animate

# dev / codegen
flutter pub add --dev build_runner \
  riverpod_generator freezed json_serializable retrofit_generator \
  go_router_builder \
  custom_lint riverpod_lint \
  mocktail
```

Add **only when the app is offline-first** (ask first — see `offline-first.md`):

```bash
flutter pub add drift sqlite3_flutter_libs path_provider path
flutter pub add --dev drift_dev
```

## 3. Folder skeleton

```
lib/
  core/
    network/        # dio.dart, failure.dart
    router/         # router.dart
    theme/
  features/         # one folder per feature (see vertical-slice.md)
  main.dart
test/
```

```bash
mkdir -p lib/core/{network,router,theme} lib/features
```

## 4. analysis_options.yaml

Turn on the riverpod lints via custom_lint — they catch the most common Riverpod mistakes at author time.

```yaml
include: package:flutter_lints/flutter.yaml

analyzer:
  plugins:
    - custom_lint
  exclude:
    - "**/*.g.dart"
    - "**/*.freezed.dart"

linter:
  rules:
    prefer_const_constructors: true
    prefer_const_constructors_in_immutables: true
```

## 5. Gitignore generated files

Append to `.gitignore`:

```
# codegen output — regenerated via build_runner
*.g.dart
*.freezed.dart
```

## 6. main.dart

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/router/router.dart';

void main() {
  runApp(const ProviderScope(child: MyApp()));
}

class MyApp extends ConsumerWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp.router(
      routerConfig: ref.watch(routerProvider),
      theme: ThemeData(useMaterial3: true),
    );
  }
}
```

`core/router/router.dart` exposes a `@riverpod` `GoRouter routerProvider`, aggregating each feature's typed routes (`$appRoutes` from go_router_builder once routes exist).

## 7. Generate, then run

```bash
dart run build_runner build --delete-conflicting-outputs   # one-shot
# or, during active development:
dart run build_runner watch --delete-conflicting-outputs
flutter run
```

A fresh clone shows analyzer errors until the first `build_runner` run — that's expected. **Generate first.** This is why a teammate cloning the repo should run build_runner before opening the IDE's problems tab.

## 8. Build the first feature

Follow the checklist at the end of `vertical-slice.md`. Start with one read-only screen end to end (model → dto → api → repository → view-model → screen → route) so the whole pipe is proven before adding writes.

## CI sketch

```yaml
- run: flutter pub get
- run: dart run build_runner build --delete-conflicting-outputs
- run: dart analyze
- run: flutter test
```

Generated files are gitignored, so the `build_runner` step is mandatory in CI before analyze/test.
