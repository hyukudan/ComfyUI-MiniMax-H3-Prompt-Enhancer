# MiniMax H3 Prompt Studio

Prompt Studio is the structured planning interface embedded in the two enhancer nodes. It keeps the node compact while exposing shots, subjects, appearance states, environments, logical references, camera controls, and diagnostics in a viewport-level drawer.

The separate **MiniMax H3 Visual Reference Director** uses the same v2 contracts but has a production-oriented workspace of its own:

- **Compose** — a draggable scene strip, visual stage, draggable reference tray, semantic drop destinations, reference lanes and contextual inspector, with deeper Details, Staging and Camera modes. A cut can be duplicated with nested camera and reference state intact, moved by drag or arrow controls, and deleted only after inline confirmation; every operation writes the ordinary Shot Plan v2 array with stable IDs. The inspector creates and places a canonical named Subject or Environment atomically, so a new set can immediately receive its Background picture without leaving Compose. The stage exposes the subject's real `<Subject N>` LLM alias, portrait, named voice/performance references and selected environment preview from the same canonical assignments used during compilation. **Dialogue & sound** authors exact spoken lines for a visible subject, selects delivery, previews available default voices and cut audio, and distinguishes voice overrides, exact-dialogue audio and soundtrack references; ambience remains derived from visible action and the Prompt Enhancer's Audio policy instead of introducing competing schema. Each scene shows its own native camera direction as visual **Start · Move · End** phases; clicking that card opens the selected cut in the Camera editor. A read-only **LLM handoff** shows the actual subject and physical H3 aliases, warns when a bound file is still missing, and copies a concise audit brief; it is derived from Media Project + Shot Plan and never becomes another prompt authority. Selecting a tray card enables Image, Voice, Performance and scene destinations as buttons for keyboard and touch use. The adjacent `+` on every destination validates the full logical assignment before upload, then atomically creates its asset, H3 binding, semantic relationship and scene use; an operating-system file may also be dropped directly. If the final document write fails, all workflow documents roll back together; the content-addressed ComfyUI input remains safely reusable. Checked green destinations are already resolved, and their `×` action detaches the destination while preserving its reusable Library media and any wiring still needed elsewhere.
- **Library** — physical media import and preview alongside reusable Subjects and Environments.
- **Wiring** — the resolved picture, video and audio slots, their semantic roles, activation and physical-file readiness.
- **Look** — an explicit handoff to the connected Prompt Enhancer, which remains the sole owner of creative direction and global cinematography.

Compose is also the first destination inside the enhancer's Prompt Studio. When a Visual Reference Director feeds the enhancer's `reference_context`, that Compose view operates on the connected Director's canonical project and physical references while keeping the enhancer's prompt context; it does not copy them into a second project. The Director's own drawer remains a focused Library/Wiring maintenance surface.

It does not add a project manager, a network service, or another ComfyUI output. The canonical project remains in the existing `media_manifest`, `shot_plan_json`, `creative_treatment_json`, and `cinematography_json` widgets saved with the workflow.

## Open the Studio

The enhancer node presents a primary **Open Compose** action plus destination chips:

- **Compose** — visually assemble the prompt from shots, subjects, voices, backgrounds, action, dialogue, camera and references.

- **Shots** — number of structured shots.
- **Staging** — positioned cast members in the selected shot.
- **Subjects** — number of logical subjects.
- **Environments** — number of logical environments.
- **Media** — bound physical slots versus logical references.
- **Camera** — the selected shot's visual camera planner and precise Start/Path/End controls.
- **Look** — creative direction and global cinematography defaults.
- **Review** — current structured diagnostic count and Prompt Coach advice.

