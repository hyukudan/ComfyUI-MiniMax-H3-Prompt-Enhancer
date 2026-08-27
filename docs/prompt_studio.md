# MiniMax H3 Prompt Studio

Prompt Studio is the visual planning interface embedded in the two enhancer nodes. One authoritative **Studio Project v3** stores Files, Subjects, Environments, Generations, Shots, semantic links and Look. The established v2 prompt contracts are generated internally as runtime projections; users do not manage them as separate Studio documents.

The canonical hierarchy and scope rules are defined in [Integrated Prompt Studio domain](integrated_prompt_studio_domain.md). In particular, one Shot is one continuous block between cuts; `Scene` is not a second container, and reusable defaults must remain separate from This Shot overrides.

**Storyboard** is the production editor: an always-visible Shot strip, visual stage, reference tray, semantic destinations and contextual inspector. **Content**, **Stage** and **Camera** are modes of the selected Shot, not separate project areas. The inspector creates and places a canonical Subject or Environment atomically, so Ana can receive a reusable identity image and voice, enter a Shot, receive Shot-only overrides, and use a selected background without leaving Prompt Studio. **Dialogue & sound** authors exact lines with separate Speaker, Channel (on-screen or V.O.), Delivery and Voice color controls, and separates default voice, Shot overrides, recordings and soundtrack. The Voice color catalog resolves to the same concrete pitch, timbre and pacing prose as the main node's one-click palette. The read-only **LLM handoff** derives its subject and physical aliases from the same v3 graph sent to the compiler.

All of this belongs to the same Prompt Enhancer node. The visible areas are **Storyboard**, **Library**, **Look**, and **Review & Generate**. Library groups **Subjects**, **Environments**, and compact **Files**; Shot editing, staging and camera direction stay contextual inside Storyboard. The older Visual Reference Director class remains loadable only for workflow migration and is marked deprecated.

It does not add a project manager or external service. The canonical project is `studio_project_json` schema v3, saved inside the workflow. Hidden older fields remain only as generated runtime adapters for compatibility.

## Open the Studio

The enhancer node presents a primary **Open Studio** action plus destination chips:

- **Storyboard** — visually assemble the prompt Shot by Shot from cast, backgrounds, action, dialogue, camera and references.
- **Library · Subjects** — reusable identities, default voices and appearances.
- **Library · Environments** — reusable places, background views and states.
- **Library · Files** — compact import, filter and preview shelf for images, video and audio.
- **Look** — creative direction and global cinematography defaults.
- **Review & Generate** — compile v3, inspect exact physical outputs, diagnostics and queue actions.

Selecting **Open Studio** or a chip opens one drawer attached to that node. The primary button changes to **Close Studio** while its drawer is open. The drawer is mounted to the browser viewport, so it does not scale with the ComfyUI canvas. It defaults to 720 px on ordinary desktops, 820 px on wide displays, and 920 px on 4K/high-resolution displays. The resizable range is 420 px to `min(1100px, 60vw)`; below 700 px the drawer becomes full-width, and below 600 px of content the editors stack into one column.

There is no separate Save action. Every explicit add, edit, assignment, reorder, or deletion is consolidated into Studio Project v3 and saved with the ComfyUI workflow. Merely opening, closing, navigating, expanding a disclosure, or hydrating old data does not create project facts.

Empty authoring fields use instructional placeholders. The example disappears on focus and returns on blur only while the field remains empty; it is never stored in project JSON or compiled into the prompt. Required empty drafts remain visibly editable and Review identifies them before generation instead of substituting invented prose.

**Guided / Advanced** is a Look-specific presentation control and therefore appears inside **Look**, not in the global Studio header. Switching modes never clears, rewrites, or adds a workflow fact, and it does not affect Storyboard, Library, or Review & Generate.

## What Prompt Studio does — and does not do

Prompt Studio is the planning layer for the prompt enhancer. Studio Project v3 compiles into `enhanced_prompt`, validation metadata, a typed `reference_project`, and aligned physical media lists.

Prompt Studio imports pictures, video and audio into ComfyUI input storage. The enhancer emits native numbered H3 outputs plus compatibility `pictures`, `videos` and `audios` lists and a typed `reference_project`; all are compiled from the same assignments used in `enhanced_prompt`.

