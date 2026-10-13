# Motion

This is an account of why things move in a marketing video and how to judge whether a given movement is doing its job. Read it before planning a storyboard in Stage 3 and again before animating in Stage 6. The engine rules for Remotion are in [remotion.md](remotion.md); this file is about the decisions, which hold in any engine.

The numbers here are starting points with their reasons attached. When a number and its reason disagree in front of you, follow the reason.

## What changes when nobody is clicking

Most written advice about animation is about interfaces, where a person acts and the interface answers. There, motion is feedback. It has to be fast, because the person is waiting; it has to be interruptible, because they may change their mind; and it should go unnoticed, because they came to do a task.

A video has no user. Nothing is waiting on an answer, and the viewer cannot interrupt anything. What remains is the one property of motion that does not depend on interaction: the eye goes to whatever is moving. In a video, motion is how you decide what the viewer looks at and in what order. That is its whole job.

Three consequences follow, and most of this file is an elaboration of them.

**One thing moves at a time, and it is the thing to read next.** Two simultaneous movements split attention, and the viewer follows whichever is larger, which is rarely the one that matters. When everything moves, nothing is being pointed at.

**Nothing moves without a reason.** A background that drifts, a gradient that breathes, or a logo that pulses pulls the eye toward something with no content. Put the question to every movement: what does the viewer learn from it? Acceptable answers are narrow. It shows where a thing came from. It shows what changed. It shows what to look at now. It shows how a feature works. "It looks alive" is not on the list.

**The message lands while things are still.** People read during holds. Movement brings the eye to a place; the hold is where the viewer takes in what is there. A film that never stops moving has delivered attention to a series of places and given the viewer nothing at any of them.

## Holds, and why product videos are too fast

The author of a video knows what every frame says and therefore always underestimates how long a stranger needs. This is the most common failure in product video, and the fix is arithmetic.

Read the on-screen text aloud at an unhurried pace and time it. Hold the text for that long plus half a second. As a check, that comes to about three words per second plus the half second. A six-word headline needs roughly two and a half seconds of stillness after it has finished arriving.

A product action needs three beats: the cause, the result, and a hold on the result. The cursor arrives and clicks; the state changes; the changed state stays on screen long enough to be recognised. Cutting away at the moment of the click shows a hand moving and no outcome. The states that matter most to the story, such as a confirmation, a copied link, a permission granted, a message sent, get the longest holds.

This sets how much a video can carry. A six to ten second loop holds one idea. A twenty-five to thirty second film holds five or six beats and an end card. If the storyboard has more beats than the duration can hold at these rates, cut beats. Speeding up is not available, because the holds are what the viewer came away with.

## How long a movement takes

Interface durations of 150 to 300 ms are calibrated for something a person triggers many times a day on a small element. A video is watched once, on a larger canvas, with longer travel, so movements run somewhat longer. Only somewhat: the viewer is still waiting for the movement to end so they can read.

| Movement | Duration |
| --- | --- |
| A small element arriving (chip, label, icon) | 0.25–0.4 s |
| A headline, card, or panel arriving | 0.4–0.6 s |
| An element leaving | about 30% shorter than its arrival |
| A camera move or a large reposition | 0.6–1.2 s |
| A scene transition | 0.3–0.5 s |

Larger things and longer distances take more time, because the same duration over a greater distance is a higher speed, and speed is what reads as abrupt. Leaving is shorter than arriving because attention has already gone to what comes next. If a movement feels slow, it is slow; shorten it before changing anything else.

Write durations in seconds and multiply by the frame rate. A raw frame count is wrong the moment the frame rate changes.

## Easing is the character of the movement

The curve decides whether a movement looks designed. Linear interpolation between two positions looks mechanical because nothing in the physical world starts and stops instantly.

**Arriving: decelerate.** The element starts fast and settles. The reason is where the eye ends up: the resting position is what the viewer needs to register, and a decelerating curve spends most of its time near it. The standard keyword curves are too gentle to look intentional. Use a strong one such as `cubic-bezier(0.16, 1, 0.3, 1)` or `cubic-bezier(0.22, 1, 0.36, 1)`.

**Moving from one place to another on screen: accelerate, then brake.** A camera, a cursor, or a card changing position has mass, and it should gather speed and lose it. `cubic-bezier(0.65, 0, 0.35, 1)` is a good default, and `cubic-bezier(0.77, 0, 0.175, 1)` is firmer.

