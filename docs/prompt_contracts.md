# MiniMax H3 Prompt Contracts & Structure Guide

This document provides the complete structural specification for MiniMax H3 prompts across all supported generation modes.

---

## Contents

- [Overview](#overview)
- [Text-to-Video-Audio (T2VA)](#text-to-video-audio-t2va)
- [Reference-to-Video-Audio (Ref2VA)](#reference-to-video-audio-ref2va)
- [Image Alignment Modes (I2VA, FL2VA, L2VA)](#image-alignment-modes-i2va-fl2va-l2va)
- [Chained Multishot Mode](#chained-multishot-mode)
- [Multi-Shot Timeline Formatting](#multi-shot-timeline-formatting)
- [Frame Grid Math & Duration Conventions](#frame-grid-math--duration-conventions)
- [Adaptive Description Budget](#adaptive-description-budget)

---

## Overview

MiniMax H3 is an audiovisual diffusion model trained on strictly segmented, section-based prompt contracts. Providing text in the exact structural format expected by the model maximizes visual quality, identity consistency, motion coherence, and audio/lip synchronization.

| Mode | Input Reference Media | Required Output Sections |
|---|---|---|
| `t2va` | None (pure text) | `integrated_multimodal_description:`, `overall_soundscape:`, `non_diegetic_music:` |
| `ref2va` | 1–12 images, videos, audio | `subject_definitions:`, `summary:`, `retention_analysis:`, `detailed_description:`, `overall_soundscape:`, `non_diegetic_music:` |
| `i2va` | Exact first frame | First-frame alignment sentence + 3 base sections |
| `fl2va` | Exact first & last frames | First-and-last-frame alignment sentence + 3 base sections |
| `l2va` | Exact last frame | Last-frame alignment sentence + 3 base sections |
| `chained_multishot` | Any / none | Canonical JSON array of autonomous prompts: `{"prompts": [...]}` |

---

## Text-to-Video-Audio (T2VA)

T2VA generates video and audio directly from text without source media references.

### Structure

```text
integrated_multimodal_description:
[Shot 1] The scene opens on a bustling Tokyo street at dusk. Warm incandescent streetlamps illuminate the wet asphalt, reflecting neon signage from surrounding storefronts. A woman in a dark trench coat walks forward through the crowd with measured steps. The camera tracks smoothly backwards in front of her at eye level. She (S1) looks towards the camera and says calmly: <d>[Japanese] 雨が降ってきたね。</d>.

overall_soundscape:
The continuous sound of distant city traffic, wet tires rolling on pavement, and a gentle ambient drizzle. Footsteps create crisp foley against the wet ground. The single tagged line is the only intelligible speech.

non_diegetic_music:
A sparse, atmospheric synth drone with subtle low-frequency pulses and restrained harmonic motion.
```

---

## Reference-to-Video-Audio (Ref2VA)

Ref2VA binds connected assets (images, videos, audio tracks) to reusable on-screen entities, motion patterns, and vocal timbres.

### The 6-Block Anatomy

1. **`subject_definitions:`**  
   Declares each `<Subject N>` or modality label with its provenance (e.g. `<Subject 1> is the woman from <Picture 1>`).
2. **`summary:`**  
   Declares bracketed task types (e.g. `[reference generation]`, `[video editing]`, `[audio reference]`) and the overall scene objective.
3. **`retention_analysis:`**  
   Defines the exact preservation policy for each reference (`fully_preserved`, `partially_preserved`, `attribute_transfer`, `weak_reference`, `fully_copy`, `partially_copy`, `reference`).
4. **`detailed_description:`**  
   The core visual and timeline narrative, organized by sequential `[Shot N]` markers with speaker IDs `(S1)`, actions, lighting, camera movement, and `<d>[Language] spoken text</d>` dialogue blocks.
5. **`overall_soundscape:`**  
   1–4 continuous English sentences describing ambient environmental sound bed, diegetic foley, and acoustic presence.
6. **`non_diegetic_music:`**  
   1–3 English sentences describing non-diegetic background score instrumentation, rhythm, and dynamics, or literal `N/A`.

### Example

```text
subject_definitions:
<Subject 1> is the adult detective from <Picture 1>; preserve his facial features, trimmed beard, and grey suit.
<Subject 2> is the antique pocket watch from <Picture 2>; preserve its gold casing and Roman numerals.
<Audio 1> is the supplied vocal track used exclusively as the voice-timbre and delivery reference for <Subject 1> (S1).

summary:
[reference generation + audio reference] Generate a cinematic investigation scene featuring <Subject 1> inspecting <Subject 2> with vocal delivery guided by <Audio 1>.

retention_analysis:
<Subject 1>: fully_preserved - maintain the exact facial identity and wardrobe from <Picture 1>.
<Subject 2>: fully_preserved - preserve the pocket watch geometry and markings from <Picture 2>.
<Audio 1>: reference - use exclusively as voice-timbre and cadence reference for <Subject 1> (S1).

detailed_description:
[Shot 1] The interior of a dimly lit study at night. Rain streams down the windowpane in the background, creating moving shadow patterns. <Subject 1> sits behind a mahogany desk illuminated by a warm brass desk lamp. He picks up <Subject 2> with his right hand, tilting it towards the light. The camera pushes in at slow speed with shallow depth of field. He (S1) speaks thoughtfully: <d>[English] Time is running out.</d>.

overall_soundscape:
The muffled sound of heavy rain against the window and the quiet tick-tick of the pocket watch mechanism. The single tagged line is the only intelligible speech.

non_diegetic_music:
N/A
```

---

## Image Alignment Modes (I2VA, FL2VA, L2VA)

For workflows where reference images act as literal frame anchors:

- **`i2va` (First Frame)**: Begins with the mandatory alignment sentence:  
  `The generated video aligns with the first frame in <Picture 1>.`  
  Moves continuously from the opening state into the requested action.
- **`fl2va` (First and Last Frame)**: Begins with:  
  `The generated video aligns with the first frame in <Picture 1> and the last frame in <Picture 2>.`  
  Constructs a progressive transition path that converges seamlessly on the final frame anchor.
- **`l2va` (Last Frame)**: Begins with:  
  `The generated video aligns with the last frame in <Picture 1>.`  
  Starts from a plausible preceding state and lands cleanly on the required final image.

---

## Chained Multishot Mode

`chained_multishot` generates independent, autonomous prompt items for multi-pass video generation workflows.

### Format

```json
{
  "prompts": [
    "Shot 1 complete autonomous prompt text...",
    "Shot 2 complete autonomous prompt text...",
    "Shot 3 complete autonomous prompt text..."
  ]
}
```

- Each prompt item is standalone English prose without section headers or timestamps.
- Continuity locks (`multishot_identity_lock`, `multishot_voice_lock`, `multishot_setting_lock`) repeat identity and style descriptions verbatim in every segment to maintain seamless visual continuity across generations.

---

## Multi-Shot Timeline Formatting

MiniMax H3 requires sequential shot headers with strictly increasing timestamps:

```text
[Shot 1] <no timestamp> The camera establishes the room in a wide static shot...
[Shot 2] At 00:04.000, The shot cuts to a medium close-up as the character approaches...
[Shot 3] At 00:08.500, The camera pushes in on the desk as the object is revealed...
```

- **Shot 1** never carries a timestamp.
- Subsequent shots use the exact syntax `[Shot N] At MM:SS.mmm, `.
- Transition cuts are phrased as `"the camera cuts to"`, `"the shot transitions to"`, or `"the shot switches to"`.

---

## Frame Grid Math & Duration Conventions

When downstream samplers require exact frame grid alignment:

$$\text{Valid Frame Counts} = 17 \times n + 5$$

At MiniMax H3's native **24 fps** convention:

| Frames ($17 \times n + 5$) | Effective Duration (s) |
|---|---|
| **107** ($n=6$) | 4.458 s |
| **124** ($n=7$) | 5.167 s |
| **141** ($n=8$) | 5.875 s |
| **175** ($n=10$) | 7.292 s |
| **243** ($n=14$) | 10.125 s |
| **311** ($n=18$) | 12.958 s |
| **345** ($n=20$) | 14.375 s |

When `frame_count > 0` is set, effective duration is calculated as `frame_count / 24` and overrides `duration_seconds`.

---

## Adaptive Description Budget

MiniMax H3 performs best when descriptive text matches its cross-attention window sweet spot (~600–1100 tokens):

This guarantees rich physical conditioning without attention overflow or drift.

---

## Proportional Resolution & Megapixel Math

MiniMax H3 prompt enhancer nodes output aligned integer dimensions (`width` and `height`) that calculate proportional pixel counts aligned to multiples of 16 for downstream video samplers:

$$\text{Total Pixels} = \text{target\_megapixels} \times 1,000,000$$
$$\text{Height } (H) = \sqrt{\frac{\text{Total Pixels}}{r}} \quad \text{and} \quad \text{Width } (W) = H \times r$$
$$\text{Aligned Dimension} = \max\left(16, \text{round}\left(\frac{\text{dim}}{16}\right) \times 16\right)$$

| Aspect Ratio ($r$) | `0.2` MP (Draft) | `0.3` MP (Light) | `0.5` MP (540p) | `0.0` (Default 720p) | `1.0` MP | `2.0` MP (1080p) |
|---|---|---|---|---|---|---|
| **`16:9`** ($1.778$) | `592 × 336` | `736 × 416` | `944 × 528` | **`1280 × 720`** | `1328 × 752` | `1888 × 1056` |
| **`9:16`** ($0.5625$) | `336 × 592` | `416 × 736` | `528 × 944` | **`720 × 1280`** | `752 × 1328` | `1056 × 1888` |
| **`1:1`** ($1.0$) | `448 × 448` | `544 × 544` | `704 × 704` | **`1080 × 1080`** | `1008 × 1008` | `1408 × 1408` |
| **`4:3`** ($1.333$) | `512 × 384` | `640 × 480` | `816 × 608` | **`960 × 720`** | `1152 × 864` | `1632 × 1216` |
| **`3:4`** ($0.75$) | `384 × 512` | `480 × 640` | `608 × 816` | **`720 × 960`** | `864 × 1152` | `1216 × 1632` |
| **`21:9`** ($2.333$) | `688 × 288` | `832 × 352` | `1088 × 464` | **`1680 × 720`** | `1536 × 656` | `2160 × 928` |