The prompt, metadata, and physical media paths are separate until the generation node:

```text
Prompt Studio ─> enhanced_prompt ──────────────────────────────────────┐
              ├> pictures / videos / audios ──────────────────────────┼─> H3 generation node
              └> reference_project ─> Inspector / compatible adapter ┘
```

The logical meaning, physical file and generation binding remain distinct records, but Prompt Studio owns and validates all three as one project.

## Which area to use

| Area | Use it when you need to… | It owns |
|---|---|---|
| **Storyboard · Content** | Create and order Shots, cast Subjects, choose an Environment view, add action/dialogue and attach references. | Story, timing/cuts, presence, background views, links, transitions and overrides in v3. |
| **Storyboard · Stage** | Arrange the selected Shot's cast visually. | Subject start/end positions, movement, facing and eyelines in that Shot. |
| **Storyboard · Camera** | Design or refine camera behavior for the selected Shot. | Start/Path/End in that same Shot; no duplicate camera model. |
| **Library · Subjects** | Create reusable identities, voices and appearance states. | Identity Files, default voice File, H3 subject index and appearance states. |
| **Library · Environments** | Create reusable places, reference views and temporary states. | Permanent place facts, view Files and states. |
| **Library · Files** | Import and preview raw references once. | Physical ComfyUI source, media type and stable File ID. |
| **Look** | Set global presentation defaults or reuse a Look. | Creative treatment and cinematography inside v3. |
| **Review & Generate** | Verify and run. | v3 compilation, quotas, exact physical output map, diagnostics and queue action. |

## Common workflows

### T2V / T2VA — no source media

1. Write the idea in `basic_prompt`.
2. Optionally organize it as Shots in **Storyboard** and create reusable resources in **Library**.
3. Choose global presentation in **Look**, switch the selected Shot to **Camera** when it needs explicit direction, and check **Review & Generate**.
4. Connect `enhanced_prompt` to the H3 generation node. Library · Files can remain empty.

When Studio Project v3 is empty, Storyboard can start directly from the Basic prompt; advanced migration tools remain collapsed in Review.

### I2V / FL2V / L2V — alignment frames

1. Load the physical image with the normal ComfyUI image loader and connect it to the H3 first/last-frame input.
2. Describe the required alignment and action in the enhancer. Use the Shot strip in **Storyboard** for the temporal plan.
3. Add a logical reference only when the project also needs reusable metadata or a binding; adding one does not carry the image tensor.
4. Connect `enhanced_prompt` to the same H3 generation node.

### Ref2VA — reusable picture, video, or audio references

1. On **MiniMax H3 Prompt Enhancer**, choose **Open Studio**.
2. In **Storyboard** or **Library · Files**, import pictures, video or audio. Prompt Studio copies them into ComfyUI input storage and creates stable Files with visual previews.
3. Drop each visual card onto the subject identity/voice, environment/background, or shot performance/camera property it controls.
4. In **Review & Generate**, compile the target Generation and verify every derived **physical slot** (`Picture N`, `Video N`, or `Audio N`).
5. Connect each active numbered output to the native H3 input with the same name: `ref_image_1`, `ref_video_1`, `ref_video_audio_1`, or `ref_audio_1`, continuing from 1 in each family. Review shows this exact socket map. The list outputs remain for compatibility with list-aware adapters. The enhancer injects the matching reference context into its own LLM request automatically.
6. Optionally connect `reference_project` to **MiniMax H3 Reference Project Inspector** for the exact wiring report.

### Chained Multishot — several generation passes

1. Create ordered Generations and assign Shots to them in **Storyboard**.
2. Link reusable Files to the Subjects, Environments and Shots used by each Generation.
3. Compile in **Review & Generate**; physical slot numbers are derived locally for each Generation.
4. Set explicit/carry/reset initial states and review continuity before queueing the chain.

## Resolution: frame shape and pixel area

Resolution has two independent controls. **Aspect Ratio** selects the shape of the frame. **Resolution Budget** selects its approximate area.

