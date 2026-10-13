---
name: marketing-assets
description: Build a repo's marketing asset pipeline end to end, for stills and for motion — on-brand templates from the logo, colors, and type already in the repo, then art, blank templates, copy, and rendered social and print assets, plus product videos and animated posts built with Remotion, with a user review gate between each stage. Use when the user asks to create marketing assets, social posts, launch graphics, posters, banners, OG images, a launch or explainer video, an animated post, or a campaign for their product. Triggers on: marketing assets, social media posts, launch posts, Instagram, Twitter/X, LinkedIn, stories, reels, shorts, posters, banners, OG image, campaign graphics, launch video, product video, demo video, explainer, onboarding film, animated post, motion graphics, Remotion, "make assets for the launch", "make a video for the launch".
---

# Marketing Assets

The pipeline has two layers. **Templates** (layout code, brand tokens, vendored fonts, art renders, content JSON, scene components, tests) are checked in. **Assets** (rendered SVG/PNG/PDF and every exported video) are gitignored output, because anyone can regenerate them and binaries bloat history. Never commit rendered assets.

It produces two kinds of output from one brand layer. **Stills** are posts, banners, and print. **Motion** is video built with Remotion: product films, feature explainers, and animated versions of posts. Both read the same tokens, the same content JSON, and the same font, so a campaign looks like one thing whether it moves or not.

Work the stages in order. Each ends at a review gate: show the result, ask the user (with a structured multiple-choice question tool when the agent has one), and wait for the answer before the next stage. Skipping a gate produces a hundred polished assets built on a direction nobody agreed to. A stills-only campaign skips Stage 6; a motion-only campaign still passes through every other stage.

References, read at the stage that names them:

- [references/what-makes-copy-work.md](references/what-makes-copy-work.md): why headlines work or fail.
- [references/motion.md](references/motion.md): why things move in a video, pacing, easing, the product camera, depth and 3D.
- [references/remotion.md](references/remotion.md): the engine rules, project structure, tests, and export for Remotion.

## Stage 1 — Read the brand from the repo

Collect before asking anything, so questions are concrete:

- Logo, app icon, wordmark (SVG preferred).
- Brand colors from the landing page or tokens.
- Typeface and weights. Vendor the font file into the marketing package so rendering never depends on system fonts.
- Taglines, headline style, and accent treatment from the landing hero.
- Docs and README. Every product claim in copy must trace to one of these.
- Product screens, if any exist: a dev server, proof pages, or screenshots. Note them; whether to use them is decided in Stage 4.
- How the product already moves: transition durations and easing in the app or the landing page. A video should move the way the product does.
- An existing Remotion package, if there is one. Extend it; never scaffold a second.

Report what you found in one short list and name what is missing.

## Stage 2 — Direction (gate)

Ask these together in one round of up to four questions, then follow up on anything vague:

1. **Purpose** — launch, feature series, hiring, event, ongoing social. Decides the post list.
2. **Audience** — who reads it, on which platform.
3. **Direction** — 2–3 concrete options with previews ("dark product-led", "light editorial", "photo-led"), never an open "what vibe?".
4. **Output and formats** — stills, motion, or both, then the formats, multi-select, default all for the chosen output.

Stills:

| Format | Size | Use |
| --- | --- | --- |
| square | 1080 × 1080 | Instagram, LinkedIn feed |
| portrait | 1080 × 1350 | Instagram feed 4:5 |
| story | 1080 × 1920 | Stories, Reels, TikTok; keep content out of top 200 / bottom 250 px |
| landscape | 1600 × 900 | X, LinkedIn posts |
| og | 1200 × 630 | Link previews |
| x-header / linkedin-banner | 1500 × 500 / 1584 × 396 | Profile headers; text on the right, the avatar covers the lower left |
| avatar | 800 × 800 | Profile picture |
| poster-a / poster-a-landscape / poster-2x3 | A3 at 150 dpi / 24 × 36 in | Print, with PDF |

Motion:

| Format | Size | Use |
| --- | --- | --- |
| video-landscape | 1920 × 1080 | X, LinkedIn, YouTube, site hero |
| video-vertical | 1080 × 1920 | Reels, Shorts, TikTok, Stories; same safe margins as story |
| video-square | 1080 × 1080 | Feed posts |

Every template that ships a vertical format also ships a horizontal one. Users always ask for it later. For motion, every format of a film has the same duration and frame rate.

When motion is chosen, follow up on three things before Stage 3:

- **Length.** A 6–10 second loop carries one idea. A 15–30 second film carries five or six beats and an end card. Anything longer is a walkthrough and needs a script first.
- **Sound.** Silent by default, because feeds play muted. Ask before adding music or voice.
- **What it must show.** The one action or result the viewer should remember.

