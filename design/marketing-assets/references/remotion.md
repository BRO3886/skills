# Remotion

Motion assets in this pipeline are built with [Remotion](https://www.remotion.dev): React components rendered frame by frame in a headless browser and encoded to video. Read this before scaffolding or editing the video package. The decisions about what should move and why are in [motion.md](motion.md).

This file holds the rules that matter for this pipeline and the failures a shipped product film ran into. It was written against Remotion 4.0.53x. Remotion publishes its own agent skills (`remotion-best-practices` and the skills it routes to); when they are installed, load them for API detail and treat them as the authority where they differ from this file. Use `npx remotion add <package>` to install any `@remotion/*` package, so that its version matches the one already in the project. Remotion has its own license terms for companies; point the user to them before a commercial project depends on it.

## Where the video package lives

Keep it beside the static asset package, for example `marketing/video`, with its own `package.json` and tests. It shares three things with the static side and should read them from one place, never copy them:

- brand tokens (colors, type, and the motion tokens below),
- the content JSON, which holds every word on screen with a pointer to its source in the docs,
- the vendored font.

Checked in: source, content, tests, the lockfile, and the scripts that prepare assets. Ignored: files generated into `public/`, the bundle, stills, and every rendered video.

## Every frame is a pure function of its frame number

This is the rule everything else follows from. Remotion does not record a page while it plays. It opens several browser tabs, asks each for arbitrary frames out of order, and screenshots them. Anything that depends on real time passing has no defined value at "frame 412" and comes out differently in each tab, which shows up as flicker or as animations frozen at their first frame.

So, inside a composition:

- No CSS `transition` or `animation`, and no Tailwind animation classes. They run on the browser's clock.
- No `setTimeout`, `setInterval`, `requestAnimationFrame`, or `Date.now()`.
- No `Math.random()`. Use `random(seed)` from `remotion`, which returns the same value for the same seed in every tab.
- No animation libraries that keep their own clock, unless they can be driven by a frame value.
- In a 3D scene, no `useFrame()` from React Three Fiber, no self-advancing shader uniforms, and no animation mixers running on their own.

Every animated value is computed from `useCurrentFrame()`.

## Timing in code

Take `fps` from `useVideoConfig()` and write every time as seconds multiplied by `fps`. Clamp both ends of every interpolation; unclamped, a value keeps going past its target for the rest of the scene.

Define the motion tokens once, next to the colors, so that every scene moves with the same character:

```tsx
import { Easing } from "remotion";

export const motion = {
  arrive: Easing.bezier(0.16, 1, 0.3, 1),
  travel: Easing.bezier(0.65, 0, 0.35, 1),
  leave: Easing.bezier(0.5, 0, 0.75, 0),
  quick: 0.3,
  standard: 0.5,
  slow: 0.9,
  stagger: 0.08,
} as const;
```

An arrival, with the stagger expressed as a delay in seconds:

```tsx
import type { ReactNode } from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { motion } from "./motion";

export function Arrive({
  at = 0,
  children,
}: {
  at?: number;
  children: ReactNode;
}) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const range = [at * fps, (at + motion.standard) * fps];
  const options = {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: motion.arrive,
  } as const;

  return (
    <div
      style={{
        opacity: interpolate(frame, range, [0, 1], options),
        scale: interpolate(frame, range, [0.96, 1], options),
        translate: interpolate(frame, range, ["0px 16px", "0px 0px"], options),
      }}
    >
      {children}
    </div>
  );
}
```

Notes on that code:

- Use the individual `scale`, `translate`, and `rotate` properties in place of a composed `transform` string. They are easier to read, and Remotion Studio can edit them.
- `interpolate()` accepts more than two keyframes, so an arrival, a hold, and an exit can be one call: `interpolate(frame, [0, 0.5 * fps, 3 * fps, 3.3 * fps], [0, 1, 1, 0], …)`.
- For large scale changes, pass `output: "perceptual-scale"` so the growth looks even to the eye.
- `spring({ frame, fps, config: { damping: 200 } })` gives a physical arrival with no overshoot. Lower damping adds bounce; see [motion.md](motion.md) for when that is appropriate.

## Structure of a film

- **One composition per format, same duration and frame rate.** Register the landscape, vertical, and square versions as separate `<Composition>` entries that render the same film component. Derive layout from `useVideoConfig()` in one layout hook, so scenes ask the hook where the art and the copy go and never branch on format themselves.
- **One component and one file per scene.** Register each scene as its own composition as well, so it can be previewed and reviewed in isolation.
- **Assemble scenes with `<TransitionSeries>`** from `@remotion/transitions`, or `<Series>` when every join is a cut. Give each sequence a `name`, an inline `durationInFrames`, and `premountFor={fps}` so media and fonts are ready before the scene starts.
- **Transitions overlap, so they shorten the film.** Total duration is the sum of the scene durations minus the sum of the transition durations. Compute it once and assert it in a test.
- **Copy comes from the content JSON**, never from string literals in scene files.
- **Fonts are loaded explicitly.** Put the vendored file in `public/` and load it with `loadFont()` from `@remotion/fonts` and `staticFile()`. Measure and fit headlines with `fitText()` from `@remotion/layout-utils`, and only after the font has loaded, or the measurement is taken against a fallback face.
- **Assets are referenced with `staticFile()`** from `public/`. If logos and icons live elsewhere in the repo, copy them in with a prepare script that the dev, test, and export scripts all run first.
- **Product screens are authored components** with invented fixture data, a fixed clock, and a fixed theme, as Stage 4 requires. They are not recordings of the running app.

A film whose scenes hand off by fading through the brand background, so that two interfaces are never readable at once:

```tsx
import {
  TransitionSeries,
  linearTiming,
  type TransitionPresentationComponentProps,
} from "@remotion/transitions";
import { AbsoluteFill, interpolate, useVideoConfig } from "remotion";

function Handoff({
  children,
  presentationDirection,
  presentationProgress,
}: TransitionPresentationComponentProps<Record<string, never>>) {
  return (
    <AbsoluteFill
      style={{
        opacity: interpolate(
          presentationProgress,
          [0, 0.5, 1],
          presentationDirection === "entering" ? [0, 0, 1] : [1, 0, 0],
        ),
      }}
    >
      {children}
    </AbsoluteFill>
  );
}

const handoff = { component: Handoff, props: {} };

export function Film() {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ backgroundColor: "#15171B" }}>
      <TransitionSeries>
        <TransitionSeries.Sequence
          name="Problem"
          durationInFrames={4 * fps}
          premountFor={fps}
        >
          <Problem />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition
          presentation={handoff}
          timing={linearTiming({ durationInFrames: Math.round(0.4 * fps) })}
        />
        <TransitionSeries.Sequence
          name="End card"
          durationInFrames={3 * fps}
          premountFor={fps}
        >
          <EndCard />
        </TransitionSeries.Sequence>
      </TransitionSeries>
    </AbsoluteFill>
  );
}
```

## One camera, driven by the cursor

For product walkthroughs, describe the cursor as a list of `[seconds, x, y]` points and interpolate its position from the frame. Compute the camera's focus from the same function, clamp it so the viewport never shows outside the product, and apply the zoom and offset to a single wrapper around the product. Because both read one path, they cannot disagree. Keep the branded frame outside that wrapper so it does not move.

Wrap the moving product in `<CameraMotionBlur>` from `@remotion/motion-blur` with `shutterAngle={180}`. Set `samples` to about 10 while the camera is travelling and to 1 while it is still. Blur samples on a stationary view only soften the text and multiply render time.

## 3D

Use `@remotion/three`. Wrap the scene in `<ThreeCanvas>` with explicit `width` and `height` from `useVideoConfig()`, and light it; an unlit scene renders black. Any `<Sequence>` inside the canvas needs `layout="none"`. Drive every rotation, position, and uniform from `useCurrentFrame()`. Keep headlines and labels in ordinary DOM above the canvas.

## Timing has more than one home

A film's duration ends up written in several places: the composition registrations, the scene durations, the standalone scene compositions, the tests, the README, and the frame numbers the stills script captures. When pacing changes, find all of them with one search before editing any, and change them together. A retime that updates the film and leaves the stills script pointing at old frame numbers produces a review gallery of the wrong moments, and nobody notices until the export.

## Preview before anything is rendered

Start Studio as soon as the project runs, and keep it running:

```bash
npx remotion studio --no-open
```

Open the URL it prints. A composition is addressable at `/<composition-id>`. The user reviews motion here, scrubbing and replaying, and this is the Stage 6 gate. Do not export video until they have approved the motion in Studio. Rendering is slow, and a rendered file invites review of the wrong thing.

For your own checks while building, render stills, which is fast:

```bash
npx remotion still <composition-id> out/frame.png --frame=120
npx remotion render <composition-id> out/frames --frames=0,30,90 --image-format=png
```

Keep a stills script in the package that renders one named frame per scene for every format, plus a frame from the middle of each transition and each camera move, and writes a gallery page. It is the storyboard gate in Stage 3 and the layout check in Stage 7.

## Tests

Tests run against the real renderer, not a model of it. Bundle the project with `@remotion/bundler`, list compositions with `getCompositions()` from `@remotion/renderer`, and assert for each format the width, height, frame rate, and duration the user agreed to. Assert that every format has the same duration.

Add pixel tests for properties that must hold through motion. Render a resting frame and a mid-zoom frame with `renderStill()`, then compare the region containing the logo; it must be identical. Check that the product viewport keeps its margins at full zoom. These catch a camera that has started moving the frame, which a still gallery can miss.

Watch each new test fail before trusting it: break the property, run the test, restore it.

Before a full export, run a preflight that resolves every real input, such as asset paths, font files, and tokens read from the product, and writes nothing. Tests that use fixtures cannot see that a real file has moved.

## Export

Export once the motion is approved. Bundle first, then render each format from the bundle:

```bash
npx remotion bundle
npx remotion render build <composition-id> out/<name>-16x9.mp4 --codec=h264 --crf=18 --pixel-format=yuv420p
```

H.264 with `yuv420p` plays everywhere, including the platforms that reject other pixel formats. For a video with a transparent background, render ProRes 4444 with `--image-format=png --pixel-format=yuva444p10le --codec=prores --prores-profile=4444`, or a WebM for the web.

A conservative `remotion.config.ts` for interface-heavy films:

```ts
import { Config } from "@remotion/cli/config";

Config.setChromeMode("headless-shell");
Config.setVideoImageFormat("png");
Config.setDisableSharedMemoryCapture(true);
Config.setDisallowParallelEncoding(true);
Config.setConcurrency(2);
Config.setOverwriteOutput(true);
```

PNG capture keeps small interface text free of JPEG artefacts. The low concurrency and separate encoding trade speed for frames that are captured reliably.

Then verify the encoded file, because the file is what ships and it can differ from every still you looked at:

```bash
ffprobe -v error -show_entries stream=codec_name,pix_fmt,width,height,r_frame_rate,nb_frames -of default=nw=1 out/<name>.mp4
ffmpeg -v error -i out/<name>.mp4 -f null -
ffmpeg -v error -i out/<name>.mp4 -vf "fps=1,scale=480:-1,tile=6x5" -frames:v 1 out/<name>-sheet.png
```

The first confirms codec, pixel format, size, frame rate, and frame count. The second decodes every frame and prints nothing if the file is sound. The third writes a contact sheet with one frame per second; look at it, and extract and look at frames from the middle of each transition and camera move as well.

## Failures seen in practice

| Symptom | Cause | Fix |
| --- | --- | --- |
| Stills are correct, but the MP4 has tiled layouts or missing interface | A browser executable override pointed sequential capture at a different Chrome build | Remove the override, use the configured headless shell with PNG capture, then scan decoded frames |
| An animation is frozen or flickers in the render but plays in a normal browser | It runs on a CSS or timer clock | Recompute it from `useCurrentFrame()` |
| Headline wraps differently in the render than in preview | Text was measured before the font loaded | Load the font first, then measure |
| Content pops in on the first frame of a scene | Media or fonts were not ready | Add `premountFor` to the sequence and its timed children |
| A value keeps drifting after its animation ends | Interpolation is not clamped | Clamp both ends |
| The film is shorter than the sum of its scenes | Transition overlaps were not subtracted | Total is scenes minus transitions; assert it |
| After a retime, tests pass but the gallery shows the wrong moments | Frame numbers were duplicated and only some were updated | Search for every timing surface and change them together |
| The film feels rushed though each animation is correct | Holds are too short | Lengthen holds at results; slow the typing and the cursor before touching curves |
| Studio fails to start with a file-watcher limit error | Too many watched files | Retry with `--webpack-poll 1000` |