Selecting **Open Compose** or a chip opens one drawer attached to that node. The primary button changes to **Close Studio** while the drawer is open. The drawer is mounted to the browser viewport, so it does not scale with the ComfyUI canvas. It defaults to 720 px on ordinary desktops, 820 px on wide displays, and 920 px on 4K/high-resolution displays. The resizable range is 420 px to `min(1100px, 60vw)`; below 700 px the drawer becomes full-width, and below 600 px of content the master/detail editors stack into one column. Close it from that same node button, the header close button, or `Esc`; focus returns to the control that opened it so the normal ComfyUI **Generate / Queue** action is available again. The navigation rail supports arrow keys, Home, End, and numeric shortcuts 1–9.

There is no separate Save action. Every explicit add, edit, assignment, reorder, or deletion is committed immediately to this node's structured v2 widgets and is saved with the ComfyUI workflow. Merely opening, closing, navigating, expanding a disclosure, or hydrating old data does not write anything.

Empty authoring fields use instructional placeholders. The example disappears on focus and returns on blur only while the field remains empty; it is never stored in project JSON or compiled into the prompt. Required empty drafts remain visibly editable and Review identifies them before generation instead of substituting invented prose.

**Guided / Advanced** is a Look-specific presentation control and therefore appears inside **Look**, not in the global Studio header. Guided presents the principal Look controls first and places neutral specialist fields behind a labelled disclosure; if an advanced Creative Treatment value is already active, that disclosure opens and reports the active count. Advanced renders every available Look field. Switching modes never clears, rewrites, or adds a workflow field, and it does not affect Shots, Media, Camera, Subjects, Environments, or Review.

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
| **Staging** | Arrange the cast visually before directing the camera. | Per-shot subject start/end positions, movement, facing, and eyelines in Shot Plan v2. |
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

1. Add **MiniMax H3 Visual Reference Director** and choose **Open director**. Its raw storage widgets remain hidden.
2. In **Media**, choose **Import files** and select pictures, video or audio. The Director copies them into ComfyUI input storage and creates stable logical assets with visual previews.
3. Drop each visual card onto the subject identity/voice, environment/background, or shot performance/camera property it controls.
4. In the target generation, verify the derived **physical slot** (`Picture N`, `Video N`, or `Audio N`).
5. Connect `reference_context` to Prompt Enhancer. Connect the ordered `pictures`, `videos` and `audios` list outputs to a list-aware H3 adapter (or split them into its numbered native slots). They come from the same assignments, so the prompt and tensors stay aligned.
6. Optionally connect `reference_project` to **MiniMax H3 Reference Project Inspector** for the exact wiring report.

### Chained Multishot — several generation passes

1. Create the ordered generations in **Media** and assign shots to them in **Shots**.
2. For each generation, connect the physical files to that generation's H3 node/pass and create matching bindings.
3. Reuse stable logical references across generations even when their physical slot number changes; slots are local to one generation.
4. Set explicit/carry/reset initial states and review continuity before queueing the chain.

## Resolution: frame shape and pixel area

Resolution has two independent controls. **Aspect Ratio** selects the shape of the frame. **Resolution Budget** selects its approximate area.

- **Auto** uses `1280×720` for 16:9, `720×1280` for 9:16, `1080×1080` for 1:1, `960×720` for 4:3, `720×960` for 3:4, and `1680×720` for 21:9.
- **Custom MP** enables and focuses the always-visible MP field, accepts any positive finite value (decimal point or comma) without an artificial minimum or maximum, and persists it when you leave the field or press Enter. It targets a megapixel budget while preserving the selected shape; final width and height are aligned to 16-pixel steps and shown live on the node.

Resolution Budget drives the enhancer's `width` and `height` outputs, not creative prose. Connect those outputs to the H3 generator; if a separate Resolution Selector supplies the generator dimensions, that downstream node overrides the Studio budget.

Changing the aspect ratio is a composition decision; changing the resolution budget is a pixel-area/performance decision. Neither control changes the shot count or carries media.

Only one Studio drawer is active at a time. Collapsing or deleting its node closes it.

## Tabs

### Shots

The shot list uses fixed 60-pixel, two-line rows and mounts only the visible range plus five-row overscan on either side. A separate editor handles the selected shot, so a 64-shot plan does not create 64 expanded editors.