- **Auto** uses `1280×720` for 16:9, `720×1280` for 9:16, `1080×1080` for 1:1, `960×720` for 4:3, `720×960` for 3:4, and `1680×720` for 21:9.
- **Custom MP** enables and focuses the always-visible MP field, accepts any positive finite value (decimal point or comma) without an artificial minimum or maximum, and persists it when you leave the field or press Enter. It targets a megapixel budget while preserving the selected shape; final width and height are aligned to 16-pixel steps and shown live on the node.

Resolution Budget drives the enhancer's `width` and `height` outputs, not creative prose. Connect those outputs to the H3 generator; if a separate Resolution Selector supplies the generator dimensions, that downstream node overrides the Studio budget.

Changing the aspect ratio is a composition decision; changing the resolution budget is a pixel-area/performance decision. Neither control changes the shot count or carries media.

Only one Studio drawer is active at a time. Collapsing or deleting its node closes it.

## Integrated areas and contextual modes

### Storyboard · Content

The shot list uses fixed 60-pixel, two-line rows and mounts only the visible range plus five-row overscan on either side. A separate editor handles the selected shot, so a 64-shot plan does not create 64 expanded editors.

For each Studio Project v3 Shot, the editor owns:

- a visible Action for every Shot; a new Shot starts from the current Basic prompt, while one existing empty Shot can inherit that prompt without mutating storage and offers **Use Basic prompt as Action** to make the inheritance explicit. Multiple Shots require individual Actions;

- stable shot and generation IDs;
- `openingState` and `action` as distinct fields;
- automatic or exact timing;
- transition and cut context;
- complete subject presence and blocking;
- environment/view selection and reference uses;
- camera Start, Path, and sparse End values, including an optional 2–6 point spatial path;
- optional relative action beats, each with a visible action/reaction and linked dialogue delivery;
- optional beat spans with a start and end, overlap/gap feedback, and a dialogue-duration estimate when exact timing is available;
- explicit subject-to-subject scale relationships without inventing dimensions;
- appearance and environment transitions.

`openingState` is the visible first-frame condition. `action` is the change that occurs during the shot. Do not repeat the opening state as if it were a second event.

### Library · Subjects

Subjects have a stable logical ID, an H3 subject index, an identity description, identity pictures, an optional default voice asset, and a base appearance state. Identity pictures appear as selectable thumbnails in the Subject itself; **+ Identity picture** uploads and attaches one without visiting Files. **+ Import voice** does the same for the reusable voice default. Below Basic prompt, and beside the selected Shot's Action, subject chips insert `<Subject N>` at the cursor. Hover or keyboard focus previews the identity image, description and default voice before insertion. The default voice is inherited whenever the subject is active; a shot-level `voice` reference is an explicit override for that Shot. Appearance states can control wardrobe, hair, makeup, accessories, carried items, damage, wetness, body condition, transformation, or another explicitly declared dimension. Their detailed forms stay collapsed until selected so the common identity workflow remains compact.

A Subject is a reusable library definition, while prompt inclusion is an explicit casting decision. New subjects are included in the currently selected generation by default. Existing subjects can be sent without creating a Shot through **Use in prompts → Always include in Generation …**; alternatively, cast them in the selected Shot under **Storyboard · Content**. Active subjects compile into authoritative lines such as `<Subject 1> (Juan): …`. Review warns when a valid library Subject is neither included in a Generation nor cast in a Shot, because it will not reach the LLM.

Identity and appearance are separate. An appearance state cannot silently replace facial identity. Copying a state creates a new stable ID. A base or referenced state cannot be deleted silently; the UI shows where it is used.

### Library · Environments

An environment separates permanent facts from temporary state:

- permanent geography, architecture, scale, and fixed elements;
- reference views with bounded roles such as overview, alternate, detail, or lighting;
- temporary lighting, weather, atmosphere, condition, time of day, and temporary elements.

A temporary state does not own permanent geometry. A detail view does not become an overview, and a lighting view does not redefine architecture. **+ Import view picture** uploads a picture, creates the logical File and attaches a new Environment view in one atomic action; existing pictures remain available as visual thumbnail choices inside each view.

### Library · Files and semantic references

