# UI layer

The View layer's job: render state, send events up, and look right on each platform. Logic stays in the ViewModel (see `SKILL.md`). This file covers cross-platform look, the adaptive widget layer, theming/tokens, and widget organization.

## Cross-platform stance: platform-adaptive

Default to a **native look per platform** — Cupertino-flavoured on iOS, Material 3 on Android — not one identical design on both. (A design-led product with a strong custom identity may instead choose a single custom design language on both platforms; that's the alternative, decide it per project.)

The thing that makes platform-adaptive maintainable — and agent-repeatable — is that **platform branching lives in exactly one place: `core/ui/`.** Feature code never sees `Platform.isIOS`.

## The adaptive widget layer (`core/ui/`)

Feature/presentation code calls *your* widgets — `AppScaffold`, `AppButton`, `AppNavBar`, `AppSwitch` — never `Cupertino*`/`Material*` directly. Each wrapper picks the platform implementation.

```dart
// core/ui/app_button.dart
import 'dart:io' show Platform;
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

class AppButton extends StatelessWidget {
  const AppButton({required this.label, required this.onPressed, super.key});
  final String label;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    if (Platform.isIOS) {
      return CupertinoButton.filled(onPressed: onPressed, child: Text(label));
    }
    return FilledButton(onPressed: onPressed, child: Text(label));
  }
}
```

- Use `Platform.isIOS` (or `defaultTargetPlatform`, which is testable via `debugDefaultTargetPlatformOverride`).
- Flutter's built-in `.adaptive` constructors (`Switch.adaptive`, `CircularProgressIndicator.adaptive`, `showAdaptiveDialog`) cover the simple cases — wrap those too so feature code stays uniform.
- Keep these wrappers dumb and thin. They are the *only* files allowed to branch on platform.

Result: the agent builds a screen from `App*` widgets and it's correct on both platforms with zero per-feature platform code.

## Theming and design tokens

`MaterialApp` with **Material 3 `ThemeData`** for the Android surfaces, **`CupertinoTheme`** for the iOS ones, and a shared **`ThemeExtension`** carrying brand tokens both sides read.

**Rule: no literals in widgets.** Every color, spacing, radius, and text style comes from the theme or a token — never a raw `Color(0xFF…)` or a magic `16.0` in a `build()`.

```dart
// core/theme/app_tokens.dart
import 'package:flutter/material.dart';

@immutable
class AppTokens extends ThemeExtension<AppTokens> {
  const AppTokens({required this.brand, required this.gapMd, required this.radiusLg});
  final Color brand;
  final double gapMd;
  final double radiusLg;

  @override
  AppTokens copyWith({Color? brand, double? gapMd, double? radiusLg}) => AppTokens(
        brand: brand ?? this.brand,
        gapMd: gapMd ?? this.gapMd,
        radiusLg: radiusLg ?? this.radiusLg,
      );

  @override
  AppTokens lerp(AppTokens? other, double t) => other == null
      ? this
      : AppTokens(
          brand: Color.lerp(brand, other.brand, t)!,
          gapMd: lerpDouble(gapMd, other.gapMd, t)!,
          radiusLg: lerpDouble(radiusLg, other.radiusLg, t)!,
        );
}

// usage in a widget:
final tokens = Theme.of(context).extension<AppTokens>()!;
```

- `ThemeExtension` is the type-safe home for tokens Material's `ColorScheme`/`TextTheme` don't model. It survives light/dark and animates via `lerp`.
- A pure spacing scale may live as plain consts if you prefer (spacing rarely changes with theme); colors and typography belong in the theme.
- On iOS, native Cupertino widgets self-style from the system — so you lean on your tokens more for Android and for any custom (non-native) surfaces.

## Liquid Glass / native iOS material (young libraries — opt-in)

Flutter **paused** design-language updates in 2025 and core does **not** ship iOS 26 Liquid Glass; Flutter's own Cupertino widgets are pre-26 styling. Flutter renders its own pixels, so it never picks up the OS material for free. If the dev wants real Liquid Glass on iOS, the options are all **young, fast-moving community packages** — treat them as experimental and **verify current state before adopting**:

- `cupertino_native` / `cupertino_native_better` — bridge to real native iOS 26 components (platform channels / native views). Most accurate, heaviest (native-view embedding has compositing/scroll sharp edges).
- `cupertino_liquid_glass` — pure-Flutter approximation via `BackdropFilter` + `CustomPainter` + spring physics. No native bridge; works on Android too.
- `adaptive_platform_ui` — auto-renders native iOS 26 glass / Cupertino / Material by platform + version.

**If you adopt one, isolate it entirely behind `core/ui/`.** The glass lives inside `AppScaffold`/`AppNavBar`; no feature code imports the package. When Flutter ships official Liquid Glass support, you swap the implementation in `core/ui/` and nothing else changes. Model glass parameters (blur sigma, tint, opacity, border) as `AppTokens` fields so the material stays themeable.

## Widget organization

- `core/ui/` — adaptive primitives (`App*`) and shared design-system widgets used app-wide.
- `features/<feature>/presentation/widgets/` — leaf widgets specific to one feature.
- A widget used by two or more features graduates to `core/ui/`.

## Consumption and rebuilds (recap from SKILL.md)

- Widgets are `HookConsumerWidget` (or `ConsumerWidget` when no hooks needed).
- Hooks hold ephemeral widget-local state; Riverpod holds anything shared or longer-lived.
- Scope rebuilds with `ref.watch(provider.select(...))` — watch the slice, not the whole object.
- Split fat `build()`s into small `const` leaf widgets.