For shot-plan v2, the editor owns:

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

### Subjects

Subjects have a stable logical ID, an H3 subject index, an identity description, identity assets, an optional default voice asset, and a base appearance state. The default voice is inherited whenever the subject is active; a shot-level `voice` reference is an explicit override for that scene. Appearance states can control wardrobe, hair, makeup, accessories, carried items, damage, wetness, body condition, transformation, or another explicitly declared dimension.

A Subject is a reusable library definition, while prompt inclusion is an explicit casting decision. New subjects are included in the currently selected generation by default. Existing subjects can be sent without creating a shot through **Use in prompts → Always include in Generation …**; alternatively, mark them `present`, `enters`, or `exits` under **Shots → Who’s in it**. Active subjects compile into authoritative lines such as `<Subject 1> (Juan): …`. Review warns when a valid library subject is neither included in a generation nor cast in a shot, because it will not reach the LLM.

Identity and appearance are separate. An appearance state cannot silently replace facial identity. Copying a state creates a new stable ID. A base or referenced state cannot be deleted silently; the UI shows where it is used.

### Environments

An environment separates permanent facts from temporary state:

- permanent geography, architecture, scale, and fixed elements;
- reference views with bounded roles such as overview, alternate, detail, or lighting;
- temporary lighting, weather, atmosphere, condition, time of day, and temporary elements.

A temporary state does not own permanent geometry. A detail view does not become an overview, and a lighting view does not redefine architecture.

### Media and references

The Reference library describes logical references; generation cards describe activation and physical bindings. Logical IDs remain stable while H3 labels such as `<Picture 1>` or `<Video 2>` are derived per generation.

**Plan by outcome** provides an inline, cancelable first-binding assistant for subject identity, environment view, performance, camera, voice, and continuity. It chooses only from existing shots, generations, subjects, and environments, then prepares the logical asset, its subject/environment relationship when required, a shot-scoped `referenceUse`, and the generation binding as one atomic Media + Shot Plan update. It never connects or uploads the physical file. If a shot belongs to another generation, a required relationship is absent, or the matching physical slot quota is full, the assistant reports that prerequisite deterministically and writes nothing.

The adjacent user-first recipes are contract-safe starting points rather than new schema objects: **Targeted edit** uses an appearance-scoped picture, **Relight** uses a lighting-scoped picture, **Performance transfer** uses a performance-scoped video, and **Continuation** uses a continuity-scoped video. The cards explain what is missing before setup and remain editable through the ordinary asset, shot-use, and binding controls afterward.

**Export LLM planning context** emits `minimax-h3-planning-context` format version 1. It is a read-only discussion artifact containing the current v2 Media Project and Shot Plan plus explicit instructions to preserve IDs and generation boundaries. It contains no physical files, performs no network request, has no import action, and never applies an LLM response automatically.

Media setup is deliberately two steps:

1. Choose **+ Add reference** to register the logical reference, its type, identity, analysis, transcript, or camera-transfer intent. This creates metadata only; Prompt Studio does not upload or connect a file.
2. Connect the physical picture, video, or audio in the generation node. The selected reference proposes the first compatible generation and slot — for example, **Assign to Generation 1 · Picture 1** — and writes that binding explicitly.

A logical reference can be reused in several generations. A physical file connection is local to the generation that consumes it; registering the logical reference alone does not make media available to H3.

This distinction allows slot reuse across chained generations without changing asset identity. The same slot may represent a different asset in another generation, but one generation cannot bind two active assets of the same type to the same slot.

### Camera