The Files library is the project-wide shelf for physical sources and stable semantic meaning, but it is not a mandatory first stop. Subjects can import identity pictures and voices directly, Environments can import view pictures directly, and Storyboard can import Shot-scoped references at their destination. Every such action also registers the reusable File atomically. H3 labels such as `<Picture 1>` or `<Video 2>` are derived deterministically for each Generation during v3 compilation.

**Plan by outcome** provides an inline, cancelable first-binding assistant for subject identity, environment view, performance, camera, voice, and continuity. It chooses only from existing shots, generations, subjects, and environments, then prepares the logical asset, its subject/environment relationship when required, a shot-scoped `referenceUse`, and the generation binding as one atomic Media + Shot Plan update. It never connects or uploads the physical file. If a shot belongs to another generation, a required relationship is absent, or the matching physical slot quota is full, the assistant reports that prerequisite deterministically and writes nothing.

The adjacent user-first recipes are contract-safe starting points rather than new schema objects: **Targeted edit** uses an appearance-scoped picture, **Relight** uses a lighting-scoped picture, **Performance transfer** uses a performance-scoped video, and **Continuation** uses a continuity-scoped video. The cards explain what is missing before setup and remain editable through the ordinary asset, shot-use, and binding controls afterward.

**Export LLM planning context** emits `minimax-h3-planning-context` format version 1. It is a read-only discussion artifact projected from Studio Project v3, with explicit instructions to preserve IDs and Generation boundaries. It contains no physical files, performs no network request, has no import action, and never applies an LLM response automatically.

Reference setup follows the visible destination. Import from a Subject, Environment or Shot when the intended meaning is already known; use **Library · Files** for batch import or when meaning will be assigned later. Prompt Studio stores the physical source and logical relationship together, while the v3 compiler derives Generation activation and physical H3 slots.

A logical reference can be reused in several generations. A physical file connection is local to the generation that consumes it; registering the logical reference alone does not make media available to H3.

This distinction allows slot reuse across chained generations without changing asset identity. The same slot may represent a different asset in another generation, but one generation cannot bind two active assets of the same type to the same slot.

### Storyboard · Camera

**Storyboard · Content** keeps camera context compact and opens **Camera** without changing the selected Shot. Camera replaces the central editor at workspace scale while the Shot strip remains visible, and exposes precise Start/Path/End fields. A path may use 2–6 positions with normalized progress, relative X/Z in −1…1, Y height in −1…1, subject- or scene-relative coordinates, and straight, smooth, or directed arc interpolation. Its 3D view uses a four-corner isometric floor rather than a perspective funnel. Camera height does not alter the icon's position on that floor: dragging the camera changes X/Z while preserving Y, and the **Camera height** slider represents height by scaling the icon (larger when low, smaller when high). Top view isolates horizontal placement; Front view shows elevation directly. **Distance from anchor** moves the camera nearer or farther along its current direction without changing height. Camera height uses five semantic bands: **Very low, Low, Eye level, Elevated, Very elevated**. The normalized number remains storage detail rather than the primary label, and untouched paths start at neutral eye level. Between positions, the compiler classifies the real height delta as held, drifting, moving, or sweeping; it states rise/descent at the destination, marks crossings of the eye line, and summarizes the whole vertical profile before listing waypoints. Horizontal distance is also compiled even when framing is explicitly set. Small slider jitter remains silent. Camera-body height and lens tilt are independent, so **Very elevated** does not silently force an overhead or high-angle view. The toolbar exposes the overall path shape, pace, speed change and reference frame, and each position exposes framing, angle, aim and timing. A four-second **Preview** and scrubber interpolate by each waypoint's actual `at` value, so uneven timing remains visible. All three views edit the same data and are direction previews, not a physical simulation. Classic motion presets remain available in a collapsed disclosure. Content and Camera read and write the same Shot in Studio Project v3, so switching modes does not copy or reconcile data.

### Storyboard · Stage

Stage shares the selected Shot with Build and Camera. **Create staging** places the Shot's present cast across the frame only after that explicit action. Drag each named subject in 3D, Top, or Front view; choose Start or End positions, a movement verb, and whether the subject faces the camera, travel, a side of frame, away from camera, or another named subject. It compiles as qualitative blocking and eyeline prose—not XYZ values. Free-text blocking remains available for nuance; Review notes when both are present so contradictory arrangements are not silently merged.

