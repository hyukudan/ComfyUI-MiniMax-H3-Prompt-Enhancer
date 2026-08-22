# MiniMax H3 Prompt Studio

Prompt Studio is the structured planning interface embedded in the two enhancer nodes. It keeps the node compact while exposing shots, subjects, appearance states, environments, logical references, camera controls, and diagnostics in a viewport-level drawer.

It does not add a project manager, a network service, or another ComfyUI output. The canonical project remains in the existing `media_manifest`, `shot_plan_json`, `creative_treatment_json`, and `cinematography_json` widgets saved with the workflow.

## Open the Studio

The enhancer node presents seven dashboard chips:

- **Shots** — number of structured shots.
- **Subjects** — number of logical subjects.
- **Environments** — number of logical environments.
- **Media** — bound physical slots versus logical references.
- **Camera** — the selected shot's visual camera planner and precise Start/Path/End controls.
- **Look** — creative direction and global cinematography defaults.
- **Review** — current structured diagnostic count and Prompt Coach advice.

Selecting a chip opens one drawer attached to that node. The drawer is mounted to the browser viewport, so it does not scale with the ComfyUI canvas. It defaults to 720 px on ordinary desktops, 820 px on wide displays, and 920 px on 4K/high-resolution displays. The resizable range is 420 px to `min(1100px, 60vw)`; below 700 px the drawer becomes full-width, and below 600 px of content the master/detail editors stack into one column. Close it with **Close** or `Esc`; focus returns to the chip that opened it. The navigation rail supports arrow keys, Home, End, and numeric shortcuts 1–7.

The header also stores a browser-local **Guided / Advanced** preference. Guided presents the principal workflow controls first and places neutral specialist fields behind a disclosure; if an advanced Creative Treatment value is already active, that disclosure opens and reports the active count. Advanced renders every available field. Switching modes never clears, rewrites, or adds a workflow field.

## What Prompt Studio does — and does not do

Prompt Studio is the planning layer for the prompt enhancer. It stores shots, reusable identities and places, logical reference metadata, generation bindings, camera choices, and diagnostics in the enhancer's existing structured widgets. Those facts compile into `enhanced_prompt` and validation metadata.

Prompt Studio does **not** load, upload, transport, or output an image, video, audio file, latent, or tensor. The enhancer has no media output ports. A Load Image, Load Video, or audio-source node must still connect the physical media to the H3 generation node through the inputs expected by that node.

The prompt, metadata, and physical media paths are separate until the generation node:

```text
Idea
  └─> Prompt Enhancer / Prompt Studio ─> enhanced_prompt ───────────────┐

Physical file
  └─> Load Image / Load Video / audio source ─> H3 media input ────────┼─> H3 generation node

Reference meaning
  └─> Add reference ─> logical reference ─> generation binding ────────┘
                                      └─> physical slot: Picture/Video/Audio N
```

The logical reference says what a file means and how it may be used. The physical connection supplies the actual file. The generation binding makes their correspondence explicit; none of the three substitutes for another.

## Which area to use

| Area | Use it when you need to… | It owns |
|---|---|---|
| **Overview** | Check whether the project is ready and jump to unfinished work. | Derived counts, health, continuity, and navigation only. |
| **Shots** | Divide the scene into visible beats and inspect each shot's compact camera summary. | Story, timing/cuts, cast presence, environment/views, reference uses, and transitions in Shot Plan v2. |
| **Subjects** | Preserve who or what appears and manage visible changes. | Identity sources, H3 subject index, base appearance, appearance states, and usage guards. |
| **Environments** | Reuse a stable place under different conditions. | Permanent geography/architecture/scale, views, default state, temporary states, and usage guards. |
| **Media** | Explain a reference and pair it with a connected file for one generation. | Reference library, activation, generation bindings, physical slots, quotas, and initial states. |
| **Camera** | Design or refine camera behavior for one selected shot. | The same Start/Path/End values in Shot Plan v2 that Shots summarizes; no duplicate camera schema. |
| **Look** | Set global presentation defaults or reuse a Look. | Creative Treatment v2, Cinematography v2, global provenance, and explicit import/export. |
| **Review** | Understand what blocks generation or could be clearer. | Diagnostics and bounded Prompt Coach actions; it does not silently rewrite the plan. |

## Common workflows

### T2V / T2VA — no source media