Shots keeps camera context compact: it shows the selected shot's current instruction and an **Edit camera** action. Camera opens the spatial planner at workspace scale, provides a shot selector, and exposes precise Start/Path/End fields. A path may use 2–6 positions with normalized progress, relative X/Z in −1…1, Y height in −1…1, subject- or scene-relative coordinates, and straight, smooth, or directed arc interpolation. Its 3D view uses a four-corner isometric floor rather than a perspective funnel. Camera height does not alter the icon's position on that floor: dragging the camera changes X/Z while preserving Y, and the **Camera height** slider represents height by scaling the icon (larger when low, smaller when high). Top view isolates horizontal placement; Front view shows elevation directly. **Distance from anchor** moves the camera nearer or farther along its current direction without changing height. Camera height uses five semantic bands: **Very low, Low, Eye level, Elevated, Very elevated**. The normalized number remains storage detail rather than the primary label, and untouched paths start at neutral eye level. Between positions, the compiler classifies the real height delta as held, drifting, moving, or sweeping; it states rise/descent at the destination, marks crossings of the eye line, and summarizes the whole vertical profile before listing waypoints. Horizontal distance is also compiled even when framing is explicitly set. Small slider jitter remains silent. Camera-body height and lens tilt are independent, so **Very elevated** does not silently force an overhead or high-angle view. The toolbar exposes the overall path shape, pace, speed change and reference frame, and each position exposes framing, angle, aim and timing. A four-second **Preview** and scrubber interpolate by each waypoint's actual `at` value, so uneven timing remains visible. All three views edit the same data and are direction previews, not a physical simulation. Classic motion presets remain available in a collapsed disclosure. Both surfaces read and write the same shot object in `shot_plan_json` v2, so switching sections does not copy or reconcile data.

### Staging

Staging shares the selected shot with Shots and Camera. **Create staging** places the shot's present cast across the frame only after that explicit action. Drag each named subject in 3D, Top, or Front view; choose Start or End positions, a movement verb, and whether the subject faces the camera, travel, a side of frame, away from camera, or another named subject. It compiles as qualitative blocking and eyeline prose—not XYZ values. Free-text blocking remains available for nuance; Review notes when both are present so contradictory arrangements are not silently merged.

Camera **Anchor** and **Aim target** are deliberately separate. Anchor establishes the origin for camera position (for example, left of Juan or behind Juan). Each waypoint's Aim target says where the lens points and may select a different present subject. If that subject has no Staging position, its name still reaches H3 but Studio reports that the reticle is only a placeholder. New waypoints inherit the prior resolved aim; target changes compile as a smooth reframe instead of numeric pan/tilt.

### Before-generation checks and Review

Overview checks the current in-browser v2 documents immediately, before the node runs. It catches missing shot actions, invalid generation links, incomplete declared presence, empty action beats, invalid spatial timing, deleted references, and reference uses without file-slot assignments. The compact result is either **Ready to generate**, a non-blocking note, or a blocking count; each visible issue opens the relevant Shots, Media, or Camera workspace.

These checks are intentionally bounded and do not replace backend validation. **Review** is populated after execution and remains authoritative for compiled continuity, camera ownership, H3 contract quality, and Prompt Coach guidance.

### Project v2 transfer

**Overview > Import & source tools > Project v2 transfer** copies or imports one portable JSON package containing any current native-v2 shot plan, media project, creative treatment, and cinematography documents. Import validates nested arrays, identifiers, field types, limits, and supported schema versions, then shows a preview with document counts. **Replace project** applies the complete preview atomically: all target storage widgets are available before writing, and exact raw snapshots are restored if a widget callback or hydration step fails. **Append generations** retains the current project and adds the package's generations and shots with collision-safe IDs; shared subjects, environments, appearances, and assets must be identical when their IDs match, so append cannot silently merge conflicting definitions. The package never contains physical image, video, or audio files. Legacy v1 sources remain a separate compatibility/import concern and are not promoted into the normal editing flow.

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

## Canonical structured inputs

### `media_manifest` v2

Manifest v2 is the only project library. It contains:

Its canonical JSON remains an internal, serialized node input; Prompt Studio never expands the technical textarea on the node. Inspect the exact read-only source under **Overview > Import & source tools > Media project v2 > View source**, and make normal changes through the visual Media, Subjects, Environments and Shots editors.