Camera **Anchor** and **Aim target** are deliberately separate. Anchor establishes the origin for camera position (for example, left of Juan or behind Juan). Each waypoint's Aim target says where the lens points and may select a different present subject. If that subject has no Staging position, its name still reaches H3 but Studio reports that the reticle is only a placeholder. New waypoints inherit the prior resolved aim; target changes compile as a smooth reframe instead of numeric pan/tilt.

### Before-generation checks and Review

Prompt Studio checks Studio Project v3 immediately, before the node runs. It catches missing Shot actions, invalid Generation links, incomplete presence, empty action beats, invalid spatial timing, deleted Files and quota overflow. **Review & Generate** calls the Python compiler and displays the exact output map before queueing, so prompt aliases and physical lists cannot drift.

These checks are intentionally bounded and do not replace backend validation. **Review** is populated after execution and remains authoritative for compiled continuity, camera ownership, H3 contract quality, and Prompt Coach guidance.

### Legacy project transfer

Older portable Project v2 packages remain importable from the collapsed source tools for migration. Import validates and applies them atomically, then Prompt Studio consolidates the result into Studio Project v3. They are compatibility input, not the current authoring format, and never include physical image, video or audio payloads.

Start and End are temporal phases, not competing owners. An omitted End field inherits Start and is not serialized redundantly.

### Look

Global cinematography values are defaults. Shot Start/Path/End values override the corresponding global aspect for that shot. This normal override is displayed as provenance, not as a red conflict.

The Visual Language selector is organized as **family → era/technique → variant**, with Back and breadcrumb navigation, while committing the same canonical `visualLanguage` token as before. Search stays global and groups matches by family and branch; it includes the visible label, token, family, branch, and conservative aliases. An unknown future token remains visible under **Other** instead of being reset. Visual language is independent from narrative Genre and scene-wide Mood.

Every option has preview-card infrastructure. Nine newly expanded drawn-animation profiles ship with small, project-original comparison samples built around the same clockwork-bird subject, making differences in line, shape, cel treatment, mechanical detail, compositing, and print texture easier to compare. They were generated specifically for this repository, are not H3 outputs, do not predict model adherence, and record their source, license, alt text, and exact SHA-256 in `VISUAL_LANGUAGE_PREVIEW_MANIFEST`. Options without a sample remain honest text-only choices instead of showing a fabricated result.

To add another project-owned example, place an original or licensed local `avif`, `jpg`, `png`, or `webp` file under `web/studio/previews/` and register it in `VISUAL_LANGUAGE_PREVIEW_MANIFEST` with:

- `kind`: `original` or `licensed`;
- a relative `./previews/...` source and descriptive `alt` text;
- provenance `creator`, `source`, `license`, and a 64-character SHA-256 digest.

Remote URLs, missing provenance, unsupported kinds, and invalid digests fall back to the honest placeholder. A sample illustrates the catalog vocabulary only; it must not be described as a predicted or guaranteed H3 output.

### Experimental animation cadence

Creative Treatment v2 optionally stores `animationCadence: "adaptive" | "ones" | "twos" | "threes"`; omission is equivalent to `adaptive`. The control lives under **Advanced creative options** and requests the exposure rhythm of authored poses or drawings for compatible 2D, pixel, stop-motion, marionette, and rotoscoped visual languages. `On ones` asks for a refreshed pose/drawing each output frame, while `On twos` and `On threes` request deliberate two- or three-frame holds.

Cadence is intentionally separate from output FPS and cinematography motion rendering. It never changes duration, frame count, interpolation, camera speed, motion blur, action timing, shot boundaries, or narrative holds. An incompatible live-action or 3D selection preserves the requested value but does not emit cadence prose and produces a warning. The UI and prompt both label the feature **Experimental** because model adherence is not guaranteed; `Adaptive` remains the safe default.

### Coach

