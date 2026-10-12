---
name: marketing-assets
description: Build a repo's marketing asset pipeline end to end — on-brand templates from the logo, colors, and type already in the repo, then art, blank templates, copy, and rendered social and print assets, with a user review gate between each stage. Use when the user asks to create marketing assets, social posts, launch graphics, posters, banners, OG images, or a campaign for their product. Triggers on: marketing assets, social media posts, launch posts, Instagram, Twitter/X, LinkedIn, stories, posters, banners, OG image, campaign graphics, "make assets for the launch".
---

# Marketing Assets

The pipeline has two layers. **Templates** (layout code, brand tokens, vendored fonts, art renders, content JSON, tests) are checked in. **Assets** (rendered SVG/PNG/PDF) are gitignored output, because anyone can regenerate them and binaries bloat history. Never commit rendered assets.

Work the stages in order. Each ends at a review gate: show the result, ask the user (with a structured multiple-choice question tool when the agent has one), and wait for the answer before the next stage. Skipping a gate produces a hundred polished assets built on a direction nobody agreed to.

## Stage 1 — Read the brand from the repo

Collect before asking anything, so questions are concrete:

- Logo, app icon, wordmark (SVG preferred).
- Brand colors from the landing page or tokens.
- Typeface and weights. Vendor the font file into the marketing package so rendering never depends on system fonts.
- Taglines, headline style, and accent treatment from the landing hero.
- Docs and README. Every product claim in copy must trace to one of these.
- Product screens, if any exist: a dev server, proof pages, or screenshots. Note them; whether to use them is decided in Stage 4.

Report what you found in one short list and name what is missing.

## Stage 2 — Direction (gate)

Ask these together in one round of up to four questions, then follow up on anything vague:

1. **Purpose** — launch, feature series, hiring, event, ongoing social. Decides the post list.
2. **Audience** — who reads it, on which platform.
3. **Direction** — 2–3 concrete options with previews ("dark product-led", "light editorial", "photo-led"), never an open "what vibe?".
4. **Formats** — multi-select, default all:

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

Every template that ships a vertical format also ships a horizontal one. Users always ask for it later.

## Stage 3 — Templates and blanks (gate)

Build the template layer, then render every template with sample copy and a dashed, measured outline where art goes. Ask the user to review the blanks before any art or copy exists; layout fixes are cheapest here.

- **Art slots depend only on the format, never on the art**, so any art fills any slot without moving copy, and the blanks state exact slot sizes. Test this.
- **Outline text to paths** with the vendored font, so SVGs look identical in browsers, Figma, and Illustrator.
- **One shared frame** (logo top, tagline and URL bottom) on every template, so a feed reads as one brand.
- **Headlines shrink to fit** their box rather than overflow. Test it.
- **Export PNGs at 2× the canvas.** At 1× the embedded art looks soft on high-density screens next to the SVG, which browsers draw at full density. Platforms downscale 2× cleanly.

## Stage 4 — Art direction (gate)

Propose the art per post and ask for the user's ideas before rendering. Pick the style by what the art must do:

```
Must the viewer read text in it (UI, messages, settings)?
├── Yes → flat and head-on: product screens or drawn UI on raised cards
└── No, it is an object (device, server, app icon, code mark) → isometric 3D is fine
```

Angled screens are unreadable and make UI look like paper. Never put a product screen on an isometric plane.

- **Capture the real product only when the post's flow needs it**, such as a feature explainer whose point is what the screen shows. Brand, launch, statement, and quote posts often need no screenshot at all. When you do capture, run the app with invented fixture data (fictional company and people), a fixed clock, and a fixed theme, and never capture real customer data.
- **Crop to the band that tells the story.** Social art slots run about 2:1 to 2.7:1; a whole page shrunk into one is unreadable. Fade the cut edges with a mask.
- **Point at what matters** with callout chips styled like the product's own UI, sitting beside or breaking the card edge. A chip never covers the text it explains.
- **Render at 2× the largest slot** the art fills, trimmed to its visible bounds.
- **Show the product, not a metaphor.** Padlocks, funnels, pawn figures, and floating blank bubbles read as stock filler.

## Stage 5 — Copy (gate)

Write copy into one content JSON per campaign, render, and have the user review copy separately from art. Before drafting headlines, read [references/copy-patterns.md](references/copy-patterns.md) for the headline moves and which one fits each kind of post.

- **Every product claim traces to the docs.** List any claim you could not source and ask.
- **A problem post carries its solution.** "You become the bottleneck" advertises the pain; "Stop being the bottleneck. *Let your team answer.*" sells the fix. The art shows the problem being solved too.
- **Never invent testimonials, quotes, customer logos, or numbers.** Ask for a real quote and photo, and confirm the person approved it.
- **Cut AI tells**: delve, leverage, seamless, robust, unlock, game-changer, "not just X, it's Y", rule-of-three lists, stacked fragments. Specific beats clever: name the real feature, the real limit.

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

**Composition**
- Text sits beside or below art, never over a busy image.
- Asymmetric splits (a wider art column against a narrower copy column) read as designed; equal halves read as static.
- One distinctive brand signature repeated across the set beats several effects used once.
- Squint test before showing anything: could this post belong to any other product? If only the logo ties it to this one, add something specific to the product: its real UI, its own language, or a concrete detail from the docs.

## Stage 6 — Render and verify

1. Run the tests: canvas size for every post × format, slot stability, headline fit.
2. Render everything and write a preview `index.html` per campaign showing every post in every format.
3. Look at the renders yourself: at least one vertical and one horizontal format per post, zoomed into the art. A render that ran without errors proves nothing about how it looks.
4. Commit templates, content, fonts, art renders, and tests. Confirm the asset output is gitignored and nothing under it is staged.
5. Tell the user which folders and preview pages to open, and name any format you rendered but did not look at.