```text
assets ─┬─ subjects ─ appearance states
        └─ environments ─ views / temporary states
generations ─ activation roots / exclusions / bindings / initial states
```

Each generation resolves its own active dependency closure and input map. Only active, available, physically bound assets enter that generation's prompt context. Dependencies include identity assets, the subject's optional default voice, active appearance sources, selected environment views, referenced audio, and explicitly transferred camera references.

Activation can be automatic or explicit. An exclusion cannot remove a mandatory dependency. Bindings are validated against asset type, per-type capacity, duplicate slots, soundtrack requirements, total file count, and media-duration limits.

The normative schema is [`schemas/media_manifest_v2.schema.json`](schemas/media_manifest_v2.schema.json). Legacy manifests remain supported by the backend and retain their existing labels and behavior; the Studio keeps them read-only rather than guessing a stateful v2 project.

### `shot_plan_json` v2

Shot-plan v2 is the temporal source of truth. It references project IDs rather than redefining subjects, appearances, environments, or assets. It supports up to 64 shots and groups them by `generationId` in chained mode. Spatial camera paths distinguish camera position from camera aim: `anchorTarget` names the project subject used as the origin, while each waypoint may inherit aim, keep the anchor framed, follow travel, aim at a named `aimTarget`, or use a custom editor direction. Optional `staging` places each subject at qualitative start/end positions with movement and facing. The compiler resolves all of this into names and natural camera/blocking prose; internal XYZ, timing percentages, angle degrees, and enum tokens do not become camera instructions.

`timingMode: "auto"` omits per-shot duration. `timingMode: "exact"` requires it, and durations are checked per generation. `actionBeats[].at`, optional `actionBeats[].endAt`, and camera waypoint `at` values are normalized from 0 to 1, so their rhythm survives duration changes. Beats may use neutral projected **calls out** delivery as well as the other documented verbs. The editor warns about overlaps, large fully-authored gaps, and dialogue that is likely too dense for its exact span using a transparent 150-words-per-minute estimate. Beat percentages and editor labels never appear in the enhanced prompt; they compile to natural temporal flow. Camera timing may also target **during dialogue** or **after dialogue**. `cameraEnd` is stored as a delta from `cameraStart`; omitted End properties inherit Start. Shot transitions include ordinary cuts plus cross dissolve and fade through black. `scaleRelationships` describes only explicitly authored relative scale between present subjects and never supplies invented measurements.

The normative schema is [`schemas/shot_plan_v2.schema.json`](schemas/shot_plan_v2.schema.json). Shot-plan v1 remains accepted without changing its generated instruction. The first intentional structured edit migrates a v1 shot plan atomically to v2.

### `creative_treatment_json` v2

Creative Treatment v2 is the canonical editable document for content format, genre, visual language, world aesthetic, scene-wide **Mood (tone)**, and title-screen style. Mood affects staging, camera, light, performance, and mix; line-level speech remains under **Delivery** and **Voice color** below the Basic prompt. The stored key remains `tone`. The normative schema is [`schemas/creative_treatment_v2.schema.json`](schemas/creative_treatment_v2.schema.json).

The Mood control is searchable and grouped by creative intent. Every option includes a short description that distinguishes nearby choices and states its anti-invention boundary; a persistent footer clarifies that Mood never adds facts, dialogue, or music. Search indexes the label, stored token, group, and description, so both **pulp** and **heightened** find the same `pulp_heightened` option. Unknown future values display as **Unavailable — token** and remain byte-preserved until deliberately replaced.

Legacy v1 remains accepted by the runtime so saved workflows continue to generate, but the Studio does not migrate it during hydration or an unrelated edit. It stays read-only until the user invokes the explicit import action, which validates the source and writes one v2 value.

### `cinematography_json` v2

The 13 existing cinematography controls remain supported in the canonical v2 document. It supplies global defaults and does not outrank an explicit shot value, source fact, or authorized video-camera transfer. The normative schema is [`schemas/cinematography_v2.schema.json`](schemas/cinematography_v2.schema.json).

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