The Coach consumes the ephemeral `minimax_h3_diagnostics` UI payload returned when the node executes. It groups diagnostics by stable code. Editing any canonical widget marks the cached report stale; run the node again before treating it as current. A location chip first selects the related shot, then opens the owning section, expands the relevant disclosure, and focuses and briefly highlights the closest exact control. Output-only or obsolete locations never pretend to be editable: Review opens the related section and shows an explicit fallback message instead.

**Dismiss** hides one stable diagnostic fingerprint in this browser only. Dismissals use a bounded, versioned local preference containing fingerprints—not report content or project data—and never mutate `validation_report`, `diagnosticReport`, the workflow, or backend suppression policy. **Show dismissed** exposes those cards with **Restore**, so the action is always reversible.

After an enhancer or validator execution, Review also shows the exact total character count and a deterministic per-section character breakdown derived from that emitted `enhanced_prompt`. Because this display is computed for the UI rather than supplied as a normative backend budget object, it is labeled **Local estimate from enhanced prompt**. The 7,000-character denominator appears only when the real validation report says `deliveryTarget: "api_v2"`; local delivery does not invent a limit. When no prompt was returned, Review omits the budget card instead of guessing.

Coach advice is conservative and bounded to two items per shot and twelve globally. It can flag:

- locomotion without a route/destination and visible final state;
- turns or looks without a target, direction, or result;
- short manipulation without contact, trajectory, or object result;
- ambiguous pronouns when multiple subjects are explicitly present;
- near-duplicate `openingState` and `action`;
- a weak cut only when sufficient structured context proves it;
- dense generic aesthetic modifiers that compete with a selected medium.

Coach findings are advisory. They do not change `valid`, `qualityValid`, the prompt, or the repair request sent to the LLM.

## Canonical Studio Project v3

The normative authoring schema is [`schemas/studio_project_v3.schema.json`](schemas/studio_project_v3.schema.json). Its top-level arrays are `files`, `subjects`, `environments`, `generations`, `shots`, and `links`; `project.look` owns creative treatment and cinematography. Files carry their provenanced ComfyUI source. Subjects point to identity Files and an optional default voice File. Environment views point to background Files. Shots select cast, Environment/view, semantic reference bindings, staging, action/dialogue and camera.

Drafts may remain incomplete while editing. **Review & Generate** rejects missing visible actions, broken IDs, unavailable physical sources and per-Generation quota overflow. The compiler assigns slots deterministically in H3 order (9 pictures, 3 videos, their 3 aligned soundtracks, and 3 independent audio inputs), builds the LLM reference context and emits both the numbered native sockets and compatibility lists from that same result.

## Hidden runtime projections and compatibility

The following v2 shapes remain documented because the established prompt engine and saved workflows still consume them. They are no longer separate Prompt Studio documents: when v3 is present, the Python compiler derives them immediately before enhancement.

### `media_manifest` v2

Manifest v2 is the internal library projection. It contains:

Its JSON remains a hidden compatibility input. Make normal changes through **Storyboard** and **Library**.

```text
assets ─┬─ subjects ─ appearance states
        └─ environments ─ views / temporary states
generations ─ activation roots / exclusions / bindings / initial states
```

Each generation resolves its own active dependency closure and input map. Only active, available, physically bound assets enter that generation's prompt context. Dependencies include identity assets, the subject's optional default voice, active appearance sources, selected environment views, referenced audio, and explicitly transferred camera references.

Activation can be automatic or explicit. An exclusion cannot remove a mandatory dependency. Bindings are validated against asset type, per-type capacity, duplicate slots, soundtrack requirements, total file count, and media-duration limits.

The normative schema is [`schemas/media_manifest_v2.schema.json`](schemas/media_manifest_v2.schema.json). Legacy manifests remain supported by the backend and retain their existing labels and behavior; the Studio keeps them read-only rather than guessing a stateful v2 project.

### `shot_plan_json` v2

Shot-plan v2 is the internal temporal projection. It references project IDs rather than redefining subjects, appearances, environments, or assets. It supports up to 64 shots and groups them by `generationId` in chained mode. Spatial camera paths distinguish camera position from camera aim: `anchorTarget` names the project subject used as the origin, while each waypoint may inherit aim, keep the anchor framed, follow travel, aim at a named `aimTarget`, or use a custom editor direction. Optional `staging` places each subject at qualitative start/end positions with movement and facing. The compiler resolves all of this into names and natural camera/blocking prose; internal XYZ, timing percentages, angle degrees, and enum tokens do not become camera instructions.