1. Write the idea in `basic_prompt`.
2. Optionally organize it in **Shots**, **Subjects**, and **Environments**.
3. Choose global presentation in **Look**, use **Camera** when a shot needs explicit direction, and check **Review**.
4. Connect `enhanced_prompt` to the H3 generation node. The Media library can remain empty.

When all structured widgets are blank, Overview also offers three small editable v2 examples: a spatial camera move, timed dialogue delivery, and a Picture 1 reference contract. They contain no external media, brand names, or hidden prompt suffixes and disappear once the user has started a project.

### I2V / FL2V / L2V — alignment frames

1. Load the physical image with the normal ComfyUI image loader and connect it to the H3 first/last-frame input.
2. Describe the required alignment and action in the enhancer. Use **Shots** for the temporal plan.
3. Add a logical reference only when the project also needs reusable metadata or a binding; adding one does not carry the image tensor.
4. Connect `enhanced_prompt` to the same H3 generation node.

### Ref2VA — reusable picture, video, or audio references

1. In **Media**, choose **Add reference** and register the logical reference and its intended role.
2. Load the actual file in ComfyUI and connect it to the reference input of the H3 generation node.
3. In the target generation, activate the logical reference and assign it to the matching **physical slot** (`Picture N`, `Video N`, or `Audio N`).
4. Use the logical reference from Subjects, Environments, or a shot `referenceUse`, then verify quotas and diagnostics in **Review**.

### Chained Multishot — several generation passes

1. Create the ordered generations in **Media** and assign shots to them in **Shots**.
2. For each generation, connect the physical files to that generation's H3 node/pass and create matching bindings.
3. Reuse stable logical references across generations even when their physical slot number changes; slots are local to one generation.
4. Set explicit/carry/reset initial states and review continuity before queueing the chain.

## Resolution: frame shape and pixel area

Resolution has two independent controls. **Aspect Ratio** selects the shape of the frame. **Resolution Budget** selects its approximate area.

- **Auto** uses `1280×720` for 16:9, `720×1280` for 9:16, `1080×1080` for 1:1, `960×720` for 4:3, `720×960` for 3:4, and `1680×720` for 21:9.
- **Custom MP** targets a megapixel budget while preserving the selected shape. Final width and height are aligned to 16-pixel steps and shown live on the node.

Changing the aspect ratio is a composition decision; changing the resolution budget is a pixel-area/performance decision. Neither control changes the shot count or carries media.

Only one Studio drawer is active at a time. Collapsing or deleting its node closes it.

## Tabs

### Shots

The shot list uses fixed 60-pixel, two-line rows and mounts only the visible range plus five-row overscan on either side. A separate editor handles the selected shot, so a 64-shot plan does not create 64 expanded editors.

For shot-plan v2, the editor owns:

- stable shot and generation IDs;
- `openingState` and `action` as distinct fields;
- automatic or exact timing;
- transition and cut context;
- complete subject presence and blocking;
- environment/view selection and reference uses;
- camera Start, Path, and sparse End values, including an optional 2–6 point spatial path;
- optional relative action beats, each with a visible action/reaction and linked dialogue delivery;
- appearance and environment transitions.

`openingState` is the visible first-frame condition. `action` is the change that occurs during the shot. Do not repeat the opening state as if it were a second event.

### Subjects

Subjects have a stable logical ID, an H3 subject index, an identity description, identity assets, and a base appearance state. Appearance states can control wardrobe, hair, makeup, accessories, carried items, damage, wetness, body condition, transformation, or another explicitly declared dimension.

Identity and appearance are separate. An appearance state cannot silently replace facial identity. Copying a state creates a new stable ID. A base or referenced state cannot be deleted silently; the UI shows where it is used.

### Environments

An environment separates permanent facts from temporary state:

- permanent geography, architecture, scale, and fixed elements;
- reference views with bounded roles such as overview, alternate, detail, or lighting;
- temporary lighting, weather, atmosphere, condition, time of day, and temporary elements.

A temporary state does not own permanent geometry. A detail view does not become an overview, and a lighting view does not redefine architecture.

### Media and references

The Reference library describes logical references; generation cards describe activation and physical bindings. Logical IDs remain stable while H3 labels such as `<Picture 1>` or `<Video 2>` are derived per generation.

Media setup is deliberately two steps:

1. Choose **+ Add reference** to register the logical reference, its type, identity, analysis, transcript, or camera-transfer intent. This creates metadata only; Prompt Studio does not upload or connect a file.
2. Connect the physical picture, video, or audio in the generation node. The selected reference proposes the first compatible generation and slot — for example, **Assign to Generation 1 · Picture 1** — and writes that binding explicitly.

A logical reference can be reused in several generations. A physical file connection is local to the generation that consumes it; registering the logical reference alone does not make media available to H3.

This distinction allows slot reuse across chained generations without changing asset identity. The same slot may represent a different asset in another generation, but one generation cannot bind two active assets of the same type to the same slot.

### Camera

Shots keeps camera context compact: it shows the selected shot's current instruction and an **Edit camera** action. Camera opens the spatial planner at workspace scale, provides a shot selector, and exposes precise Start/Path/End fields. A path may use 2–6 positions with normalized progress, relative X/Y/Z, subject- or scene-relative coordinates, and straight, smooth, or directed arc interpolation. A four-second **Preview** and scrubber interpolate by each waypoint's actual `at` value, so uneven timing remains visible. The Perspective and Top views edit the same data; they are direction previews, not a physical simulation. Classic motion presets remain available in a collapsed disclosure. Both surfaces read and write the same shot object in `shot_plan_json` v2, so switching sections does not copy or reconcile data.

### Before-generation checks and Review

Overview checks the current in-browser v2 documents immediately, before the node runs. It catches missing shot actions, invalid generation links, incomplete declared presence, empty action beats, invalid spatial timing, deleted references, and reference uses without file-slot assignments. The compact result is either **Ready to generate**, a non-blocking note, or a blocking count; each visible issue opens the relevant Shots, Media, or Camera workspace.

These checks are intentionally bounded and do not replace backend validation. **Review** is populated after execution and remains authoritative for compiled continuity, camera ownership, H3 contract quality, and Prompt Coach guidance.

### Project v2 transfer

**Overview > Import & source tools > Project v2 transfer** copies or imports one validated portable JSON package containing any current native-v2 shot plan, media project, creative treatment, and cinematography documents. All included documents are validated for the supported schema version before any import handler runs. The package never contains physical image, video, or audio files. Legacy v1 sources remain a separate compatibility/import concern and are not promoted into the normal editing flow.

Start and End are temporal phases, not competing owners. An omitted End field inherits Start and is not serialized redundantly.

### Look

Global cinematography values are defaults. Shot Start/Path/End values override the corresponding global aspect for that shot. This normal override is displayed as provenance, not as a red conflict.

The Visual Language selector is organized as **family → era/technique → variant**, with Back and breadcrumb navigation, while committing the same canonical `visualLanguage` token as before. Search stays global and groups matches by family and branch; it includes the visible label, token, family, branch, and conservative aliases. An unknown future token remains visible under **Other** instead of being reset. Visual language is independent from narrative Genre and scene-wide Mood.

Every option has preview-card infrastructure, but this repository intentionally ships no claimed H3 result images. The empty manifest produces one discreet notice for the selector instead of repeating a placeholder on every option. To add project-owned examples later, place an original or licensed local `avif`, `jpg`, `png`, or `webp` file under `web/studio/previews/` and register it in `VISUAL_LANGUAGE_PREVIEW_MANIFEST` with:

- `kind`: `original` or `licensed`;
- a relative `./previews/...` source and descriptive `alt` text;
- provenance `creator`, `source`, `license`, and a 64-character SHA-256 digest.

Remote URLs, missing provenance, unsupported kinds, and invalid digests fall back to the honest placeholder. A sample illustrates the catalog vocabulary only; it must not be described as a predicted or guaranteed H3 output.

### Experimental animation cadence — design only

Animation cadence is **not** currently stored or emitted. Creative Treatment v2 is a closed schema and its frontend sanitizer and Python parser accept only the existing six fields, so adding cadence without a schema revision would either lose the value or break validation.

The proposed additive contract is `animationCadence: "adaptive" | "ones" | "twos" | "threes"`, with absent values interpreted as `adaptive`. A future UI must label it **Experimental**, keep it separate from output FPS, show it only for compatible drawn/stop-motion families or under Advanced, and state that it requests a timing vocabulary rather than guaranteeing model adherence. It should ship only with a schema/parser/compiler update, compatibility tests, prompt-budget tests, and generation evals; no current workflow contains this field.