## Stage 3 — Templates and blanks (gate)

Build the template layer, then render every template with sample copy and a dashed, measured outline where art goes. Ask the user to review the blanks before any art or copy exists; layout fixes are cheapest here.

- **Art slots depend only on the format, never on the art**, so any art fills any slot without moving copy, and the blanks state exact slot sizes. Test this.
- **Outline text to paths** with the vendored font, so SVGs look identical in browsers, Figma, and Illustrator.
- **One shared frame** (logo top, tagline and URL bottom) on every template, so a feed reads as one brand.
- **Headlines shrink to fit** their box rather than overflow. Test it.
- **Export PNGs at 2× the canvas.** At 1× the embedded art looks soft on high-density screens next to the SVG, which browsers draw at full density. Platforms downscale 2× cleanly.

For motion, the blank is a **storyboard**, and it is reviewed as stills before anything is animated. Read [references/motion.md](references/motion.md) first.

- Write the scene list: for each scene, the one thing it says, what the viewer sees, the action and its visible result, and its duration in seconds.
- Check the arithmetic. Each line of on-screen text gets its read-aloud time plus half a second of stillness, and each action gets a held result. If the beats do not fit the agreed length, cut beats; do not speed up.
- Scaffold the Remotion package per [references/remotion.md](references/remotion.md), with every format registered and the shared frame in place, and render one still per scene per format with placeholder art.
- Show the storyboard and the stills together. Retiming a list is free; retiming a finished film touches every scene.

## Stage 4 — Art direction (gate)

Propose the art per post and ask for the user's ideas before rendering. Pick the style by what the art must do:

```
Must the viewer read text in it (UI, messages, settings)?
├── Yes → flat and head-on: product screens or drawn UI on raised cards
└── No, it is an object (device, server, app icon, code mark) → isometric 3D is fine
```

Angled screens are unreadable and make UI look like paper. Never put a product screen on an isometric plane. The same test holds in motion: a screen the viewer must read stays flat while the camera moves over it, and real 3D is for objects that have a form worth turning.

- **Capture the real product only when the post's flow needs it**, such as a feature explainer whose point is what the screen shows. Brand, launch, statement, and quote posts often need no screenshot at all. When you do capture, run the app with invented fixture data (fictional company and people), a fixed clock, and a fixed theme, and never capture real customer data.
- **In a film, product screens are authored components**, built from the product's own tokens with the same fixture data. A screen recording cannot be retimed, restyled, or reframed for a vertical format, and it leaks whatever was on screen.
- **Crop to the band that tells the story.** Social art slots run about 2:1 to 2.7:1; a whole page shrunk into one is unreadable. Fade the cut edges with a mask.
- **Point at what matters** with callout chips styled like the product's own UI, sitting beside or breaking the card edge. A chip never covers the text it explains.
- **Render at 2× the largest slot** the art fills, trimmed to its visible bounds.
- **Show the product, not a metaphor.** Padlocks, funnels, pawn figures, and floating blank bubbles read as stock filler.

## Stage 5 — Copy (gate)

Write copy into one content JSON per campaign, render, and have the user review copy separately from art. Before drafting headlines, read [references/what-makes-copy-work.md](references/what-makes-copy-work.md). It explains why headlines work or fail, and the questions to put to every draft before showing it.

- **Every product claim traces to the docs.** List any claim you could not source and ask.
- **A problem post carries its solution.** "You become the bottleneck" advertises the pain; "Stop being the bottleneck. *Let your team answer.*" sells the fix. The art shows the problem being solved too.
- **Never invent testimonials, quotes, customer logos, or numbers.** Ask for a real quote and photo, and confirm the person approved it.
- **Cut AI tells**: delve, leverage, seamless, robust, unlock, game-changer, "not just X, it's Y", rule-of-three lists, stacked fragments. Specific beats clever: name the real feature, the real limit.
- **In a film, the words on screen are the script.** One line per scene, short enough to read in the hold the storyboard gives it. The film must make sense with the sound off.
- **What a film shows is a claim too.** Compressed time, invented counts, and authored screens are ordinary, but each one is recorded in the package README, and nothing is presented as a benchmark or as a recording of a live system.

## Stage 6 — Motion (gate)

Animate the approved storyboard. Read [references/motion.md](references/motion.md) for the decisions and [references/remotion.md](references/remotion.md) for the engine before writing a scene.