`timingMode: "auto"` omits per-shot duration. `timingMode: "exact"` requires it, and durations are checked per generation. `actionBeats[].at`, optional `actionBeats[].endAt`, and camera waypoint `at` values are normalized from 0 to 1, so their rhythm survives duration changes. Dialogue stores its vocal action in `delivery`, its source in optional `channel`, and its selected Voice color in `mood`; legacy `delivery: "voice_over"` projects to neutral `says` plus `channel: "voice_over"`. Beats may use neutral projected **calls out** delivery as well as the other documented verbs. The editor warns about overlaps, large fully-authored gaps, and dialogue that is likely too dense for its exact span using a transparent 150-words-per-minute estimate. Beat percentages and editor labels never appear in the enhanced prompt; they compile to natural temporal flow. Camera timing may also target **during dialogue** or **after dialogue**. `cameraEnd` is stored as a delta from `cameraStart`; omitted End properties inherit Start. Shot transitions include ordinary cuts plus cross dissolve and fade through black. `scaleRelationships` describes only explicitly authored relative scale between present subjects and never supplies invented measurements.

The normative schema is [`schemas/shot_plan_v2.schema.json`](schemas/shot_plan_v2.schema.json). Shot-plan v1 remains accepted without changing its generated instruction. The first intentional structured edit migrates a v1 shot plan atomically to v2.

### `creative_treatment_json` v2

Creative Treatment v2 is the internal Look projection for content format, genre, visual language, world aesthetic, scene-wide **Mood (tone)**, and title-screen style. Its normative runtime schema is [`schemas/creative_treatment_v2.schema.json`](schemas/creative_treatment_v2.schema.json).

The Mood control is searchable and grouped by creative intent. Every option includes a short description that distinguishes nearby choices and states its anti-invention boundary; a persistent footer clarifies that Mood never adds facts, dialogue, or music. Search indexes the label, stored token, group, and description, so both **pulp** and **heightened** find the same `pulp_heightened` option. Unknown future values display as **Unavailable — token** and remain byte-preserved until deliberately replaced.

Legacy v1 remains accepted by the runtime so saved workflows continue to generate, but the Studio does not migrate it during hydration or an unrelated edit. It stays read-only until the user invokes the explicit import action, which validates the source and writes one v2 value.

### `cinematography_json` v2

The 13 existing cinematography controls remain supported in the internal v2 projection. It supplies global defaults and does not outrank an explicit shot value, source fact, or authorized video-camera transfer. The normative runtime schema is [`schemas/cinematography_v2.schema.json`](schemas/cinematography_v2.schema.json).

As with Creative Treatment, runtime parsing accepts a legacy v1 source and canonicalizes it to v2 only in memory. The Studio keeps v1 read-only; only explicit import persists a converted v2 document.

## Camera authority

Camera ownership is resolved independently for each shot, phase, and aspect. Aspects are motion, aim, framing, angle, viewpoint, composition, focus, distance, stability, lens, and parallax. Phases are Start, Path, End, and Whole Shot.

| Source | Authority | Behavior |
|---|---:|---|
| Explicit source-prompt fact | 100 | Immutable; incompatible explicit configuration blocks validation. |
| Explicit video camera transfer | 90 | Owns only declared and requested aspects. |
| Shot plan | 80 | Local authority for that shot and phase. |
| Global cinematography | 60 | Default; normally shadowed by the shot plan. |
| Generated prose | 40 | Must realize the owner; it does not become a new configuration owner. |
| Creative treatment | 20 | Suggestion only when no higher owner exists. |

A video does not own camera because it is connected, because a workflow is a direct edit, or because a reuse mode is selected. It must satisfy every gate:

1. the logical asset is a video;
2. `cameraTransfer.enabled` is `true`;
3. `cameraTransfer.role` is `camera_reference`;
4. the transfer enumerates camera aspects;
5. the asset is active and bound in the shot's generation;
6. that shot has a `referenceUse` with role `camera_transfer` and requests a subset of those aspects.

