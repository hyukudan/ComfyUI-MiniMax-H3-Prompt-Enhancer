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
- [Structured Planning Contracts](#structured-planning-contracts)
- [Camera Authority Contract](#camera-authority-contract)
- [Diagnostics and Prompt Coach](#diagnostics-and-prompt-coach)
- [Compatibility and No-Clobber Rules](#compatibility-and-no-clobber-rules)
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

The rendered H3 prompt remains section-based prose. Structured planning is a separate authoring layer:

- `media_manifest` v2 defines logical assets, subjects, appearance states, environments, generations, activation, and physical bindings;
- `shot_plan_json` v2 defines opening/action allocation, presence, reference uses, camera phases, and state transitions over time;
- `creative_treatment_json` v2 defines the canonical editable creative-treatment selection;
- `cinematography_json` v2 defines global camera/look defaults;
- `validation_report.diagnosticReport` reports typed configuration, output-quality, and Coach findings.

These layers do not add sections to the prompt sent to H3. They compile deterministically into the existing mode contract.

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
- In a v2 project, shots are grouped by `generationId`. Every generated array item remains autonomous, but each generation receives only its active logical references, physical input map, and resolved initial state.
- A v2 `shotsPackage` stores generation-level input/state/authority digests once and links shots to them by `generationId`; `MiniMaxH3ShotSelector` accepts both package v1 and v2.

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

Timeline formatting is the rendered output contract, not the shot-plan storage format. Shot-plan v1 keeps its established `description`, timing, transition, scale, angle, and motion fields. Shot-plan v2 uses `openingState` plus `action`, groups timing per generation, and stores `cameraEnd` as a sparse delta from `cameraStart`. Both compile into the same required H3 timeline syntax.

---

## Structured Planning Contracts

### Media project v2

`media_manifest` v2 is the canonical project library. Stable logical IDs are never replaced by physical H3 labels. A binding derives `<Picture N>`, `<Video N>`, or `<Audio N>` independently for each generation.

The manifest is metadata, not a media transport. **Add reference** registers a logical reference but does not upload a file or produce a tensor. The physical picture, video, or audio must be connected to the H3 generation node through its normal media input; the generation binding declares which logical reference that physical slot fulfills. The enhancer continues to output prompt text and metadata only, with no media output port.

The project contains:

- logical `assets` with type, availability, description/analysis, transcript, audio mode, and optional explicit video-camera transfer;
- `subjects` with stable H3 index, identity facts/assets, a base appearance state, and an acyclic appearance-state graph;
- `environments` with permanent facts, bounded-role picture views, a default state, and an acyclic temporary-state graph;
- ordered `generations` with automatic/explicit activation, exclusions, physical bindings, and initial subject/environment state policies.

Activation and dependency closure are deterministic. A subject activates required identity assets and its active appearance source. An environment activates selected views. A referenced soundtrack or camera-transfer video activates its required media. Excluding a mandatory dependency is an error rather than permission to drop it.

The active asset set and binding set must match within a valid generation. Per-type slots and limits are enforced; the same physical slot can be reused by a different asset in another generation.

See the normative [`media_manifest_v2.schema.json`](schemas/media_manifest_v2.schema.json) and the operational [Prompt Studio guide](prompt_studio.md).

### Shot plan v2

`shot_plan_json` v2 is the temporal source of truth and supports up to 64 shots. Each shot has a stable ID, a valid `generationId`, and an `action`; optional structured fields include:

- `openingState`;
- automatic or exact per-generation duration;
- transition and cut context;
- complete subject presence/blocking;
- environment and view selection;
- role-bounded `referenceUses`;
- `cameraStart`, `cameraPath`, and sparse `cameraEnd`; `cameraPath` may add 2–6 strictly ordered normalized waypoints, relative coordinates, coordinate space, path shape, and per-waypoint named aim targets distinct from the path anchor;
- optional per-shot `staging` with unique subject start/end positions, movement, facing, and eyeline targets;
- `actionBeats`, with strictly ordered normalized progress and an action/reaction and/or linked dialogue (`speakerId`, exact text, delivery, and optional mood);
- appearance and environment transitions with exact from/to state IDs, timing, trigger, and mechanism.

`openingState` describes the visible first frame. `action` describes what changes during the shot. The validator does not infer this split from generated prose or from shot-plan v1.

In exact mode, duration is required and checked within each generation. In automatic mode, per-shot `durationSeconds` is prohibited. An omitted End property inherits Start; a fully identical End is omitted from canonical JSON.

See the normative [`shot_plan_v2.schema.json`](schemas/shot_plan_v2.schema.json).

### Appearance and environment continuity

Identity, appearance, and environment geometry are independent authority domains. An appearance state controls only its declared dimensions and cannot change identity. A temporary environment state cannot redefine permanent geography, architecture, scale, or fixed elements.

Generation initial state uses explicit, carry, or reset policy. The first generation cannot carry unknown prior state. A reset points to the subject base or environment default and requires a reason. Shot transitions must begin at the state resolved on entry, target a different valid state, and involve a present subject or the active environment. State and dependency resolution is deterministic; an LLM does not choose carry, IDs, activation, or physical slots.

---

## Camera Authority Contract

Camera ownership is resolved by `(shot, phase, aspect)`, not as one global camera flag.

- Phases: `start`, `path`, `end`, `whole_shot`.
- Aspects: `motion`, `aim`, `framing`, `angle`, `viewpoint`, `composition`, `focus`, `distance`, `stability`, `lens`, `parallax`.

| Source | Rank |
|---|---:|
| Explicit source-prompt fact | 100 |
| Explicit, active, bound video camera transfer used by the shot | 90 |
| Shot plan | 80 |
| Global cinematography | 60 |
| Generated prose | 40 |
| Creative treatment | 20 |

Equal or compatible claims merge provenance. Incompatible source/video/shot/global owners follow the explicit-conflict matrix. A shot-plan value normally shadows global cinematography for only that shot; it is not a diagnostic. Global cinematography shadows treatment guidance. Start and End are separate phases and never conflict merely because they differ.

A video owns no camera aspect by connection, editing mode, or reuse mode alone. The video must declare `cameraTransfer.enabled=true`, role `camera_reference`, and named aspects; it must be active and bound in the generation; and the shot must include a `camera_transfer` reference use requesting a subset of those aspects.

When no source claims an aspect, the compiler creates no aesthetic default.

---

## Diagnostics and Prompt Coach

`validation_report` retains `valid`, `qualityValid`, `errors`, `warnings`, and the three coverage-gap arrays. It adds `diagnosticReport` schema v1 with a catalog version, counts, and structured diagnostics.

Each diagnostic carries a stable code and structured policy: severity, category, confidence, evidence basis, valid/quality blocking flags, repair eligibility and priority, message, location, related resource IDs, suggestions, allowlisted actions, data, and a fingerprint. The fingerprint does not depend on the English message.

The Prompt Coach operates only on shot-plan v2 structured fields. It is advisory, bounded, and never enters the LLM repair request. Coach findings therefore do not change `valid`, `qualityValid`, or user text. Lexical rules run conservatively for supported English/Spanish input; weak-cut and duplicate-opening checks require their full structured preconditions rather than guessing from final prose.

The normative report schema is [`diagnostic_report_v1.schema.json`](schemas/diagnostic_report_v1.schema.json).

---

## Compatibility and No-Clobber Rules

The enhancer retains its existing input order and eight output ports. Prompt Studio stores no duplicate subjects/environments widget and adds no Coach output. Diagnostics reach the drawer through an ephemeral ComfyUI UI payload while the direct Python `enhance()` tuple remains unchanged.

Structured JSON is classified before editing as `blank`, `v1`, `v2`, `malformed`, or `future`:

- hydration never writes;
- untouched blank and v1 values remain byte-identical;
- historical `false`/`null` placeholders in creative treatment or cinematography, and boolean/`null` placeholders in shot-plan storage, are treated as neutral blank values without rewriting their raw bytes;
- the first structured shot-plan v1 edit migrates atomically to v2;
- legacy creative-treatment and cinematography v1 values remain read-only in the Studio until explicit import validates and writes v2;
- legacy media manifests remain supported and read-only in the v2 entity editor rather than being guessed into a new project;
- malformed input remains raw and cannot be replaced by an editor default;
- a future version remains raw/read-only and is never downgraded.

The runtime still reads existing v1 manifest, creative-treatment, cinematography, shot-plan, and `shotsPackage` inputs so old workflows can generate. Creative-treatment and cinematography parsers normalize v1 to the canonical v2 model in memory and never rewrite the source value. New defaults and persisted edits use v2. `referenceSemanticsVersion` describes resolved output semantics, not the input manifest schema. See [Prompt Studio](prompt_studio.md) for UI behavior and migration details.

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

MiniMax H3 prompt enhancer nodes expose two separate decisions: **Aspect Ratio** selects frame shape, while **Resolution Budget** selects approximate pixel area. Their `width` and `height` outputs are aligned to multiples of 16 for downstream video samplers.

**Auto** uses the established H3-oriented dimensions for each shape. **Custom MP** calculates proportional dimensions from a requested area:

$$\text{Total Pixels} = \text{target\_megapixels} \times 1,000,000$$
$$\text{Height } (H) = \sqrt{\frac{\text{Total Pixels}}{r}} \quad \text{and} \quad \text{Width } (W) = H \times r$$
$$\text{Aligned Dimension} = \max\left(16, \text{round}\left(\frac{\text{dim}}{16}\right) \times 16\right)$$

| Aspect Ratio ($r$) | `0.2` MP (Draft) | `0.3` MP (Light) | `0.5` MP | **Auto** | `1.0` MP | `2.0` MP |
|---|---|---|---|---|---|---|
| **`16:9`** ($1.778$) | `592 × 336` | `736 × 416` | `944 × 528` | **`1280 × 720`** | `1328 × 752` | `1888 × 1056` |
| **`9:16`** ($0.5625$) | `336 × 592` | `416 × 736` | `528 × 944` | **`720 × 1280`** | `752 × 1328` | `1056 × 1888` |
| **`1:1`** ($1.0$) | `448 × 448` | `544 × 544` | `704 × 704` | **`1080 × 1080`** | `1008 × 1008` | `1408 × 1408` |
| **`4:3`** ($1.333$) | `512 × 384` | `640 × 480` | `816 × 608` | **`960 × 720`** | `1152 × 864` | `1632 × 1216` |
| **`3:4`** ($0.75$) | `384 × 512` | `480 × 640` | `608 × 816` | **`720 × 960`** | `864 × 1152` | `1216 × 1632` |
| **`21:9`** ($2.333$) | `688 × 288` | `832 × 352` | `1088 × 464` | **`1680 × 720`** | `1536 × 656` | `2160 × 928` |