**Leaving: accelerate away.** Interface guidance forbids ease-in because a slow start delays feedback to a waiting user. Nobody is waiting here. An object that speeds up as it goes reads as departing, which is the point. Keep it short.

**Constant rate: linear.** Use it only where the movement represents time or a steady process: a progress bar, a ticker, a slow continuous camera drift, a turning object.

**Springs** suit things that should feel physical. Default to no overshoot. Bounce is a statement about personality, and on a product interface it makes the product look like a toy. If the brand is playful, allow overshoot on one element per scene and keep it small.

Pick one arrival curve, one travel curve, and two or three durations. Define them once as tokens beside the colors and use them everywhere. Motion is part of the brand in the same way type is: a developer tool moves quickly and stops cleanly, and a calm consumer product moves more slowly with softer curves. A film that mixes several motion characters reads as assembled from parts.

## Arriving and leaving

**Nothing arrives from nothing.** An element that scales up from zero appears to be created out of a point, which no real object does. Start at 95 to 97 percent of full size with zero opacity. The element has a shape from its first visible frame.

**Travel is short.** An arrival moves 8 to 24 px on a 1080 px canvas, scaled with the canvas. When an element slides in from off screen, the slide becomes the event and the content becomes its cargo. Reserve a full slide for the case where the direction is the information, such as a panel that belongs to the right edge.

**Things grow from where they come from.** A menu opens from its button. A callout extends from the thing it describes. A zoom moves toward the cursor. Set the transform origin to that source. An element that scales from its own centre while supposedly emerging from a control at its corner looks detached from the control, and the viewer loses the causal link you were trying to show.

**Split, then stagger.** Do not bring in a block as a single unit. Divide it into the parts the viewer reads separately, such as eyebrow, headline, supporting line, and action, and offset each by 60 to 100 ms in reading order. The stagger is a reading instruction. Keep the whole sequence inside about half a second, because a long cascade makes the viewer wait for the last piece.

**Parts of one object share one timing.** A card and its shadow, a panel and the dimming layer behind it, a cursor and the camera following it. Different curves or durations on parts of a single thing make it look as though it is coming apart.

**Leaving is quiet.** A small movement in the direction the element is going, a fade, and a shorter duration. Often the best exit is none: let the scene change remove it.

**Blur joins two states.** When one piece of content replaces another in the same place, a plain crossfade shows two overlapping things for a moment. Two to four pixels of blur at the midpoint makes the eye read one thing changing into another. More blur than that becomes an effect in its own right.

**Reveal by clipping.** To wipe in an image, sweep a highlight across a phrase, or compare before and after, animate a clipping rectangle over content that is already in its final position. Layout never shifts, and the edge of the reveal gives the eye a line to follow.

**Text arrives by line or by word.** Per-character animation turns a headline into a texture and delays the moment it can be read. The exception is text whose typing is the content, such as a prompt or a search query; type it at a pace a viewer can follow, with a cursor, and hold the finished text.

## Showing the product

Stage 4's rule carries over unchanged: anything the viewer must read is shown flat and head-on. Motion adds the camera.

**The camera does the pointing.** A full product screen at video size is unreadable, so move in. Zoom once toward the control that matters, hold while the action happens, follow the cursor to the next control at the same zoom, and pull back only when the screen is finished. Zooming in and out for each action makes the viewer rebuild their sense of where they are every time.

**The cursor and the camera share one path.** Define the cursor's positions over time once and derive the camera's focus from it. Two separately authored paths drift apart, and the camera ends up looking where the cursor is not.

**The cursor behaves like a hand.** It travels with an accelerate-and-brake curve, arrives, pauses for a beat, and then clicks. The control responds visibly to the press, for example by scaling to about 96 percent, and then the result appears. Without the pause the click is over before the viewer has found the cursor.

**The frame stays still.** Keep the logo, margins, and any caption fixed while the product moves inside its viewport. A stable frame is what makes the movement inside it readable, and it keeps the brand in every frame, including whichever one a platform picks as a thumbnail.

**Compressed time is a claim.** Shortening a sync or an install is ordinary editing, but invented counts and durations are still product claims. Keep them plausible, never present them as a benchmark, and note in the package README what is authored and what is real.

## Cuts and transitions