Two incompatible explicit videos, video versus shot, video versus global, or source fact versus an incompatible explicit configuration produce `camera.authority.explicit_conflict`. Shot versus global produces only a normal `shot_overrides_global` shadow record. Start and End never compete.

## Structured diagnostics

`validation_report` keeps all legacy fields and adds `diagnosticReport`:

```json
{
  "schemaVersion": 1,
  "catalogVersion": 1,
  "summary": {
    "errors": 0,
    "warnings": 0,
    "advice": 0,
    "info": 0,
    "suppressedCoach": 0,
    "valid": true,
    "qualityValid": true
  },
  "diagnostics": []
}
```

Each diagnostic has a stable code, severity, category, confidence, basis, blocking policy, repair eligibility/priority, message, structured location, related resources, up to three suggestions, allowlisted safe actions, data, and a SHA-256 fingerprint. Fingerprints use the code, location, and related resource identities; message wording and excerpt text do not define identity.

Legacy `errors`, `warnings`, `coverageGaps`, `styleCoverageGaps`, and `contentFormatCoverageGaps` remain present. `valid` and `qualityValid` therefore retain their public meaning while structured consumers stop comparing English messages.

The normative schema is [`schemas/diagnostic_report_v1.schema.json`](schemas/diagnostic_report_v1.schema.json).

The enhancer also records compact planning metadata in `enhancement_manifest`: the real input schema versions, manifest and diagnostic digests, generation/shot/diagnostic counts, reference semantics version, and a v1 or v2 `shotsPackage`. It does not duplicate the full diagnostic report there.

## Preservation and migration rules

Every structured widget is classified as `blank`, `v1`, `v2`, `malformed`, or `future` before editing.

| State | Load behavior | Edit behavior |
|---|---|---|
| `blank` | Remains byte-empty; hydration writes nothing. | First intentional edit creates the relevant supported schema. |
| legacy `false` / `null` Creative or Cinematography; boolean / `null` Shots | Raw bytes remain untouched and the Studio presents a neutral blank state. | First intentional edit creates v2. |
| `v1` shot plan | Preserved byte-for-byte while untouched. | First structured edit atomically creates v2. |
| `v1` Creative / Cinematography | Preserved byte-for-byte and accepted by the runtime. | Read-only until explicit import validates and writes one v2 document. |
| legacy media manifest | Preserved and accepted by the backend. | Read-only in the v2 entity editor; no guessed conversion. |
| `v2` | Parsed into the relevant editor. | An explicit edit writes normalized v2 JSON. |
| `malformed` | Raw text and parse error are preserved. | Structured editing is blocked; the Studio never substitutes a default. |
| `future` | Version and raw text are preserved. | Read-only; the Studio never downgrades it. |

Hydration, opening/closing the drawer, zooming, collapsing, cloning, copy/paste, and saving an untouched workflow do not serialize structured data. There is no project state in `localStorage`.

## Port and workflow compatibility

No persistent input or output was added for Prompt Studio or Coach. The enhancer nodes retain these eight outputs, in order:

1. `enhanced_prompt`
2. `validation_report`
3. `enhancement_manifest`
4. `duration_seconds`
5. `aspect_ratio`
6. `treatment_warnings`
7. `width`
8. `height`

The ordinary Python `enhance()` result remains the same tuple. ComfyUI calls `enhance_with_ui()`, which wraps that exact tuple and adds only the ephemeral `minimax_h3_diagnostics` UI payload. Workflows do not store the Python method name, so existing graphs and connections remain valid.

`MiniMaxH3ShotSelector` accepts `shotsPackage` v1 and v2 without changing its six outputs.

## Independent implementation and provenance

Prompt Studio was implemented independently in this GPL-3.0 project. General planning and editor concepts were evaluated from the publicly visible [BMB12d3/minimax-h3-prompt-composer](https://github.com/BMB12d3/minimax-h3-prompt-composer), which did not publish a license when reviewed. No source code, HTML, CSS, wording, regular expressions, fixtures, or documentation was copied or adapted. The schemas, algorithms, UI, diagnostics, tests, and prose in this project were written from scratch around this repository's existing H3 contracts and ComfyUI compatibility requirements.