### Coach

The Coach consumes the ephemeral `minimax_h3_diagnostics` UI payload returned when the node executes. It groups diagnostics by stable code. Editing any canonical widget marks the cached report stale; run the node again before treating it as current.

Coach advice is conservative and bounded to two items per shot and twelve globally. It can flag:

- locomotion without a route/destination and visible final state;
- turns or looks without a target, direction, or result;
- short manipulation without contact, trajectory, or object result;
- ambiguous pronouns when multiple subjects are explicitly present;
- near-duplicate `openingState` and `action`;
- a weak cut only when sufficient structured context proves it;
- dense generic aesthetic modifiers that compete with a selected medium.

Coach findings are advisory. They do not change `valid`, `qualityValid`, the prompt, or the repair request sent to the LLM.

## Canonical structured inputs

### `media_manifest` v2

Manifest v2 is the only project library. It contains:

Its canonical JSON remains an internal, serialized node input; Prompt Studio never expands the technical textarea on the node. Inspect the exact read-only source under **Overview > Import & source tools > Media project v2 > View source**, and make normal changes through the visual Media, Subjects, Environments and Shots editors.

```text
assets ─┬─ subjects ─ appearance states
        └─ environments ─ views / temporary states
generations ─ activation roots / exclusions / bindings / initial states
```

Each generation resolves its own active dependency closure and input map. Only active, available, physically bound assets enter that generation's prompt context. Dependencies include identity assets, active appearance sources, selected environment views, referenced audio, and explicitly transferred camera references.

Activation can be automatic or explicit. An exclusion cannot remove a mandatory dependency. Bindings are validated against asset type, per-type capacity, duplicate slots, soundtrack requirements, total file count, and media-duration limits.

The normative schema is [`schemas/media_manifest_v2.schema.json`](schemas/media_manifest_v2.schema.json). Legacy manifests remain supported by the backend and retain their existing labels and behavior; the Studio keeps them read-only rather than guessing a stateful v2 project.

### `shot_plan_json` v2

Shot-plan v2 is the temporal source of truth. It references project IDs rather than redefining subjects, appearances, environments, or assets. It supports up to 64 shots and groups them by `generationId` in chained mode.

`timingMode: "auto"` omits per-shot duration. `timingMode: "exact"` requires it, and durations are checked per generation. `actionBeats[].at` and camera waypoint `at` values are normalized from 0 to 1, so their rhythm survives duration changes. Beat percentages and editor labels never appear in the enhanced prompt; they compile to natural temporal flow. `cameraEnd` is stored as a delta from `cameraStart`; omitted End properties inherit Start.

The normative schema is [`schemas/shot_plan_v2.schema.json`](schemas/shot_plan_v2.schema.json). Shot-plan v1 remains accepted without changing its generated instruction. The first intentional structured edit migrates a v1 shot plan atomically to v2.

### `creative_treatment_json` v2

Creative Treatment v2 is the canonical editable document for content format, genre, visual language, world aesthetic, scene-wide **Mood (tone)**, and title-screen style. Mood affects staging, camera, light, performance, and mix; line-level speech remains under **Delivery** and **Voice color** below the Basic prompt. The stored key remains `tone`. The normative schema is [`schemas/creative_treatment_v2.schema.json`](schemas/creative_treatment_v2.schema.json).

Legacy v1 remains accepted by the runtime so saved workflows continue to generate, but the Studio does not migrate it during hydration or an unrelated edit. It stays read-only until the user invokes the explicit import action, which validates the source and writes one v2 value.

### `cinematography_json` v2

The 13 existing cinematography controls remain supported in the canonical v2 document. It supplies global defaults and does not outrank an explicit shot value, source fact, or authorized video-camera transfer. The normative schema is [`schemas/cinematography_v2.schema.json`](schemas/cinematography_v2.schema.json).

As with Creative Treatment, runtime parsing accepts a legacy v1 source and canonicalizes it to v2 only in memory. The Studio keeps v1 read-only; only explicit import persists a converted v2 document.

## Camera authority

Camera ownership is resolved independently for each shot, phase, and aspect. Aspects are motion, framing, angle, viewpoint, composition, focus, distance, stability, lens, and parallax. Phases are Start, Path, End, and Whole Shot.

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