The cut is the default. It costs nothing and reads instantly. A transition is a statement about how two scenes relate, so use one only when the statement is true:

- A fade through the background says time has passed or the context has changed.
- A push or slide says the next thing sits beside this one.
- A shared element that carries across says this is the same thing, continuing.

Use one kind of transition per film. Do not let two readable interfaces overlap during a crossfade; for a moment the viewer sees two screens of text and can read neither. Fade the outgoing scene to the brand background before the incoming one appears.

## Depth and 3D

The test from Stage 4 decides this as well. If the viewer must read text in it, it stays flat. Depth is for objects, and for showing structure that a flat picture cannot.

There are three honest reasons to add depth. The product has layers and the viewer needs to see what sits above what. An object such as an app icon, a device, or a mark needs physical presence. Two things need to be connected by moving through the space between them. "It looks premium" is not a reason, and 3D done for that purpose is what viewers recognise as stock.

Reach for the cheapest depth that does the job:

1. **Planes.** Two or three flat layers that move at slightly different rates as the camera shifts, with shadows that agree. This explains layering completely and keeps every layer readable.
2. **Perspective on a flat element.** A CSS perspective with a rotation under about 12 degrees gives a card presence without making its content hard to read.
3. **Real geometry.** Use a 3D scene only when an object has form that must be seen turning.

When you do build a scene, the following keep it looking designed.

- **One light direction, shared with the flat layer.** If cards cast shadows down and to the right, the key light in the scene comes from the upper left. Disagreement between the two is the first thing that looks wrong, though viewers rarely name it.
- **A long lens.** A narrow field of view, around 25 to 35 degrees, keeps products from looking warped. Wide lenses exaggerate depth and suit architecture. Isometric views use an orthographic camera with no perspective at all.
- **Slow, small camera moves.** A few degrees of orbit or a short push over a whole scene. A quarter turn of an object takes two to three seconds. Fast camera moves in 3D are what make people feel unwell.
- **Matte materials in the brand palette.** Chrome, glass, and iridescence are the 3D equivalents of gradient text. One material family, one accent color.
- **Text lives outside the scene.** Keep headlines and labels in the flat layer above the 3D canvas so they stay sharp and stay in the brand typeface's own rendering.
- **Everything is a function of the frame.** No self-running shader clocks or animation mixers; see [remotion.md](remotion.md).

Motion blur belongs to fast movement over a long distance, where without it the object strobes. A 180 degree shutter is the natural look. Do not apply it to anything stationary or slow, and never to text that is being read.

## Where the video will be watched

**Most feeds play video muted.** The story has to work in silence. On-screen text carries it, and sound is an addition for the viewers who turn it on.

**The first frame is the thumbnail and the first second is the pitch.** Do not open on an empty background or a half-faded logo. Content is visible in frame one or arrives within the first third of a second, and the claim is on screen inside the first second.

**The last frame is what is left on screen.** End on a card with the logo and the URL and hold it for at least a second and a half.

**A loop must close.** For a short looping asset, the last frame matches the first, and the loop includes a hold so that it does not feel frantic on the third repetition.

**On a web page, respect the viewer's motion setting.** A video embedded in a site should not autoplay for someone who has asked for reduced motion. Provide a poster frame and a play control.

**Frame rate follows content.** Thirty frames per second is enough for text, fades, and slow moves. Use sixty when a cursor and a camera travel across an interface, where the extra frames keep fast movement from stuttering. Choose one per film.

## Judging motion

Motion cannot be judged from code, and it cannot be judged from stills. Stills verify layout at a moment. They say nothing about whether a movement is too fast, whether two things moved at once, or whether a hold was long enough.

- Step frame by frame through every arrival, exit, and transition. Look for two states visible at once, a pop on the first or last frame, a wrong origin, and properties that should move together finishing at different times.
- Watch at half speed, then at full speed at the size of a phone.
- Watch once from the start as a stranger would, and note every place where you could not finish reading.
- Look again after working on something else. Problems that were invisible while building are obvious on return.
- Then put it in front of the user, in the live preview, before exporting anything.

Questions to put to each scene:

- What is the one thing this scene says, and is it on screen, still, long enough to read?
- At each moment, what is moving, and is it the thing to look at next?
- Does every movement answer a question the viewer has?
- Does every action show its result, and is the result held?
- Would the scene lose anything if this movement were a cut?
- Does it use the same curves and durations as every other scene?