- **Open the live preview first and keep it open.** Start Remotion Studio as soon as the project runs. The user watches and steers there.
- **Animate one scene to the standard, show it, then do the rest.** The first scene fixes the motion tokens (curves, durations, stagger) for the whole film.
- **Every animated value is a function of the frame.** No CSS transitions or animations, no timers, no unseeded randomness. They flicker or freeze in the render.
- **Do not export video at this gate.** The user approves motion in Studio, by scrubbing and replaying. A rendered file is slow to make and invites review of the wrong thing.

The gate is the user watching the whole film in the preview, in at least one vertical and one horizontal format.

## Design rules

These apply in every stage.

**Color**
- Work in oklch. Lightness is perceptual there, so contrast and tints become arithmetic.
- Contrast lives in the lightness gap: on a background above L 0.85 text sits at L 0.45 or below; on one below L 0.25 text sits at L 0.75 or above. Fix failing pairs by moving L only.
- Build tints by lowering chroma on the brand hue, never by opacity, which goes grey.
- Neutrals carry a slight bias toward the brand hue; blue brands get cool greys. Never pure #808080.
- Desaturate the brand color 20–30% on dark backgrounds, or it vibrates.
- One accent color per post, used on one phrase of the headline.

**Surfaces**
- Raised cards get a stacked shadow: a 1px ring at ~5% black, a short soft shadow, and a long low-opacity one. One big drop shadow looks pasted on.
- On dark themes shadows vanish; replace them with a 1px white ring at ~9% opacity.
- Nested radii are concentric: inner radius = outer radius − padding. Copying the parent radius pinches the corners.
- Screenshots and photos get a 1px inner outline: black at 10% on light, white at 10% on dark. Never a tinted grey or the accent.
- Fade cropped content with a mask, not a colored gradient overlay, so it works on any background.
- One depth cue per surface. No glassmorphism, no glows behind the hero, no gradient text.

**Type**
- Display headlines: leading about 1.05, tracking slightly negative (around −0.04em). Small uppercase eyebrows: tracking positive (around +0.12em). Body: neither.
- Body and point text at leading 1.4–1.5, lines capped near 65 characters.
- At most three text sizes per post, all from one scale. Hierarchy comes from making the rest recede, not from making the headline louder.
- Balance headline lines and avoid a single stranded word. Use real punctuation: curly quotes, en dashes in ranges, the … character.
- Never use light weights at small sizes; they break up in print and on phones.
- In video, text is larger than on a page: on a 1080 px wide canvas a headline is at least 84 px and supporting text at least 44 px, kept 80 px from the sides and 100 px from the top and bottom.

**Composition**
- Text sits beside or below art, never over a busy image.
- Asymmetric splits (a wider art column against a narrower copy column) read as designed; equal halves read as static.
- One distinctive brand signature repeated across the set beats several effects used once.
- Squint test before showing anything: could this post belong to any other product? If only the logo ties it to this one, add something specific to the product: its real UI, its own language, or a concrete detail from the docs.

**Motion**
- One thing moves at a time, and it is the thing the viewer should read next. Nothing moves without a reason.
- The message lands in the holds. Text stays still for its read-aloud time plus half a second; every action shows its result and holds on it.
- Arrivals decelerate, on-screen travel accelerates then brakes, and only steady processes move at a constant rate. One arrival curve, one travel curve, two or three durations, defined once as tokens.
- Nothing scales up from zero or slides in from off screen. Start near full size, travel a short distance, and grow from the thing that caused it.
- The branded frame stays fixed while the product moves inside it. The cursor and the camera follow one path.
- A cut is the default. Use one kind of transition per film, and never let two readable screens overlap.
- The first frame has content, the last frame is the logo and URL held for a second and a half, and the film works muted.

## Stage 7 — Render and verify

Stills:

1. Run the tests: canvas size for every post × format, slot stability, headline fit.
2. Render everything and write a preview `index.html` per campaign showing every post in every format.
3. Look at the renders yourself: at least one vertical and one horizontal format per post, zoomed into the art. A render that ran without errors proves nothing about how it looks.

Motion, once Stage 6 is approved:

1. Run the tests against the real renderer: size, frame rate, and duration for every format, equal durations across formats, and the pixel checks that the frame holds still through camera moves.
2. Run the preflight that resolves real asset and font paths, then export every format as H.264 with `yuv420p`.
3. Verify the encoded files, not the stills: probe codec, size, frame rate, and frame count; decode every frame; write a contact sheet and look at it; extract and look at frames from the middle of each transition and camera move. An export can differ from every still you checked.
4. Watch each format through once at phone size before handing it over.

Then, for both:

1. Commit templates, content, fonts, art renders, scene components, and tests. Confirm the asset output is gitignored and nothing under it is staged.
2. Tell the user which folders, preview pages, and video files to open, and name any format you rendered but did not look at.
