# ComfyUI MiniMax H3 Prompt Enhancer

Guide-constrained prompt enhancement, repair, and validation nodes for MiniMax H3 workflows in ComfyUI.

[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB.svg)](pyproject.toml)
[![Status: Beta](https://img.shields.io/badge/status-beta-orange.svg)](#project-status-and-license)

The main node turns a short request into MiniMax H3's documented audiovisual prompt structure. It can use either:

1. an OpenAI-compatible endpoint, including services exposed by Ollama, LM Studio, or another provider; or
2. a local GGUF selected from `ComfyUI/models/llm_gguf`, launched through an isolated `llama-server` process.

The package does not bundle model weights or llama.cpp, does not inspect reference pixels, and does not replace H3 conditioning. It prepares and validates text for native or custom H3 workflows.

## Contents

- [Why use it?](#why-use-it)
- [Backend design](#backend-design)
- [Quick start](#quick-start)
- [Get the best result](#get-the-best-result)
- [Interface behavior](#interface-behavior)
- [Nodes](#nodes)
- [Exact wiring](#exact-wiring)
- [Prompt contracts](#prompt-contracts)
- [Description enhancement](#description-enhancement)
- [Creative direction and explicit shot plans](#creative-direction-and-explicit-shot-plans)
- [Chained multishot and per-shot execution](#chained-multishot-and-per-shot-execution)
- [Dialogue, language, and exact text](#dialogue-language-and-exact-text)
- [Audio policies](#audio-policies)
- [References](#references)
- [Output metadata](#output-metadata)
- [Installation](#installation)
- [Models and llama.cpp](#models-and-llamacpp)
- [Memory policy](#memory-policy)
- [Workflow compatibility and migration](#workflow-compatibility-and-migration)
- [Privacy and security](#privacy-and-security)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Project status and license](#project-status-and-license)

## Why use it?

MiniMax H3 responds best when actions, timing, camera, dialogue, language, and sound follow the structure expected by the selected generation mode. This pack makes that structure explicit and machine-checkable.

| Need | What the pack provides |
|---|---|
| Rewrite a basic idea | A switchable remote/local Prompt Enhancer |
| Use a local quantized LLM | GGUF discovery and isolated llama.cpp execution |
| Preserve dialogue | Exact quoted text and mandatory `<d>[Language] ...</d>` blocks |
| Reuse another LLM node | Separate system/user instructions from Prompt Guide Builder |
| Check authored text | Model-free structural validation and repair feedback |
| Control generated audio | Independent ambience/foley, score, and voice-performance policies |
| Apply a reusable creative treatment | Independent genre, visual-language, world-aesthetic, and tone profiles |
| Set presentation without rewriting the story | Optional color, exposure, camera, optics, depth, texture, lens-effect, and motion-rendering controls |
| Author exact cuts or chained segments | A visual shot-plan editor with automatic or exact timing |
| Feed duration downstream | `duration_seconds` output on both enhancer nodes |
| Plan independent chained generations | `chained_multishot` mode plus Chained Multishot Output |
| Ground prompts in connected media metadata | Optional JSON media manifest and Manifest Validator |
| Reclaim VRAM before H3 | Per-run unload by default, with optional persistent mode |

Validation is a structural gate. It cannot guarantee visual quality, identity fidelity, physical correctness, or diffusion-model compliance.

## Backend design

| Route | Runtime | Best for | Memory lifecycle |
|---|---|---|---|
| OpenAI-compatible | LM Studio, Ollama, or another compatible API | Existing local/remote LLM services | Controlled by that service |
| Local GGUF | Standalone `llama-server` | Direct use of GGUF files without a separate API server | Close after every prompt by default, or keep loaded on request |
| Existing ComfyUI LLM node | QwenVL/GGUF/other node plus Guide Builder | Reusing a loader already present in the graph | Controlled by that node |

### Why standalone llama-server?

Some ComfyUI prompt enhancers import `llama-cpp-python` inside the long-running ComfyUI process. This pack deliberately uses a standalone `llama-server` for its direct GGUF route:

- newer llama.cpp builds can support newer architectures or quantizations without replacing a Python/CUDA wheel shared by other custom nodes;
- a native-model crash is isolated from ComfyUI;
- terminating the process releases its RAM and VRAM deterministically;
- the same OpenAI-compatible request pipeline is used for remote and local execution.

The trade-off is model startup time when `keep_server_loaded` is disabled. Users with sufficient VRAM can keep the process alive between prompt-enhancement calls.

`llama-server` is required only for the local GGUF route. The endpoint route, Guide Builder, and Validator do not need it.
It is a native executable, not a Python package, so it is intentionally absent from `pyproject.toml`/`requirements`.
The node pack does not install, download, or update llama.cpp. Another custom node or ComfyUI distribution may already
have placed a compatible runtime under the discovered directory; that runtime can be reused without copying it.

## Quick start

### OpenAI-compatible server

1. Install the node pack and restart ComfyUI.
2. Start an OpenAI-compatible server. Common local API roots include Ollama's `http://127.0.0.1:11434/v1` and LM Studio's `http://127.0.0.1:1234/v1`.
3. Add **MiniMax H3 Prompt Enhancer** from `MiniMax H3 → Prompting`.
4. Open **Model setup** and select **OpenAI-compatible API**.
5. Enter the endpoint and API key if required, then press **Refresh API model list**.
6. Choose the model under **Available API models**, or type its exact server ID into **API model ID**. Leaving the ID blank asks the node to choose a suitable chat/instruct model automatically.
7. Start with `mode=auto`, `enhance_description=true`, and the default audio policies. Select a creative treatment or
   add explicit shot rows only when you want those constraints.
8. In normal modes, connect `enhanced_prompt` to H3 conditioning, `duration_seconds` to the downstream duration
   control, and optionally route `aspect_ratio` to geometry-selection logic. In `chained_multishot`, do not send the
   whole JSON object to H3: select or iterate its individual `prompts` and run one H3 generation per item.
   Inspect
   `validation_report.valid` before a costly render; a completed LLM request can still return a structurally invalid
   best candidate.

Loopback endpoints work by default. Sending prompts to another host requires `allow_remote_endpoint=true`.

### Local GGUF without a separate API server

1. Install a current official llama.cpp build containing `llama-server` or `llama-server.exe`.
2. Place one or more text-generation GGUF files in `ComfyUI/models/llm_gguf/`.
3. Restart ComfyUI or refresh node definitions.
4. Add **MiniMax H3 Prompt Enhancer**, open **Model setup**, and select **Local GGUF via llama.cpp**.
5. Select `local_model` and the detected `llama_server_path` from their dropdowns. When models are present, the first
   discovered GGUF is selected by default; the “no models found” placeholder appears only for an empty discovery list.
6. Leave `keep_server_loaded=false` when H3 needs the VRAM immediately afterward.

The direct-GGUF route is text-only. Select the language-model GGUF, not an `mmproj` file. `gpu_layers=auto`,
`context_size=16384`, `threads=0`, and `startup_timeout=180` are safe starting values. The first request includes
model startup; later requests are faster only when `keep_server_loaded=true`.

## Get the best result

### Choose the mode by the role of the supplied media

`auto` can resolve from explicit labels and media metadata, but an explicit mode is clearer when the media's role is
already known. The same image file can require different modes depending on how H3 should use it:

| What H3 receives | Use |
|---|---|
| No reference media | `t2va` |
| One image that must be the exact first frame | `i2va` |
| Exact first and last frames | `fl2va` |
| One image that must be the exact last frame | `l2va` |
| Identity, appearance, object, style, motion, camera, video-edit, continuation, or audio references | `ref2va` |
| Several autonomous H3 generations that will be assembled or chained later | `chained_multishot` |

An identity image is not automatically I2VA: use Ref2VA when it supplies who or what should appear but is not the
literal opening frame. `reference_context` and `media_manifest` describe roles; this node never inspects connected
pixels, frames, or waveforms.

### Write a source prompt that gives the enhancer facts to preserve

The enhancer can develop direction, but it should not invent the central content. For demanding scenes, state as many
of these as matter:

- subject count, identity, age category, appearance, wardrobe, and which reference supplies each element;
- location, time, weather, important props, and initial spatial relationships;
- actions in causal order, including actor, limb or manipulated object, contact point, physical response, and resulting
  state when interaction matters;
- the required final visible state, especially ownership, position, open/closed state, damage, or transformation;
- whether the scene is one continuous take or where literal cuts occur;
- any indispensable shot scale, viewpoint, camera move, or point-of-view owner;
- exact spoken words and their language, and exact visible text;
- required ambience, physical sounds, music, or explicit absence of them.

Use straight double quotes only for literal dialogue, lyrics, or visible text, not for emphasis. Structural prompt prose
is written in English because that is the official H3 contract; dialogue, lyrics, and visible text retain their exact
authored language.

Example source prompt:

```text
One continuous 8-second shot. The same adult mechanic from image 1, wearing the supplied blue coveralls, approaches
the left-hand-drive red coupe from its driver's side. She grips the exterior handle with her right hand, pulls the
door fully open, steps in left leg first, sits behind the steering wheel, brings her right leg inside, and closes the
door. Keep the car, handle, door hinge, her hands, and both feet readable during contact. She ends seated behind the
wheel with the door closed, looks at camera, and says in Spanish: "Vamos." No background music.
```

This is more useful than a longer list of adjectives because it gives H3 observable geometry, contacts, continuity,
causality, and an exact ending.

### Understand precedence

The controls resolve by domain rather than through one ambiguous global ranking:

1. Content facts come from the Basic prompt, connected-reference metadata, exact text/dialogue, explicit shot rows,
   and chained identity/voice/setting locks. The enhancer cannot replace them.
2. Audio policies are absolute gates for ambience/foley, audience-only score, and voice performance. Creative profiles
   cannot turn a disabled layer back on.
3. A specific instruction in a shot row or source/reference description overrides a conflicting global presentation
   preference for that shot.
4. Global Cinematography overrides conflicting Creative direction advice in the same presentation domain.
5. Creative direction and active description enhancement fill only compatible unspecified direction.

Examples: `action + Static shot` retains action staging without camera movement; `dark + high-key` keeps the explicit
high-key exposure while dark can still influence pacing or performance; a reference-authoritative red jacket remains
red even if monochrome treatment would otherwise apply.

### What Enhance description changes

| Behavior | Enabled | Disabled |
|---|---|---|
| Convert to the documented H3 structure | yes | yes |
| Preserve source facts, exact text, references, timing, and audio gates | yes | yes |
| Creative direction | applied to unspecified direction | stored but not applied |
| Cinematography | applied | applied |
| Explicit Shot/Segment plan | applied | applied |
| Develop composition, blocking, performance, light, materials, camera, continuity, and permitted sound | active | minimum needed for coherence |
| Chained items | richly developed autonomous segments | conservative autonomous adaptation |

When enabled, the LLM is instructed to make every addition visibly observable or audibly motivated. It establishes
shot scale, composition, positions, orientation, eyelines, prop state, actions/reactions, state changes, material
response, permitted sound, and a concrete ending in playback order. It preserves screen direction, handed contact,
object possession, and open/closed or intact/changed states across cuts. It prefers specific geometry, material,
position, motion, and cause-and-effect over generic cinematic adjectives.

`max_tokens=4096` is normally ample. If the result is complete but shallow, supply more concrete facts, use only the
profiles that add useful direction, select a stronger instruct model explicitly, and inspect warnings. Increasing the
token ceiling alone does not force depth, and a Ref2VA result below the recommended 350 words is a warning rather than
an automatic repair trigger. Increase both output and context capacity only for genuinely truncated output,
dialogue-dense Ref2VA, or large chained packages; repairs also need context for the previous complete candidate.

### Practical recipes

- **Simple T2VA:** describe the event and ending, keep `mode=auto` or `t2va`, enable description enhancement, and leave
  optional panels neutral until the basic result is stable.
- **Exact first-frame animation:** use `i2va`, describe what must develop after Picture 1, and avoid re-describing a
  conflicting opening composition.
- **Identity + motion + voice:** use Ref2VA; define which Picture supplies identity, which Video supplies motion, and
  which Audio supplies voice. Use a media manifest when those bindings must be machine-validated.
- **Precise edit:** add Shot plan rows in exact narrative order. Use exact timing only when the boundary matters;
  otherwise let the LLM distribute the effective duration.
- **Long sequence:** use `chained_multishot`, give each Segment plan row one autonomous causal unit, repeat only stable
  facts through the locks, and generate each returned JSON item separately. The schema limit of 64 items is not a
  practical recommendation; split very large sequences into manageable batches.

## Interface behavior

The main node keeps the everyday controls visible and places setup-heavy controls in compact accordions. All accordions
start closed and expand downward; their open/closed state is saved in node properties, not in positional widget values:

- **Model setup** selects **OpenAI-compatible API** or **Local GGUF via llama.cpp**, then shows only that backend's
  endpoint/model/key or GGUF/runtime/offload controls. Its summary reports the active backend and model.
- **Chained multishot** appears only in `chained_multishot` mode and contains segment count plus identity, voice, and
  setting continuity. Every segment uses the global Duration; incompatible per-row duration controls are disabled.
- **Creative direction** contains Narrative genre, Visual language, World / aesthetic, and Tone. Its summary lists only
  active choices and reads **No preferences** when neutral.
- **Cinematography** contains optional presentation controls for color palette, exposure/contrast, camera motion plus
  amplitude and speed, optics, depth of field, image texture, lens effects, and motion rendering. Its summary lists
  only active choices and reads **No preferences** when neutral.
- **Shot plan** becomes **Segment plan** in chained mode. Its summary shows row count and Auto or Exact timing.
  **+ Add shot** becomes **+ Add independent segment** in chained mode.
- **Advanced settings** is always the last section. It contains exact frames, structured media metadata, generation
  timeout/repair controls, token budget, temperature, and thinking control. Its summary calls out non-default exact
  frames or active metadata.
- `add_instrumental` reveals **Music genre / style** immediately below **Background score**, followed by
  **Instrumental description** in the main flow.
- `ref2va` reveals **Reference notes**. Existing non-empty reference notes remain visible in every mode.

The accordion controls are non-persistent presentation proxies over the original canonical widgets. Hidden canonical
fields retain and serialize their saved values, and only the selected backend is executed. The model picker, refresh
button, and visual direction/planning controls are deliberately not serialized as extra widgets. The three hidden JSON
storage fields behind Creative direction, Shot plan, and Cinematography remain normal serialized inputs. This separation allows visual
reordering without shifting positional workflow values when the extension is updated.

Long text areas such as Video description, Reference notes, and Media metadata JSON have a draggable resize handle below the field. Their chosen heights are saved with the workflow; double-clicking the handle restores the default height, and keyboard users can resize with Up/Down (Shift for a larger step). Refreshing a model list does not resize them, avoiding the previous feedback loop in which multiline fields grew after every refresh.

Multiline inputs have a persistent title above the field plus a short example placeholder inside it for the video
request, reference notes, media JSON, instrumental direction, and multishot continuity locks. Placeholders disappear
as soon as you type and are never submitted to the model or saved as workflow values. The headings are presentation
only and do not add serialized widgets to the workflow.

## Nodes

All nodes appear under `MiniMax H3 → Prompting`.

### MiniMax H3 Prompt Enhancer

The primary switchable node.

Outputs:

| Output | Meaning |
|---|---|
| `enhanced_prompt` | Normalized prompt for H3 conditioning in normal modes; canonical `{"prompts":[...]}` in `chained_multishot` |
| `validation_report` | Resolved mode, errors, and recommendations |
| `enhancement_manifest` | Backend/model/mode/memory metadata; never contains an API key |
| `duration_seconds` | Effective downstream duration; in chained mode this is the duration of each independent segment, not their combined runtime |
| `aspect_ratio` | Selected target geometry (`auto`, `21:9`, `16:9`, `4:3`, `1:1`, `3:4`, or `9:16`) for downstream routing; it does not calculate pixels |

Shared controls:

| Control | Default | Behavior |
|---|---:|---|
| `mode` | `auto` | Chooses from explicit manifest mode/roles first, then reference labels, otherwise T2VA |
| `duration_seconds` | `5.0` | H3 generation duration (4–15 s); frame count becomes the effective downstream duration when supplied |
| `reference_context` | blank | Optional plain-language descriptions of supplied reference assets and their roles; this does not contain the media itself |
| `aspect_ratio` | `auto` | Adds target geometry to the rewrite request without inventing an H3 section |
| `frame_count` | `0` | Advanced exact H3 frame count on the `17 × n + 5` grid; zero means “derive generation length from duration” |
| `media_manifest` | blank | Advanced authoritative JSON inventory of supplied files, roles, durations, subject mappings, analyses, and transcripts |
| `show_advanced_controls` | disabled | Reveals media metadata JSON and exact-frame controls without changing their saved values |
| `multishot_shot_count` | `0` | Exact autonomous prompt count for `chained_multishot`; zero infers it |
| `multishot_*_lock` | blank | Optional identity, voice and setting clauses inserted verbatim into every autonomous prompt |
| `creative_treatment_json` | blank | Canonical storage for the four optional creative-direction selectors; blank is completely neutral |
| `shot_plan_json` | blank | Canonical storage for ordered explicit shots or autonomous chained segments; blank preserves automatic planning |
| `cinematography_json` | blank | Canonical storage for optional non-narrative image-presentation and camera controls; blank is completely neutral |
| `use_remote_model` | enabled | Endpoint when enabled; local GGUF when disabled |
| `enhance_description` | enabled | Adds bounded cinematic direction while preserving source facts and exact text |
| `ambience_foley_policy` | `auto` | Controls non-musical, non-spoken scene sound: environment plus physical action sounds |
| `background_score_policy` | `follow_prompt` | Follow the source, add an instrumental score, or force music off |
| `instrumental_description` | empty | When `add_instrumental` is selected, describe instrumentation, tempo, rhythm, and dynamics; mood wording is translated into audible parameters |
| `instrumental_style` | `none` | Optional arrangement grammar applied to the instrumental description when `add_instrumental` is active |
| `voice_performance` | `audible` | Audible dialogue, experimental silent mouth acting, or no voice performance |

Generation and repair controls:

| Control | Default | Accepted range / behavior |
|---|---:|---|
| `temperature` | `0.2` | 0–2; lower values are usually more reliable for the strict output contracts |
| `max_tokens` | `4096` | 512–32768 output tokens per completion |
| `timeout_seconds` | `300` | 10–1800 seconds for endpoint model discovery and each endpoint completion |
| `repair_attempts` | `2` | 0–4 additional attempts for both applicable dialogue-ledger planning and main-prompt repair |
| `disable_thinking` | enabled | Requests reasoning-off output where supported; see [Remote API behavior](#remote-api-behavior) |

Remote-only controls:

| Control | Default | Behavior |
|---|---:|---|
| `endpoint` | `http://127.0.0.1:1234/v1` | OpenAI-compatible API root; a trailing `/chat/completions` is normalized back to its root |
| `model` | blank | Exact server model ID; blank discovers and chooses a compact chat/instruct candidate |
| `api_key` | blank | Bearer token; blank falls back to `MINIMAX_H3_PROMPT_ENHANCER_API_KEY` for enhancement requests |
| `allow_remote_endpoint` | disabled | Required for every host except `localhost`, `::1`, and `127.*` |

Main-node local controls:

| Control | Default | Behavior |
|---|---:|---|
| `local_model` | discovery list | Text GGUF below `models/llm_gguf` or an environment-registered root |
| `llama_server_path` | discovery list | Existing executable found by environment variable, `PATH`, or the managed runtime directory |
| `gpu_layers` | `auto` | `auto`, `all`, `-1`, or a non-negative integer; `auto` lets llama.cpp choose because no offload flag is sent |
| `context_size` | `16384` | 4096–131072; migrated zero values also resolve to 16384 |
| `threads` | `0` | 0–256; zero leaves llama.cpp's default unchanged |
| `startup_timeout` | `180` | 10–1800 seconds; migrated zero values also resolve to 180 |
| `keep_server_loaded` | disabled | Reuse the same compatible private server instead of releasing the prompt-model memory after the call |

Remote and local values remain saved when hidden, but only the route selected by `use_remote_model` executes.

The 4096-token default is an output ceiling, not a target length. It is comfortably above MiniMax's normal
350–500-word Ref2VA generation description and does not make ordinary T2VA/I2VA/FL2VA/L2VA prompts terse. Increase it
for unusually large chained-multishot packages or exceptionally dialogue-dense full-reference work; also ensure the
local `context_size` can hold the system/user instructions plus the requested output. Raising the ceiling alone does
not improve detail—the `enhance_description` contract and the scene's information load determine useful depth.

In remote mode, press **Refresh API model list** after entering the endpoint and API key. ComfyUI requests the
endpoint's `/models` resource through its own same-origin backend, avoiding browser CORS restrictions. It filters
obvious embedding and reranking models and fills **Available API models**. Selecting an entry copies its exact model
ID into the saved **API model ID** field. The model string must be the ID reported by the server, not a model file path
or a display name invented by this extension. Manual IDs and blank automatic selection remain available for servers
that do not implement discovery. Non-local endpoints still require the explicit safety toggle.

`context_size=0` and `startup_timeout=0` are migration-safe automatic values. They resolve to 16384 tokens and 180
seconds respectively. This prevents workflows saved before those local controls existed from failing ComfyUI's
input-range validation.

### MiniMax H3 GGUF Prompt Enhancer

The specialized direct-GGUF node exposes both model and runtime paths, extra registered model roots, GPU-layer
offload, context, threads, timeouts, and the persistent-process toggle. It returns the same five outputs as the main
enhancer. Its local runtime defaults match the main node except that the request timeout is named `request_timeout`.

`gguf_model_path` must name an existing `.gguf` below a registered root. `registered_model_dirs` adds trusted roots
separated by the operating system path separator (`;` on Windows, `:` on Unix); newlines are also accepted. ComfyUI's
model roots, `MINIMAX_H3_GGUF_MODEL_DIRS`, and the standard LM Studio cache
`~/.cache/lm-studio/models` are already registered. `llama_server_path` must point to a file named exactly
`llama-server` or `llama-server.exe`.

Use it when you need custom paths or prefer a graph dedicated to GGUF. The main node is simpler for models under `ComfyUI/models/llm_gguf`.

### MiniMax H3 Unload GGUF Prompt Model

Stops the optional persistent prompt-model server and releases its RAM/VRAM. It is safe to queue when no persistent
model is loaded. With `unload=true` it returns `unloaded=true` only when a cached process existed; otherwise it returns
`false` and the status `No persistent GGUF server was loaded.` Setting `unload=false` is a no-op.

### MiniMax H3 Prompt Guide Builder

Builds `system_prompt`, `user_prompt`, and `resolved_mode` without calling an LLM. Connect the two prompt outputs to an
existing QwenVL, GGUF, Ollama, or other text-generation node, preserving their system/user roles, then validate its
result. It exposes the same mode, duration, reference, creative, cinematography, shot-plan, audio, aspect, frame, and chained-lock
controls as the enhancer, but no model/runtime or repair controls. It does not normalize or repair the external
model's answer.

### MiniMax H3 Prompt Validator

Validates enhanced or manually authored prompts without running an LLM. It returns the original `prompt` unchanged,
a `valid` boolean, and a JSON `validation_report`. Set `source_prompt` to the original request and mirror the same
mode, duration, reference, media, audio, aspect, frame, chained-lock, creative-treatment, cinematography, and shot-plan controls used
to build the text. Omitting that context prevents source-fidelity checks from knowing what must be preserved.

The Validator checks section order, exact keyframe alignment, shot numbering/timing, explicit-plan boundaries,
language-tagged dialogue, exact quoted and visible text, audio policies, reference labels, retention markers, media
limits, and generation geometry. It checks creative-treatment and cinematography JSON for valid supported
configurations, but it cannot prove that free-form prose aesthetically realizes either selection. Errors make
`valid=false`; warnings are
advisory, such as recommended Ref2VA length, sound-section sentence counts, dialogue budget, or continuity risk.

`valid=true` confirms the documented structure and literal invariants that the validator knows how to check. It does
not prove rendered visual quality, physical correctness, every semantic quantity or state, compliance with a shot-row
description, identity fidelity in pixels, or aesthetic adherence to Creative direction or Cinematography. Likewise,
`applied=true` in a manifest means that a control was injected into the LLM request, not that the LLM or H3 obeyed it.

### MiniMax H3 Media Manifest Validator

Normalizes a JSON media inventory, assigns effective `<Picture N>`, `<Video N>`, and `<Audio N>` labels in input
order, and checks the documented reference limits. Enabled video soundtracks consume an audio ordinal before later
standalone audio. Outputs are `normalized_manifest`, `valid`, `validation_report`, and generated
`reference_context`. Validation errors are returned in the report rather than raised.

### MiniMax H3 Chained Multishot Output

Accepts canonical `{"prompts":[...]}`, a top-level JSON string array, or a `---`-separated script and normalizes it to
the canonical object. It validates the optional exact item count, source dialogue/visible text, and the three
continuity locks; locks missing from an item are prepended deterministically before validation. Outputs are
`multishot_script`, compact canonical `prompts_json`, `valid`, `validation_report`, and
`total_duration_seconds = duration_per_shot × prompt count`. `duration_per_shot` defaults to 10.1 seconds and accepts
4–15 seconds.

Each item is an independent conditioning pass, not a `[Shot N]` inside one generation. This node formats the plan; it
does not queue H3 renders. Generate each item separately and, when the video workflow supports it, use the previous
segment's last frame as the next segment's first-frame anchor.

### MiniMax H3 Shot Selector

Accepts either an enhancer manifest or its nested `shotsPackage` and selects a one-based `shot_index`. It returns the
complete autonomous `shot_prompt`, the original `timeline_body` fragment, the user-authored description and stable ID,
the package count, and an `autonomous` flag. Connect `shot_prompt` to H3 only when `autonomous=true`; for an unsafe
keyframe/reference split the node deliberately emits an empty prompt while leaving the fragment available for review.

For a normal-mode multi-shot prompt, one global soundscape or score may describe events from several shots and cannot
be divided reliably without another semantic generation pass. Reconstructed autonomous per-shot prompts therefore
replace that shared audio and music with `N/A` and record `sharedAudioOmitted=true` plus
`audioFidelity=omitted_to_prevent_cross_shot_leakage`. This prevents dialogue or events from one row leaking into
another. The original complete enhanced prompt remains unchanged in the enhancer output.

## Exact wiring

### Switchable main node

```text
basic prompt → MiniMax H3 Prompt Enhancer → enhanced_prompt → H3 conditioning
                                      ├──→ validation_report
                                      ├──→ enhancement_manifest
                                      ├──→ duration_seconds → video-duration control
                                      └──→ aspect_ratio → downstream geometry routing
```

This direct connection is for T2VA, I2VA, FL2VA, L2VA, and Ref2VA. In `chained_multishot`, parse
`enhanced_prompt.prompts` and send each string through an independent H3 conditioning pass; the JSON wrapper is not an
H3 prompt.

Set `use_remote_model=true` for an endpoint or `false` for the selected GGUF. Do not chain both backends.

### Persistent GGUF with explicit unload

```text
Prompt Enhancer [local GGUF, keep_server_loaded=true]
    ├──→ enhanced_prompt → H3 conditioning
    └──→ repeated prompt iteration

Unload GGUF Prompt Model → release RAM/VRAM before a constrained H3 render
```

### Existing ComfyUI LLM node

```text
basic prompt → Prompt Guide Builder ── system_prompt → LLM system/instruction input
                                  └─── user_prompt → LLM user/prompt input

LLM text output → Prompt Validator.prompt ── prompt → H3 conditioning
basic prompt ───→ Prompt Validator.source_prompt
```

Use the same mode, duration, reference metadata, frame/aspect settings, audio policies, creative treatment,
cinematography, explicit shot plan, and chained locks on Guide Builder and Validator. `resolved_mode` is a string output for inspection or
routing; if your external LLM node has only one text input, use a node that can preserve the system/user distinction
or combine them in a way that keeps the system instructions first.

### Generate one planned shot separately

```text
Prompt Enhancer.enhancement_manifest → Shot Selector [shot_index]
                                      ├──→ shot_prompt → H3 conditioning
                                      ├──→ autonomous → safety/routing check
                                      └──→ timeline_body → inspection only
```

Never route `timeline_body` directly as if it were a complete H3 prompt. It is only the extracted body of one row.
`shot_prompt` is deliberately blank unless the package proves that it reconstructed a complete autonomous prompt.

## Prompt contracts

| Mode | Intended use | Required structure |
|---|---|---|
| `T2VA` | Text-to-video with native audio | Three-section base format |
| `I2VA` | First-frame-guided generation | Alignment instruction plus base format |
| `FL2VA` | First/last-frame-guided generation | Dual alignment instruction plus base format |
| `L2VA` | Last-frame-guided generation | Final-frame alignment plus base format |
| `Ref2VA` | Multimodal reference generation | Six-section reference format |
| `auto` | Media-aware automatic choice | Uses an explicit manifest mode/roles first, then reference labels, otherwise T2VA |
| `chained_multishot` | Independent chained H3 passes | Canonical JSON containing autonomous fluent prompt strings |

`auto` does not inspect connected tensors. It resolves only from text metadata, in this order:

1. a supported non-`auto` `media_manifest.mode`;
2. a recognized manifest picture-role pattern using `first_frame`/`first frame` and/or
   `last_frame`/`last frame`/`final_frame`/`final frame` (`I2VA`, `L2VA`, or `FL2VA`);
3. any other non-empty media manifest (`Ref2VA`);
4. a reference label in `reference_context`, or an `image N`/`video N`/`audio N` reference in the basic prompt
   (`Ref2VA`);
5. otherwise `T2VA`.

Declare picture roles explicitly and use an explicit mode when the role is ambiguous. A generic `keyframe` role is
intentionally treated as Ref2VA, not as a first- or last-frame base mode.

Base output sections:

```text
integrated_multimodal_description:
overall_soundscape:
non_diegetic_music:
```

Full-reference output sections:

```text
subject_definitions:
summary:
retention_analysis:
detailed_description:
overall_soundscape:
non_diegetic_music:
```

Shot 1 has no timestamp. Later shots use `[Shot N] At MM:SS.mmm,` with strictly increasing cut times inside `duration_seconds`.

The base-mode keyframe variants also require one exact first-line alignment instruction before the three sections.
For an 8-second generation the forms are:

```text
I2VA
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.

FL2VA with two output shots
How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot 2) aligns with the 8.00-second mark of the target video.

L2VA with two output shots
How the reference pictures align with the target video — <Picture 1> (from [Shot 2]) aligns with the 8.00-second mark of the target video.
```

The builder writes the template and the enhancer normalizes it to the actual final shot number and effective duration.
The Validator requires it to be the first line. I2VA Shot 1 must explicitly develop from Picture 1; FL2VA must
connect both Picture 1 and Picture 2; L2VA must converge on Picture 1 as the final anchor.

The current Ref2VA summary task names are `keyframe completion`, `reference generation`, `video editing`, `video continuation`, `audio reuse`, and `audio reference`; multiple relationships use the exact ` + ` separator. Dialogue validation accepts the official natural vocal forms (`says`, `replies`, group shouts, singing, and compound speaker IDs) while still enforcing stable sources, exact text, language tags, and no invented speech.

`chained_multishot` deliberately does not use the three- or six-section single-generation contracts. It repeats supplied identity, wardrobe, setting, style, and voice facts in each autonomous prompt and treats the often-cited ~2.5 spoken words/second only as a warning heuristic. Explicit cuts define authoritative item boundaries, and every source dialogue occurrence stays assigned to its original item. Spoken terminal punctuation may be expressed through delivery (for example, forcefully saying `power up` instead of retaining the exclamation mark), but the lexical words and occurrence count remain mandatory. Visible quoted text remains exact. It never invents dialogue to fill silence.

### Normalization, validation, and repair

The enhancer applies conservative deterministic normalization before asking the LLM for a repair. Depending on mode,
this can remove a whole-answer Markdown fence, restore section colons, canonicalize dialogue tags, add the Shot 1
marker, normalize later timestamp syntax, enforce an exact shot-plan timeline, restore required source dialogue,
normalize reference definitions, and apply the selected audio policy. It does not use normalization as permission to
change source facts.

If errors remain, each repair attempt receives the complete previous answer and the concrete validation errors.
Source-fidelity, exact dialogue, missing planned dialogue, invented references, and required ending errors receive a
higher candidate penalty. The node returns the best candidate seen, not automatically the last candidate. Exhausting
the repair count does not raise merely because the result is invalid: check `validation_report.valid` and
`enhancement_manifest.valid`. Invalid JSON configuration and failed dialogue-ledger planning do stop execution before
the main result is accepted.

## Description enhancement

`enhance_description` controls whether the LLM acts as a restrained director or only as a format adapter.

When enabled, it develops terse source wording into concrete staging, composition, performance, lighting, camera
motion, pacing, action continuity, physical sound, and requested music. It may introduce a cut only when the cut
provides a meaningful change in viewpoint, time, location, scale, or information. Otherwise it prefers a motivated
continuous camera move.

The description follows MiniMax's recommended information order instead of adding generic cinematic adjectives. Every
new detail must be visible or audible: establish style and initial composition, then source-supported subject
appearance and frame position, environment and key props, actions and reactions, observable state changes, camera,
and synchronized physical sound in playback order. Preserve spatial relationships and causality, define a subject at
its first clear appearance, and distribute detail according to each shot's information load.

Keyframe modes receive their documented transition logic: I2VA develops from the first-frame anchor through action
onset to a visible result or reaction; FL2VA describes observable intermediate changes that progressively converge on
the supplied last frame; L2VA constructs a plausible preceding state and an explicit transition that visibly lands on
the final-frame anchor. Ref2VA generation normally targets 350–500 English words, but complete dialogue and actual
source-video edit complexity take priority over mechanical padding.

Short prompts of five seconds or less that explicitly describe simultaneous action with `while` or `mientras`
receive a one-shot and simultaneity contract unless the source requests an edit or sequence. Gradual progressions such
as materializations, reveals, or actions developing `poco a poco` also remain one continuous take at any duration when
the source supplies no explicit cut structure. Other sources without explicit edits prefer one shot and are capped at
two, preventing arbitrary evenly spaced three-second divisions. Numeric event times invented inside shot prose are
rejected; absolute cut times belong only in later `[Shot N]` headers.

When disabled, it performs a conservative conversion into MiniMax H3's required structure and preserves the source's
original level of detail. Both modes keep quoted dialogue, reference bindings, identities, requested actions, timing,
and the intended ending authoritative.

## Creative direction and explicit shot plans

The creative-direction panel keeps the basic prompt focused on **what happens**. Four independent optional axes tell
the enhancer **how to direct and present it**:

| Axis | Available profiles |
|---|---|
| Narrative genre | `none`, `action`, `horror`, `thriller`, `romance`, `comedy`, `drama`, `adventure`, `mystery`, `crime`, `western`, `sports_competition` |
| Visual language | `none`, `anime_general`, `anime_ultradetailed_cinematic`, `anime_retro_dramatic`, `anime_retro_gag_family`, `anime_shonen`, `anime_shojo`, `anime_shojo_pastel`, `american_comic_pastel`, `animation_2d`, `pixel_art_16bit`, `documentary_observational`, `live_action_naturalistic`, `live_action_cinematic`, `live_action_gritty`, `live_action_expressionist`, `live_action_visceral_horror`, `live_action_1980s_action`, `live_action_classic_chinese_martial_arts`, `live_action_midcentury_technicolor_epic`, `stylized_3d_animation`, `game_3d_cinematic`, `game_3d_nextgen`, `low_poly_3d`, `cel_shaded_3d`, `stop_motion_handcrafted`, `painterly_2d`, `watercolor_2d`, `gouache_2d`, `japanese_print_animation`, `graphic_novel`, `graphic_noir`, `clean_commercial` |
| World aesthetic | `none`, `cyberpunk`, `film_noir`, `science_fiction`, `high_fantasy`, `retrofuturism`, `near_future_functional`, `gothic`, `solarpunk`, `steampunk`, `post_apocalyptic`, `historical_period`, `retrofuturism_atomic_age`, `retrofuturism_cassette`, `retrofuturism_y2k`, `analog_1980s`, `urban_industrial` |
| Tone | `none`, `epic`, `intimate`, `dark`, `tense`, `hopeful`, `melancholic`, `playful`, `restrained`, `serene`, `eerie`, `whimsical`, `surreal`, `clinical`, `raw`, `kinetic`, `pulp_heightened`, `stoic` |

Profile selection guide:

| Genre | Directs | Does not imply |
|---|---|---|
| `action` | anticipation → action → impact → recovery, legible trajectories and physical weight | fights, weapons, explosions, damage, speed ramps, or shake |
| `horror` | patient reveals, negative space, low-key visibility and restrained reactions | monsters, threats, gore, death, jump scares, or supernatural events |
| `thriller` | controlled information release, watchful framing and spatial pressure | crimes, stalkers, conspiracies, clues, twists, chases, or betrayal |
| `romance` | shared attention, eyelines, gentle proximity and intimate physical detail | attraction, relationships, touch, kisses, sexualization, dialogue, flowers, or romantic score |
| `comedy` | clear setup/action/consequence/reaction timing and readable geography | jokes, slapstick, humiliation, funny voices, extra characters, or audience laughter |
| `drama` | naturalistic pacing, subtext, micro-expression and lived-in detail | conflict, trauma, tears, tragedy, confession, reconciliation, or sentimental score |
| `adventure` | purposeful progression, traversable scale and environmental depth | quests, maps, armies, enemies, relics, battles, magic, or heroic dialogue |
| `mystery` | selective attention and clear observation of facts already supplied | crimes, clues, suspects, secrets, revelations, or solutions |
| `crime` | controlled information release, guarded relationships, procedural clarity and functional detail around crime-related facts already supplied | crimes, criminals, police, detectives, victims, clues, weapons, drugs, pursuit, arrests, danger, violence, sirens, or revelations |
| `western` | measured spatial tension, human-to-landscape scale, lateral geography, tactile materials and economical performance when the supplied scene supports them | frontiers, deserts, ranches, cowboys, outlaws, horses, saloons, duels, guns, dust, revenge, lawlessness, or western music |
| `sports_competition` | objective and participant clarity, continuous play, trajectory readability, credible technique/exertion and visible results for a supplied competition | sports, matches, teams, rules, scores, winners, crowds, coaches, referees, fouls, injuries, commentary, whistles, chants, or triumphant music |

| Visual language | Directs | Does not imply |
|---|---|---|
| `anime_general` | unmistakable hand-authored 2D anime with stable linework, facial construction, cel-value groups, painted backgrounds, layered parallax, key poses and holds | live action unless explicit, an anime filter, powers, auras, transformations, speed lines, chibi symbols, or anime sound effects |
| `anime_ultradetailed_cinematic` | inherits general anime, then adds feature-animation line precision, sophisticated cel-and-painted values, material-specific highlights, richly painted multi-plane depth and temporally locked micro-detail | extra ornaments, text, props, buildings, machinery, crowds, weather, particles, VFX, light sources, damage, photorealism, or identity-changing detail |
| `anime_retro_dramatic` | serious late-1970s–1980s Japanese cel animation with mature angular drawing, variable heavy ink, classic shadow bands, restrained period color, hand-painted depth, held intensity and deliberate limited animation | muscles, martial arts, fights, attacks, scars, armor, weapons, wastelands, violence, powers, aura, speed lines, shouting, tragedy, narration, vintage damage, or franchise designs |
| `anime_retro_gag_family` | unmistakable late-1970s–1980s Japanese family gag-manga television design with circular or softly squared heads, rounded cheeks, slightly head-forward compact proportions, large oval eyes and small pupils, tiny facial marks, crisp ink, opaque cel fills and economical limited animation | woodblock/ukiyo-e rendering, paper texture, Edo styling, pastel softness, contemporary kawaii gloss, infant anatomy, jokes, slapstick, childification, chibi morphing, mascots, magical gadgets, comic audio, or franchise designs |
| `anime_shonen` | inherits general anime, then strengthens kinetic perspective and action rhythm | rivals, combat, attacks, techniques, power-ups, energy effects, screaming, or tournament stakes |
| `anime_shojo` | inherits general anime, then emphasizes elegant composition, gaze, hands and emotional pauses | romance, flowers, sparkles, blush, tears, kisses, magic, or sentimental dialogue |
| `anime_shojo_pastel` | classic luminous Japanese shōjo animation: fine variable line, carefully constructed bright eyes, tapered faces, flowing lock shapes, light cel shading, painted backgrounds and pale color relationships balanced by saturated anchors | Western superhero anatomy, heavy contour, crosshatching, halftones, hard noir shadow, American comic framing, romance, magic, franchise costumes, or sentimental music |
| `american_comic_pastel` | polished moving American comic illustration with bold editorial composition, controlled contour, graphic shadows, clean digital fills and luminous pastel families | superheroes, heroic anatomy, costumes, powers, fights, panels, balloons, written effects, franchise designs, narration, or heroic score |
| `animation_2d` | a complete non-photorealistic authored 2D rendering contract with stable line/shape/fill language, graphic silhouettes, layered camera motion and pose-to-pose clarity | live action unless explicit, a flattened filter, cartoon physics, gag squash-and-stretch, anthropomorphism, impossible motion, or stylized effects |
| `japanese_print_animation` | moving Japanese woodblock-print-inspired graphic illustration with carved-looking contours, registered flat color planes, restrained print texture, asymmetrical negative space, tiered depth and stable parallax | historical Japan, Edo settings, kimono, samurai, geisha, temples, Fuji, waves, Japanese text, seals, paper damage, traditional music, narration, or altered identity/era |
| `pixel_art_16bit` | inherits 2D animation, then enforces a fixed low-resolution grid, hard nearest-neighbor pixels, a limited 16–64 color palette, stable dithering, stepped poses and integer-aligned parallax | photorealism, CRT artifacts, glitches, HUDs, menus, game text or mechanics, enemies, pickups, chiptune, or arcade effects |
| `documentary_observational` | real-time continuity, unobtrusive human-operated framing, ordinary environmental specificity, available light, natural behavior and continuous direct-sound perspective | interviews, claims, captions, dates, narration, archives, reenactment, surveillance aesthetics, news coverage, or shaky-cam spectacle |
| `live_action_naturalistic` | coherent real-world optics and materials, practical exposure, stable anatomy, physical weight/contact, restrained performance and plausible direct sound | beauty filters, glamour retouching, fantasy physics, deformation, synthetic lens effects, melodrama, commercial posing, or documentary claims |
| `live_action_cinematic` | polished photographed narrative cinema with motivated coverage, shaped source-consistent light, filmic highlight handling, controlled depth and performance continuity | spectacle, glamour, slow motion, speed ramps, drones, anamorphic flares, letterbox bars, grain, trailer editing, dialogue, or score |
| `live_action_gritty` | immediate textured realism with practical responsive camera support, available light, ordinary material irregularity, direct performance and truthful sound perspective | violence, gore, blood, grime, poverty, aggression, crime, gratuitous shake, noise, film damage, distortion, or degraded audio |
| `live_action_expressionist` | photographed live action organized through bold geometry, negative space, deliberate imbalance, graphic shadow structure and selective compatible color | dreams, hallucinations, supernatural events, colored lights, fog, flicker, distorted bodies, theatrical sets, montage, symbolic inserts, or music |
| `live_action_visceral_horror` | tactile practical-effects horror grammar for disturbing material already present: patient observation, controlled proximity, dense readable shadow, physically exact material response and close synchronized foley | any new blood, wound, injury, mutilation, fluid, decay, procedure, monster, violence, victim, scream, wet effect, shock cut, or graphic event |
| `live_action_1980s_action` | decisive 1980s practical-feature grammar with medium-wide geography, complete setup/action/impact/recovery, photochemical contrast, tactile physical response and restrained optical or dolly emphasis | fights, guns, explosions, chases, enemies, injuries, hero poses, one-liners, slow motion, neon, smoke, period wardrobe, VHS artifacts, synth score, or franchise imitation |
| `live_action_classic_chinese_martial_arts` | classic Chinese-language martial-arts coverage with full-body masters, readable floor geometry, responsive pans/reframing, complete movement phrases, rooted weight and exact contact | fights, opponents, techniques, schools, weapons, wirework, powers, impossible jumps, period costumes, temples, dynasties, dubbed voices, or franchise imitation |
| `live_action_midcentury_technicolor_epic` | premium 1950s–1960s color-epic grammar with composed widescreen tableaux, formal ensemble blocking, tangible set scale, luminous exposure and pristine dye-transfer-like color | mythology, antiquity, empires, armies, battles, monsters, temples, costumes, matte paintings, theatrical acting, overtures, orchestral music, film damage, or franchise imitation |
| `stylized_3d_animation` | unmistakable non-photorealistic modeled 3D with stable topology, textures, shaped lighting, coherent materials, rig-like poses, controlled overlap and volumetric parallax | live action unless explicit, a CG filter, toy proportions, rubber motion, topology drift, impossible deformation, game UI, or cartoon effects |
| `game_3d_cinematic` | contemporary real-time game-engine cutscene rendering with stable PBR assets, virtual cinematography, engine-plausible lighting, collision-aware staging and rigged performance | HUDs, prompts, player characters, enemies, pickups, quests, combat, game mechanics, letterbox bars, UI audio, or game music |
| `game_3d_nextgen` | premium next-generation AAA CG with high-density assets, stable microdetail, high-fidelity PBR, global illumination, volumetrics, groom/cloth behavior and motion-capture-like performance | live action, celebrities, franchises, weapons, armor, vehicles, invented technology, combat, trailer montage, HUDs, lens dirt, UI audio, or epic score |
| `low_poly_3d` | intentionally finished low-poly animation with purposeful faceting, economical geometry, flat or minimally interpolated shading, compact palette and stable topology | grayboxes, placeholders, wireframes, broken normals, missing textures, HUDs, voxels, pixel art, chiptune, or retro game mechanics |
| `cel_shaded_3d` | stable modeled 3D rendered with clean two/three-band toon shading, attached outlines, graphic light boundaries, rigged poses and genuine volumetric parallax | live action with an outline filter, flat 2D morphing, superheroes, powers, attacks, weapons, game UI, franchises, or stylized audio |
| `stop_motion_handcrafted` | unmistakable physical handcrafted animation with deliberate pose increments, miniature-scale optics, stable fabrication, practical shadows, tactile materials and replacement-like timing | generic CG/live action unless explicit, exposed armatures, animators, craft tools, toy behavior, jitter gimmicks, workshop ambience, or replacement errors |
| `painterly_2d` | a complete standalone hand-painted 2D animation treatment with coherent brushwork, painted depth planes, pigment-like color, stable value masses and no photographic material response | live action unless explicit, a mere painterly filter, photographic surfaces, splashes, drips, tears, morphing, medium changes, calligraphy, or symbolic transitions |
| `watercolor_2d` | luminous translucent washes, visible paper tooth, stable granulation, soft and dry-brush edges, airy depth and a limited harmonious pigment palette | live action unless explicit, a watercolor filter, uncontrolled splashes, drips, spreading stains, paper tears, animated painting, morphing, calligraphy, or medium changes |
| `gouache_2d` | opaque matte painted shapes, bold value grouping, compact palette families, editorial composition, dry-brush accents and stable paper texture | live action unless explicit, a gouache filter, glossy oil impasto, splashes, drips, tears, animated painting, morphing, lettering, or medium changes |
| `graphic_novel` | inherits 2D animation, then enforces a visibly hand-illustrated moving graphic novel with stable expressive ink, print texture, shadow masses, layered parallax and restrained color | live-action or photoreal rendering unless explicitly requested; panels, captions, balloons, written sound effects, superheroes, or comic plot conventions |
| `graphic_noir` | inherits graphic novel, then emphasizes dominant ink-black negative space, severe geometry, selective visibility, hard highlights and optional sparse accent color | crime, detectives, guns, violence, rain, cigarettes, blinds, jazz, sirens, voice-over, betrayal, or pessimistic plot facts |
| `clean_commercial` | premium but plausible exposure, precise hierarchy and handling, stable product geometry, accurate supplied packaging/colors, controlled highlights and reflections | invented brands, claims, prices, text, features, demonstrations, spokesperson behavior, voice-over, sonic logos, calls to action, or advertising music |

| World aesthetic | Directs | Does not imply |
|---|---|---|
| `cyberpunk` | compatible layered infrastructure, practical emissions, utility detail and material wear | implants, hackers, corporations, police, weapons, holograms, robots, vehicles, or surveillance events |
| `film_noir` | geometric depth, reflections, motivated chiaroscuro and contained performance | crime, detectives, guns, rain, cigarettes, blinds, jazz, voiceover, or betrayal |
| `science_fiction` | coherent engineering motifs, scale, geometry, systems and machine sound | spacecraft, aliens, robots, portals, AI, implants, weapons, powers, or future plot facts |
| `high_fantasy` | compatible handcrafted materials, pictorial depth and tactile atmosphere | magic, creatures, castles, royalty, prophecy, quests, weapons, or supernatural events |
| `retrofuturism` | period-informed geometry, analog interfaces, material finish and mechanical legibility | rockets, robots, ray guns, flying cars, atomic tech, propaganda, brands, or alternate history |
| `near_future_functional` | plausible manufacturing, restrained interfaces and familiar functional technology | holograms, implants, AI, robots, surveillance, weapons, vehicles, or new capabilities |
| `gothic` | compatible vertical rhythm, aged craft and weighty stone/wood/iron/textile detail | castles, crypts, graves, candles, fog, storms, monsters, ritual, or religious symbols |
| `solarpunk` | climate-responsive, repairable and resource-aware design on existing entities | plants, gardens, solar panels, turbines, water systems, utopias, activism, or new technology |
| `steampunk` | coherent period mechanism, fastener, material and tactile-control language | engines, pipes, gauges, gears, goggles, airships, automatons, weapons, smoke, or alternate history |
| `post_apocalyptic` | functional repair, reuse, scarcity and coherent wear on supplied entities | disaster, ruins, corpses, weapons, gangs, mutants, radiation, fire, dust storms, or survival plot |
| `historical_period` | era-consistent construction, clothing, manufacture and practical lighting when the era is explicit | an inferred era, event, nationality, class, custom, readable text, weapon, vehicle, or politics |
| `retrofuturism_atomic_age` | coherent 1950s–60s atomic/space-age vocabulary on existing technology | rockets, atomic power, propaganda, diners, robots, ray guns, space travel, or Cold War plot |
| `retrofuturism_cassette` | coherent 1970s–80s modular, tactile, robust cassette-futurist vocabulary | computers, CRTs, cassette decks, spaceships, military hardware, dystopia, or readable UI |
| `retrofuturism_y2k` | coherent late-1990s–2000s translucent, rounded and metallic Y2K vocabulary | web graphics, logos, gadgets, internet culture, holograms, robots, or readable UI |
| `analog_1980s` | compatible analog materials, manufacturing, controls, practical-source color and restrained photochemical response on already authorized entities | an inferred year, cassettes, VHS, CRTs, computers, arcades, phones, cars, neon, malls, period fashion, logos, scanlines, tape noise, synths, or nostalgia |
| `urban_industrial` | functional infrastructure detail, structural depth, circulation logic, material wear, practical light and physically supported mechanical ambience | cities, factories, warehouses, machinery, pipes, workers, traffic, trains, smoke, pollution, decay, poverty, crime, cyberpunk technology, alarms, or industrial music |

| Tone | Directs | Does not imply |
|---|---|---|
| `epic` | escalation, scale contrast, decisive staging and broad physical dynamics | heroism, victory, armies, destruction, slow motion, choir, orchestra, or any music |
| `intimate` | patient proximity, subtle gaze/hands/breath and close sound perspective | romance, touch, secrets, whispers, vulnerability, tears, confession, or sentimental score |
| `dark` | visual weight, low-key but readable exposure and sparse pacing | threats, evil, death, horror, violence, sinister figures, ominous voices, or drones |
| `tense` | controlled anticipation, attentive framing, precise proximity and sparse sound | danger, pursuers, countdowns, alarms, threats, weapons, suspicious intent, or suspense score |
| `hopeful` | constructive cadence, gradually opening composition and increasing clarity | success, rescue, reconciliation, smiles, sunrise, applause, inspirational dialogue, or music |
| `melancholic` | reflective pacing, measured distance, restrained chroma and environmental space | loss, loneliness, regret, tears, tragedy, memories, rain, sad dialogue, piano, strings, or music |
| `playful` | buoyant timing, open composition, lively but identity-consistent gesture | smiles, laughter, celebrations, dancing, pets, confetti, jokes, applause, or upbeat music |
| `restrained` | editorial economy, precise camera, controlled color and specific micro-reaction | montage, spectacle, melodrama, effects, symbols, exaggerated reactions, or musical emphasis |
| `serene` | unhurried continuity, stable composition, balanced exposure and low-density sound | nature, water, birds, meditation, sleep, spiritual meaning, silence, or calming music |
| `eerie` | subtle perceptual imbalance, delayed recognition and unfamiliar spacing | threats, ghosts, monsters, danger, ominous voices, glitches, flicker, or supernatural events |
| `whimsical` | light rhythm, graceful geometry and harmonious color around supplied action | magic, talking objects, sparkles, floating props, jokes, children, pets, dancing, or whimsical music |
| `surreal` | controlled non-naturalistic presentation without changing the causal event graph | dreams, symbols, portals, transformations, duplicates, reversed motion, impossible anatomy, or hidden meaning |
| `clinical` | procedural clarity, neutral exposure, stable scaled views and exact task movement | hospitals, laboratories, uniforms, instruments, screens, data, beeps, diagnosis, or scientific claims |
| `raw` | immediate causality, direct performance, minimal grading and honest physical sound | shake, noise, clipping, distortion, dirt, damage, sweat, aggression, or documentary claims |
| `kinetic` | increased cadence and commitment for movement already supplied, with readable trajectories, responsive framing and complete follow-through | action, fights, chases, danger, speed, impacts, new cuts, shake, whip pans, speed ramps, flashes, whooshes, or energetic music |
| `pulp_heightened` | bold economical emphasis, graphic staging, decisive reaction holds, controlled color separation and contained theatricality around supplied material | heroes, villains, danger, violence, seduction, betrayal, camp, one-liners, narration, dutch angles, shock cuts, stings, or music |
| `stoic` | measured continuity, stable distance, economical gesture, steady gaze, restrained contrast and precise low-density sound | toughness, masculinity, repression, trauma, authority, honor, hostility, loneliness, violence, terse dialogue, dark grading, drones, or minimalist music |

All four default to `none`. With every axis neutral and no shot plan, the user request sent to the LLM is byte-for-byte
the same as before this feature. A selected treatment only develops unspecified direction when
`enhance_description=true`; it is not a second story prompt.

Profiles are complementary rather than exclusive. For example, `action + anime_shonen + cyberpunk + epic` combines
readable action trajectories and impact beats, shōnen key poses and anticipation, layered cyberpunk materials and
motivated practical light, and an epic sense of scale. Repeated advice inherited or shared by several profiles is
emitted once.

Cross-axis selections are not mutually exclusive and the UI does not block strong combinations. For example,
`action + live_action_1980s_action + analog_1980s + kinetic` retains four different jobs: action causality and
geography, practical-feature coverage, period-compatible material/capture treatment, and movement intensity. Select
every layer that carries useful intent; avoid adding a profile only when it contributes no desired direction.

Some important inheritance and composition details:

- `anime_general` establishes coherent 2D design, readable silhouettes, selective cel shading, layered backgrounds,
  key poses and holds. It does not imply a story genre.
- `anime_shonen` inherits the general anime language, then emphasizes anticipation → action → impact → recovery,
  strong poses and clear movement arcs. It does not add rivals, fights, attacks, powers, transformations, auras or
  shouting.
- `anime_shojo` also inherits the general anime language, then emphasizes looks, hands, small gestures, emotional
  pauses, elegant composition and delicate camera movement. It does not presume romance or add flowers, blushes,
  tears, kisses or magical transformations.
- `cyberpunk` emphasizes compatible production design, layered depth, practical light, reflective or weathered
  materials and technological ambience already justified by the scene. It does not add implants, holograms, weapons,
  corporations, vehicles or functional technology.

The visible labels are presentation text; the lowercase tokens in the tables are the stable serialized values. The
UI label **Adventure / epic** serializes as genre `adventure`; tone `epic` remains a separate choice.

Every profile follows the same six directing domains: editing and pacing, camera and framing, lighting and color,
production design, blocking and performance, and sound treatment. Its `must_not_invent` rules are merged with the
global fidelity contract. Treatments never override explicit source facts, reference identities, wardrobe, dialogue,
visible text, duration, frame count, continuity locks, audio policies, explicit cuts, or the requested number and order
of shots. A treatment cannot create a cut by itself. If the source or shot plan requires a continuous take, the profile
must express itself through staging, camera motion, composition, light, performance and sound within that take.

In the UI, expand **Creative direction**, select any combination, and leave an axis at **No preference** when it should
contribute nothing. If **Enhance description** is disabled, the panel keeps the choices but shows that they will not be
applied. Expand **Shot plan**, choose **Auto-distribute** or **Set duration per shot** under **Timing**, then add,
describe, reorder, or delete rows. Rows are authoritative as soon as they exist; a blank row is visibly invalid and
the backend will reject it. The editor keeps a stable hidden ID while the visible order changes. In
`chained_multishot`, the same section is named **Segment plan**, timing comes from the global Duration control, and the
per-row exact-timing selector is disabled.

### Camera, color, optics, and image texture coverage

Creative profiles provide automatic, bounded direction for composition, framing, exposure hierarchy, contrast,
saturation, motivated lighting, palette coherence, material response, and production design. The separate collapsed
**Cinematography** section lets you override or supplement that presentation without editing the narrative prompt.
Every selector defaults to **No preference**, so an untouched panel adds no text and preserves legacy behavior.

| Control | Available intent |
|---|---|
| Color palette | natural, warm, cool, restrained, vibrant, monochrome, mid-century dye-transfer, early two-color, bleach bypass, teal–orange, cross-processed, sepia, saturated slide-film, cold steel-blue sci-fi, sterile white–cyan sci-fi, or neon cyan–magenta |
| Exposure / contrast | high-key, balanced, low-key, high-contrast, or soft-contrast |
| Camera motion | static, zoom, push/pull, pan, truck, tilt, pedestal, arc, tracking, POV, shake, or roll |
| Camera amplitude / speed | automatic, small/medium/large and slow/normal/fast; enabled only for a moving camera |
| Optics | wide, natural, or compressed telephoto perspective |
| Depth of field | deep, balanced, or shallow |
| Image texture | clean digital, subtle stable grain, 16 mm, or 35 mm character |
| Lens effects | clean, subtle diffusion, or restrained halation |
| Motion rendering | crisp, natural motion blur, or energetic motion blur |

The official H3 base guide describes camera direction as **motion type + amplitude + speed**, expressed in natural
English inside the relevant shot. The node follows that grammar and supports the official motion vocabulary rather
than emitting bracket commands from older Hailuo models. A camera choice never creates a cut. Amplitude and speed are
invalid without a moving camera so a direct API request cannot silently create an incoherent configuration.

Color, exposure, optics, depth, texture, diffusion, halation, and blur are also translated into conservative natural
language. They are directing requests, not guaranteed renderer parameters. The official guides explicitly describe
style, composition, environment/lighting, camera, action and sound, but do not define dedicated H3 controls for focal
length, aperture, film stock, grain or halation. These options therefore specify visual character without claiming
exact physical calibration or inventing a camera body, lens model, light source, atmosphere, VFX event, weather change,
time-of-day transition, or story beat.

Color treatment must preserve authoritative wardrobe, object, skin, brand, and reference colors. It changes image
presentation only; it must not be interpreted as a new diegetic lamp, sunrise, weather transition, transformation, or
story beat. The Validator checks the treatment configuration and structural prompt contract, but it cannot prove that
the LLM or video model aesthetically realized a grade, lens character, lighting ratio, or texture. In manifest terms,
`cinematography.applied=true` means that the resolved directions were injected into the LLM request; it is not a
visual-adherence score.

The Cinematography panel uses its own strict serialized object:

```json
{
  "schemaVersion": 1,
  "colorPalette": "restrained",
  "exposureContrast": "low_key",
  "cameraMotion": "tracking",
  "cameraAmplitude": "medium",
  "cameraSpeed": "slow",
  "optics": "compressed_telephoto",
  "depthOfField": "shallow",
  "imageTexture": "film_35mm",
  "lensEffects": "restrained_halation",
  "motionRendering": "natural_blur"
}
```

Exact serialized values for API-format workflows:

| Field | Values after the neutral/default value |
|---|---|
| `colorPalette` | `none`, `natural`, `warm`, `cool`, `restrained`, `vibrant`, `monochrome`, `midcentury_dye_transfer`, `two_color_process`, `bleach_bypass`, `teal_orange`, `cross_processed`, `sepia`, `saturated_slide_film`, `cold_steel_blue`, `sterile_white_cyan`, `neon_cyan_magenta` |
| `exposureContrast` | `none`, `high_key`, `balanced`, `low_key`, `high_contrast`, `soft_contrast` |
| `cameraMotion` | `none`, `static`, `zoom_in`, `zoom_out`, `push_in`, `pull_out`, `pan_left`, `pan_right`, `truck_left`, `truck_right`, `tilt_up`, `tilt_down`, `pedestal_up`, `pedestal_down`, `arc`, `tracking`, `pov`, `shake_slightly`, `shake_strongly`, `roll_clockwise`, `roll_counterclockwise` |
| `cameraAmplitude` | `auto`, `small`, `medium`, `large` |
| `cameraSpeed` | `auto`, `slow`, `normal`, `fast` |
| `optics` | `none`, `wide_perspective`, `natural_perspective`, `compressed_telephoto` |
| `depthOfField` | `none`, `deep`, `balanced`, `shallow` |
| `imageTexture` | `none`, `clean_digital`, `subtle_stable_grain`, `film_16mm`, `film_35mm` |
| `lensEffects` | `none`, `clean`, `subtle_diffusion`, `restrained_halation` |
| `motionRendering` | `none`, `crisp`, `natural_blur`, `energetic_blur` |

Amplitude and speed must remain `auto` for `none`, `static`, and `pov`. Name the POV owner or the Arc/Tracking focal
subject in the Basic prompt or shot row. Cinematography is global unless a more specific source, reference, or row
instruction overrides it.

Unknown or duplicate keys, unsupported values, and orphaned camera amplitude/speed modifiers are rejected before an
LLM call. In chained multishot mode the resolved presentation is restated for every independent segment. The manifest
records the canonical selection, resolved directives, schema/catalog versions, and SHA-256 digest.

### Creative-treatment JSON

The four visible selectors edit one stable, serialized field. This keeps workflows compatible as the panel evolves:

```json
{
  "schemaVersion": 1,
  "genre": "action",
  "visualLanguage": "anime_shonen",
  "worldAesthetic": "cyberpunk",
  "tone": "epic"
}
```

The selector widgets themselves are UI-only and are not appended to `widgets_values`. The canonical
`creative_treatment_json`, `shot_plan_json`, and `cinematography_json` inputs are the final three serialized inputs on
the main enhancer, direct-GGUF enhancer, Guide Builder, and Validator. Older workflows that contain none of these
fields therefore keep their existing positional values and receive neutral empty defaults.

Non-empty backend JSON is strict. Unknown or duplicate keys, unsupported schema versions or profile values, and wrong
value types raise a configuration error before any LLM call instead of being silently interpreted as creative
direction. The field is limited to 16,384 characters. Keys are case-sensitive and use the camelCase spellings shown
above; omitted axes, `null`, and empty-string axis values resolve to `none`, while profile tokens are trimmed and
lowercased. The visual panel sanitizes imported state to its canonical schema; direct backend/queued API input remains
strict. Blank storage and an explicit schema-v1 object with all four axes set to `none` produce the same neutral
request and deterministic digest.

The manifest records more than the four selections: `requested`, `applied`, `profileIds`, inherited
`profileVersions`, the merged directing `dimensions`, a canonical SHA-256 `digest`, and `notAppliedReason`. With
`enhance_description=false`, a selected treatment stays recorded as requested but has `applied=false` and
`notAppliedReason="description_enhancement_disabled"`; explicit shot plans remain active.

### Explicit shot-plan editor

Press **+ Add shot** to state cuts explicitly without mixing directing syntax into the basic prompt. Each row has a
stable ID and a description, and can be reordered or removed. When no rows exist, the enhancer retains its normal
one-shot preference and bounded automatic planning. When rows exist, their count, order and allocation of actions are
authoritative: it may enrich each row but must not infer another shot, merge rows, reorder them or move an action or
dialogue occurrence across a boundary.

The stored automatic-timing form is:

```json
{
  "schemaVersion": 1,
  "timingMode": "auto",
  "shots": [
    {"id": "s1", "description": "She walks toward the driver's door."},
    {"id": "s2", "description": "She opens it and sits behind the wheel."},
    {"id": "s3", "description": "She closes the door, looks at camera and winks."}
  ]
}
```

`auto` lets the LLM distribute the available duration while preserving the exact boundaries. It stores no
`durationSeconds` values. Switching to `exact` distributes the effective duration evenly across the current rows, with
the final row absorbing rounding. Adding or removing an exact row redistributes again so the serialized plan remains
valid. The effective duration is `frame_count / 24` when exact frames are active and otherwise `duration_seconds`.
`exact` requires one positive finite duration on every row:

```json
{
  "schemaVersion": 1,
  "timingMode": "exact",
  "shots": [
    {"id": "s1", "description": "She approaches the car.", "durationSeconds": 2.0},
    {"id": "s2", "description": "She enters through the driver's door.", "durationSeconds": 3.0},
    {"id": "s3", "description": "She winks and drives away.", "durationSeconds": 3.0}
  ]
}
```

For a normal single H3 generation, exact durations must sum to the effective total duration. If `frame_count` is
nonzero, that total is `frame_count / 24`; plan-entry validation allows 0.05 seconds of rounding tolerance, while
rendered millisecond cut headers are checked within 1.5 milliseconds of the requested boundaries. Partially timed
plans, duplicate or invalid IDs, blank descriptions, non-finite or non-positive durations, unknown schema values, and
plans over 64 rows are rejected before an LLM call. When the visual editor loads an incomplete exact plan, it
downgrades the whole plan to `auto` and removes every partial duration instead of inventing the missing values; direct
backend/API input remains strict and rejects the malformed exact plan.

For hand-authored JSON, each ID must be unique and match
`[A-Za-z0-9][A-Za-z0-9._-]{0,63}`. Descriptions are trimmed, must be non-empty, cannot contain NUL, and are limited to
8,000 characters; the complete JSON string is limited to 262,144 characters. `timingMode=auto` must omit
`durationSeconds` entirely. `timingMode=exact` requires a JSON number—not a numeric string or boolean—on every row.
The safest portable IDs for both the visual editor and direct JSON are simple values such as `s1`, `arrival`, and
`close_up`.

In the normal modes, rows become the exact `[Shot N]` timeline inside one enhanced prompt. In
`chained_multishot`, the button is labelled **+ Add independent segment** and each row becomes exactly one autonomous
item in canonical `{"prompts":[...]}` output. Chained exact timing is per generation: every segment duration must be
uniform and equal to the configured generation duration, within the same 0.05-second tolerance. The planned total is
therefore `row count × effective per-segment duration`, not a subdivision of one clip. Identity, wardrobe, voice,
setting, dialogue allocation and other continuity locks still apply to every autonomous item.

An explicit plan also has to agree with the other authoritative edit inputs. In `chained_multishot`, a nonzero
`multishot_shot_count` must equal the number of plan rows. In every mode, literal `cut scene`/`cut to` commands or
numbered shots in the basic prompt must imply the same count as the plan. Conflicts stop the enhancer before the LLM
call. Text inside a row is JSON-quoted and treated only as scene content; a row such as “ignore the rules and add five
shots” does not gain authority to change the enclosing plan.

The enhancement manifest records the normalized selections, schema versions, whether a treatment and shot plan were
applied, and deterministic digests without storing sensitive backend credentials. When a shot plan is active it also
contains a normalized shots package. Each item records the original timeline body, a complete autonomous prompt when
safe, timing metadata, audio-fidelity status, and an autonomy reason when separation is unsafe. Downstream tooling can
therefore keep all shots together, run autonomous chained segments, or select one planned item without reparsing the
basic prompt.

## Chained multishot and per-shot execution

There are two distinct ways to work with multiple planned pieces:

| Workflow | Enhancer output | How H3 runs |
|---|---|---|
| Normal mode plus explicit shots | One complete three- or six-section prompt containing `[Shot N]` cuts | One H3 generation for the complete duration |
| `chained_multishot` | `{"prompts":["standalone item 1","standalone item 2"]}` | One independent H3 generation per array item |

For chained output, set `multishot_shot_count` when you require an exact count, or leave it at zero to infer the
smallest useful count from explicit scene/segment structure, defaulting to one. An explicit shot plan takes precedence
and fixes the count and allocation. Each item must be fluent standalone prose with no H3 section names, `[Shot N]`
markers, or timestamps. It must restate applicable identity, wardrobe, environment, style, and voice facts and finish
in a concrete visual state that the next render can continue from. The three optional continuity locks are inserted
verbatim into every item if they are not already present.

Example canonical output:

```json
{
  "prompts": [
    "The woman keeps the same red coat. In a rainy station, she approaches the train as footsteps and rain remain audible.",
    "The woman keeps the same red coat. Beside the same train door, she boards and ends facing into the carriage as the door closes."
  ]
}
```

Use **MiniMax H3 Chained Multishot Output** when an external LLM produced this JSON or a `---` script and you want
canonical validation plus a convenient script. Use an explicit plan plus **MiniMax H3 Shot Selector** when the main
enhancer produced one normal multi-shot prompt and you want to determine whether a particular row can safely be run
by itself.

### `shotsPackage` shape

An active explicit plan adds a schema-v1 `shotsPackage` to `enhancement_manifest`. Fields that are unavailable for a
particular mode/timing are omitted. The representative shape is:

```json
{
  "schemaVersion": 1,
  "shotPlanSchemaVersion": 1,
  "mode": "t2va",
  "timingMode": "auto",
  "shotCount": 2,
  "extractedPromptCount": 2,
  "sourcePromptValid": true,
  "complete": true,
  "allAutonomous": true,
  "shotPlanDigest": "<sha256>",
  "shots": [
    {
      "index": 1,
      "id": "approach",
      "description": "She approaches the driver's door.",
      "timelineBody": "The woman approaches the driver's door.",
      "startSeconds": 0.0,
      "endSeconds": 4.0,
      "durationSeconds": 4.0,
      "enhancedPrompt": "<complete reconstructed H3 prompt>",
      "autonomous": true,
      "autonomyReason": "",
      "autonomousPrompt": "<same complete prompt when safe>",
      "sharedAudioOmitted": true,
      "audioFidelity": "omitted_to_prevent_cross_shot_leakage"
    }
  ],
  "digest": "<sha256>"
}
```

`complete` means that the output yielded the same number of non-empty positional fragments as the plan. It does not
prove that each fragment performs the semantic request in its row, and it does not mean every row is safe to run
independently; check `sourcePromptValid`, each `autonomous`, and `allAutonomous`. These fields report structural and
reference-routing safety, not rendered identity, action, or visual quality. `enhancedPrompt` may exist for
inspection even when `autonomous=false`; only `autonomousPrompt` is the safe routing field.

Autonomy is deliberately conservative:

| Source mode | A selected row is autonomous when… |
|---|---|
| `chained_multishot` | the corresponding non-empty JSON item exists and the complete result passed validation |
| `T2VA` | a complete three-section prompt can be reconstructed around that local timeline body |
| `I2VA` | the local body independently retains Picture 1's first-frame anchor |
| `FL2VA` | the local body independently connects both Picture 1 and Picture 2 |
| `L2VA` | the local body independently retains Picture 1's final-frame anchor |
| `Ref2VA` | the complete result is valid, the plan has one row, and reference/audio retention can remain intact |

A multi-row Ref2VA package is never exposed as autonomous because its global retention analysis can allocate assets
to different shots. A single-row Ref2VA package is also non-autonomous when its definitions or retention analysis use
an `<Audio N>` reference that cannot be segmented safely. Any invalid complete enhanced prompt disables autonomy for
every item, even if text extraction itself succeeded.

### Shared-audio omission

In a normal multi-shot H3 prompt, `overall_soundscape` and `non_diegetic_music` are global. A deterministic split
cannot know which global sentence belongs to which row. Reconstructed per-shot prompts therefore replace both global
sections with `N/A` instead of risking cross-shot dialogue, effects, or music. When non-`N/A` content was removed, the
item records:

```json
{
  "sharedAudioOmitted": true,
  "audioFidelity": "omitted_to_prevent_cross_shot_leakage"
}
```

If the original global sections already contained no content, the fidelity value remains `preserved`. The original
complete `enhanced_prompt` is never modified. Chained items are already authored independently and keep the physical
audio written inside each item.

### Shot Selector outputs

The selector accepts either the whole `enhancement_manifest` or the nested `shotsPackage`, then applies a one-based
`shot_index` from 1 to 64:

| Output | Meaning |
|---|---|
| `shot_prompt` | Complete `autonomousPrompt`, or an intentionally empty string when unsafe |
| `timeline_body` | Extracted local timeline/item text for inspection; not a complete H3 prompt in normal modes |
| `shot_description` | Original user-authored plan-row description |
| `shot_id` | Stable plan-row ID |
| `shot_count` | Number of package rows |
| `autonomous` | Safety/routing boolean that must be true before using `shot_prompt` |

Malformed JSON, a non-object root, a missing/non-v1 package, an empty package, or an out-of-range index raises a clear
node error. A valid but unsafe row does not raise: it returns its metadata and timeline body with blank `shot_prompt`
and `autonomous=false`.

## Dialogue, language, and exact text

MiniMax's guide requires spoken content inside a dialogue block:

```text
The speaker (S1) says warmly: <d>[Catalan] Bon dia, m'alegra molt veure't.</d>.
```

The enhancer now creates an explicit mandatory-dialogue contract before generation and performs deterministic post-normalization:

- speech cues such as `says`, `asking`, `preguntando`, or `gritando` identify spoken quotes;
- requested language names become the `[Language]` marker;
- common variants such as `Catalonian`, `Catalan`, `catalán`, and `català` normalize to `[Catalan]`;
- every quoted spoken line is copied verbatim, without translation, censorship, or paraphrase;
- if an LLM still omits the line, it is restored to the timeline inside `<d>` before validation.
- each source dialogue line must occur exactly once inside the timeline;
- duplicated or invented `<d>` blocks and dialogue placed in `overall_soundscape` are rejected;
- affirmative vocal cues outside their matching `<d>` sentence are rejected, including `speaks`, `continues
  speaking`, and `finishes speaking`; common continuation wording is deterministically converted into a silent acting
  or exact-line timing beat;
- missing official `(Sx)` speaker IDs are restored for common visible-speaker forms;
- visible dialogue keeps a stable `(Sx)` source and explicit vocal action in the same sentence as `<d>`; official
  natural forms such as replies, asks, group shouts, singing, and compound `(S1,S2)` IDs remain valid;
- post-dialogue Ref2VA alias appositives such as `the ... version` are reduced to their canonical `<Subject N>`
  binding so H3 is less likely to vocalize descriptive reference labels as accidental narration;
- intentionally repeated quoted lines remain separate occurrences at their original causal beats, reuse the same
  recurring speaker ID, and may differ only in authored terminal punctuation without being nested or deduplicated;
- literal edit commands such as `cut scene`/`cut to` create mandatory ordered shot spans; actions, dialogue,
  transformations, wardrobe states, and reactions cannot migrate across those boundaries;
- repeated action/trigger/transformation cycles are expanded as a visible state ladder with countable full-motion
  repetitions and explicit body, wardrobe, expression, camera, and sound changes at every stage;
- after the final tagged line, the generated prompt adds one idempotent no-extra-dialogue closure, keeps every
  character vocally silent through the final frame, and describes the correct number of tagged lines;
- when a short line precedes a long visual continuation, validation requires at least two concrete non-verbal sounds
  inside the remaining timeline instead of leaving an unplanned audio gap;
- absent non-diegetic music requests resolve to `N/A` instead of invented scoring.

When the source explicitly asks the enhancer to **generate, write, or invent dialogue**, audible mode performs a bounded planning pass before the normal enhancement. This also covers scenario wording such as a character who “explains in Spanish what she sees” when no exact words were supplied. The planner returns a compact dialogue ledger constrained by duration (about 2.5 spoken words per second), requested language, line count and existing quoted speech. The main pass must place every planned line exactly once in a valid `<d>[Language] ...</d>` block; changed, omitted, duplicated or additional lines trigger the normal repair loop. Chained multishot output applies the same ledger across its autonomous prompts without losing a line at a cut.

The planner budget is deterministic. It allows at most 12 lines and otherwise approximately one line per four
seconds, multiplied by the chained segment count. Its total new-word ceiling is
`round(effective duration × 2.5) × segment count`, minus words already supplied as source dialogue, with a minimum
ceiling of one new word. In chained mode,
an explicit plan supplies the segment count; otherwise the nonzero `multishot_shot_count` does. The ledger accepts a
compact `{"lines":[{"language":"Spanish","text":"..."}]}` shape, rejects placeholders, `<d>` tags, duplicated
new lines, and lines that merely duplicate source-provided dialogue, and may use up to `repair_attempts` dedicated
ledger repairs before the main enhancement begins.

The extra completion is used only when dialogue authoring was requested. Descriptions of silent action and prompts that merely contain no dialogue still use one completion and do not acquire invented speech. If the planner cannot return valid concrete dialogue within `repair_attempts`, generation stops with a clear planning error before spending the main completion. The manifest records `dialogueLedgerLineCount`, a non-plaintext `dialogueLedgerDigest`, and `dialoguePlanningRepairAttemptsUsed` for reproducibility.

The dialogue-authoring pass runs only under `voice_performance=audible`. With either suppressed-voice policy, the
authoring request is explicitly overridden and no lexical speech is generated. Conversely, merely omitting dialogue
from a prompt never authorizes the model to invent it. Negative directions such as “no dialogue, narration, or
voiceover” are treated as prohibitions, not as dialogue-writing requests.

Visible on-screen text is also preserved exactly, but it is not converted to dialogue unless the source contains a speech cue.

Advanced official dialogue markers are preserved when used correctly. A line that continues across a cut uses
`<scenetrans>` at both connected points and explicitly states that its audio continues across the transition.
`<cutoff>` belongs only inside the final `<d>` block when the video intentionally ends before that utterance finishes.
Singing and lyrics use a stable vocal source plus `<d>[Language] exact lyrics</d>`. Keep dialogue, lyrics, and
shot-synchronized diegetic sound in the timeline; `overall_soundscape` is one paragraph of 1–4 English sentences, and
`non_diegetic_music` is 1–3 English sentences or `N/A`.

These controls constrain the prompt, not the generated waveform, so delivery-critical renders should still be
reviewed or transcribed. The strict source and dialogue-envelope controls were verified on a 15-second Ref2VA render containing a
two-second Spanish line followed by a long portal reveal: the raw H3 output contained the requested line once and no
additional intelligible speech, without audio post-processing.

Quoted thoughts and internal monologue are treated as audible, non-lip-synced speech when `voice_performance=audible`. The enhancer preserves the
exact words inside `<d>[Language] ...</d>`, describes them as an off-screen internal monologue, and explicitly keeps
the on-screen character's lips closed. If an explicit language is absent, conservative recognition handles clear
markers such as Spanish inverted punctuation and accented interrogatives; otherwise the non-translating
`[Original language]` marker is used.

## Audio policies

The three audio controls are independent and are available on the main enhancer, direct-GGUF enhancer, Guide Builder,
and Validator:

| Policy | Values | Meaning |
|---|---|---|
| Scene sounds (ambience & foley) | `auto`, `ensure_audible`, `off` | Follow the scene, explicitly require environmental/physical sound, or suppress it |
| Background score | `follow_prompt`, `add_instrumental`, `off` | Respect the source, add non-vocal music, or emit `non_diegetic_music: N/A` |
| Voice performance | `audible`, `silent_mouth_acting_experimental`, `none` | Preserve exact spoken text, request non-verbal mouth acting, or suppress speech performance |

**Ambience** is the environmental sound bed: rain, wind, waves, traffic, room tone, crowd murmur, forest insects, or
the hum of machinery. **Foley** is sound caused by visible physical action: footsteps, cloth movement, handling an
object, a door closing, an impact, an engine starting, or breathing. It is neither dialogue nor background music.
`auto` lets the enhancer describe sounds naturally implied by the scene; `ensure_audible` makes concrete scene sounds
an explicit requirement; `off` asks for no ambience or foley. For example, a rainy chase can have rain and traffic as
ambience, shoes striking wet pavement and clothes moving as foley, dialogue as voice, and an orchestral cue as score.

Selecting `add_instrumental` reveals **Music genre / style** immediately below **Background score**, followed by an
**Instrumental description** text box. The text
supplies the concrete intent: instrumentation, tempo, meter, rhythm, dynamics, structure, and entry/exit timing. The
selector adapts that material to a musical arrangement grammar without replacing compatible instructions. Abstract
mood wording is converted to audible parameters rather than repeated in the final field. Both controls remain hidden
and are ignored under the other score policies. Leaving the selector at `none` preserves the previous behavior.

Available styles:

| ID | Arrangement emphasis | Never implied automatically |
|---|---|---|
| `cinematic_orchestral` | coherent orchestral families, thematic development, register and dynamic arcs | heroic brass, ostinatos, trailer percussion, choir or huge climax |
| `hybrid_orchestral_electronic` | integrated acoustic orchestral and designed electronic roles | braams, risers, impacts, choir or vocals |
| `action_cinematic` | readable pulse, propulsive figures, controlled low-end weight, and event-linked rises/releases | a chase, fight, danger, braams, choir or constant percussion |
| `mystery_investigation` | sparse question-and-answer motifs, harmonic ambiguity, transparent texture, and deliberate gaps | guilt, crime, danger, supernatural causes, reveal stings or a solved mystery |
| `suspense_build` | low-density opening and a controlled rise in register, subdivision or density alongside existing events | threats, countdowns, heartbeat, ticking, jump scares, braams or false climaxes |
| `combat_rhythmic` | accented rests, changing metrical pressure and synchronization to combat already present | blows, weapons, crowds, victory, chants, impacts or nonstop maximal intensity |
| `chinese_martial_arts` | non-tokenistic Chinese instrumental color with compatible orchestral/percussive roles, agile phrasing and breath-shaped pauses | a dynasty, location, folklore, comedy, wire-fu, combat, gong hits, chanting or a fixed instrument roster |
| `ambient_atmospheric` | sparse evolving timbre, spacious register and restrained harmonic motion | room tone, sound-design filler, drone-only structure or vocal ambience |
| `electronic_modern` | contemporary synthesis, programmed rhythm, controlled low end and automation | club drops, glitches, arpeggios or aggressive bass |
| `synthwave` | restrained analog-style synth vocabulary and period-compatible electronic rhythm | VHS noise, arcade sounds, vocals or forced neon-action mood |
| `rock_instrumental` | playable rhythm section, lead roles, section contrast and amplification | vocals, crowds, virtuoso solos, distortion or anthem structure |
| `jazz` | jazz-informed harmony, voicing, articulation, ensemble interaction and measured improvisation | swing, saxophone, walking bass, big band or nightclub ambience |
| `classical_chamber` | transparent small-ensemble counterpoint, phrasing and acoustic dynamics | full orchestra, concerto display, period pastiche, choir or opera |
| `folk_acoustic` | intimate acoustic ensemble, human-scale pulse and natural dynamics | an inferred culture, nationality, rustic setting, vocals, stomps or claps |
| `hip_hop_instrumental` | intentional groove, drum/bass relationship, texture and section variation | rapping, vocal chops, copyrighted samples, tags or turntable effects |
| `funk_disco` | syncopated interlocking groove, concise harmony and controlled bright accents | four-on-the-floor, slap bass, wah, strings, brass, camp or vocals |
| `horror_tension` | event-supported dissonance, register, pulse, silence and timbral friction | danger, jump scares, screams, heartbeat, chanting, reversed voices or impacts |
| `horror_intense` | unstable harmony, abrasive controlled timbre, extreme-register contrast, ruptured pulse and bounded peaks | gore, monsters, danger, screams, whispers, chanting, jump scares or impacts |

The selected style is authoritative for arrangement, while explicit tempo, timing, dynamics and compatible requested
instruments remain authoritative source facts. Every style remains strictly instrumental: no singing, lyrics, speech,
chants, choir or vocal samples. Semantic adherence is LLM-driven; the Validator checks the normal music policy and
output structure but does not score whether the final prose sounds sufficiently jazz, orchestral or electronic.
Cinematography has one additional bounded literal guard: grading-only sci-fi palettes trigger repair if generated
prose turns them into colored lights, glow, neon fixtures, or emissions absent from the source. This checks a specific
forbidden invention; it is not a general aesthetic-quality score.

`silent_mouth_acting_experimental` intentionally removes the dialogue words, `<d>` blocks, and speaker IDs from the
final H3 prompt. It retains only non-lexical visual direction such as language rhythm, approximate length, cadence,
and pauses. Internal thoughts keep the character's lips closed. MiniMax documents `<d>` for audible dialogue but does
not document a phoneme, viseme, or silent-lip-sync control, so this mode is prompt-only best effort: exact lip sync and
complete silence are not guaranteed. Use `voice_performance=none` when mouth movement is not wanted.

Audio policies cannot selectively remove material embedded in an `<Audio N>` marked `fully_copy`. The Validator
reports a conflict when a copied reference contains voice, music, or environmental sound that the selected policy
forbids.

## References

The enhancer cannot inspect attached images, video, or audio tensors. These two inputs only tell the prompt writer what
the downstream H3 workflow will receive:

- `reference_context` is the easy option: plain-language notes such as `Picture 1 supplies the woman's identity;
  Video 1 supplies her movement; Audio 1 supplies her Spanish voice.` Explicit definitions are authoritative.
- `media_manifest` is the advanced option: structured JSON for workflows that know the exact media inventory, order,
  roles, durations, subject relationships, analyses, and transcripts. It contains metadata, not paths, API keys, or
  encoded media.

Use reference notes for normal manual workflows. Use a manifest when another node or workflow builder can provide
reliable structured facts and you want those facts validated and normalized. If both are present, their generated
context is combined; do not give them contradictory definitions.

The minimal manifest form is:

```json
{
  "mode": "ref2va",
  "items": [
    {"type": "picture", "role": "identity", "analysis": "person in a red coat"},
    {"type": "video", "role": "motion", "duration": 6, "audio_mode": "paired"},
    {"type": "audio", "role": "voice", "duration": 4,
     "transcript": {"language": "Spanish", "text": "Hola."}}
  ],
  "subjects": [
    {"id": 1, "description": "the same person in the red coat",
     "sources": ["<Picture 1>", "<Video 1>"]}
  ]
}
```

Accepted top-level shape and field aliases:

| Location | Field | Meaning |
|---|---|---|
| root | `mode` | Optional explicit mode token; useful when `auto` would be ambiguous |
| root | `items` | Media array; a top-level array is also accepted, and `assets`/`media` are aliases |
| root | `subjects` | Optional authoritative many-to-many reusable subject definitions |
| item | `enabled` | Defaults to true; exactly `false` skips the item and its counters |
| item | `type` | `picture`/`image`, `video`, or `audio`; `kind` is an alias |
| item | `role` | String or array describing how H3 receives it; `roles`/`purpose` are aliases |
| item | `duration_seconds` | Known audio/video duration; `duration` is an alias; zero/omitted means unknown |
| video item | `audio_mode` | `off` (default), `paired`, or `alone`; the latter two create a numbered soundtrack reference |
| item | `analysis` | Trusted textual facts supplied by the workflow; `description` is an alias |
| item | `reuse_mode` | Optional copy/reference instruction included in generated context |
| item | `transcript` | String, object, or list of transcript entries |
| subject | `id` | Numeric subject identity; `subject_id` is an alias |
| subject | `description` | Concrete reusable identity/style/object description; `analysis` is an alias |
| subject | `sources` | One or more already assigned canonical media labels; `source` is an alias |

The parser does not read paths or media bytes and does not verify that a free-form `analysis` is true. Supply only
facts established by the actual connected workflow. Disabled items are skipped; malformed metadata is reported
instead of being concealed or repaired by the LLM.

Supported item types are `picture`/`image`, `video`, and `audio`. Optional fields include `role`, `analysis`,
`duration_seconds`, `audio_mode` (`off`, `paired`, `alone`), and `transcript`. Known video/audio durations must be
2–15 seconds and each media-type total must not exceed 15 seconds. A video transcript is imported only when its
soundtrack is enabled. Optional `subjects` entries provide authoritative many-to-many identity mappings: one asset
may define several subjects and one subject may cite several assets. The manifest is metadata supplied by the
workflow; the enhancer does not pretend to analyze media tensors itself.

Transcript entries may be plain strings or objects such as:

```json
{
  "language": "Spanish",
  "text": "Hola.",
  "source": "<Audio 2>",
  "reuse_mode": "copied"
}
```

A string uses `[Original language]`. `unclear=true` becomes the literal `[unclear]` rather than guessed words.
Conservative cleanup removes leading bullet marks and repeated tildes, collapses repeated punctuation, and adds final
punctuation when absent. An item or transcript entry with `reuse_mode=reference_only` guides delivery/timbre but does
not import exact spoken words. A video transcript is ignored when its `audio_mode` is `off`.

The Manifest Validator enforces the documented Ref2VA envelope: at most 9 pictures, 3 videos, 3 audio references
(enabled video soundtracks count as audio), and 12 media files overall. Known video and audio items must each be 2–15
seconds; total referenced video and total referenced audio must each be at most 15 seconds. Audio cannot be the only
reference modality. Labels are assigned by input order, with an enabled video soundtrack consuming its `<Audio N>`
number before later standalone audio.

Counters are independent by media type. For example, a video with `audio_mode=paired`, followed by standalone audio
and then a picture, becomes `<Video 1>` plus `<Audio 1>`, then `<Audio 2>`, then `<Picture 1>`. `subjects.sources`
must use those effective labels; unknown labels are validation errors.

MiniMax full-reference semantics separate reusable content from standalone media structure:

- `<Subject N>` represents reusable identity, appearance, object design, style, or motion. Its definition cites the
  source asset, for example `The person identity from <Picture 1>` or `The object design from <Picture 2>`.
- `<Picture N>` is defined independently only when the image itself is a first/last frame, storyboard panel,
  composition, or other frame-level anchor.
- `<Video N>` is defined independently only for global editing, continuation, or temporal-structure use. Motion or
  identity extracted from a video becomes a `<Subject N>`.
- `<Audio N>` remains an audio-signal definition and uses the appropriate copy/reference retention marker.

Ref2VA `retention_analysis` uses only these marker families:

| Reference kind | Accepted markers |
|---|---|
| Visual subject/picture/video | `fully_preserved`, `partially_preserved`, `attribute_transfer`, `weak_reference` |
| Audio signal | `fully_copy`, `partially_copy`, `reference`, `weak_reference` |

Every retention line begins with its reference label and the marker must agree with the inferred role. Speaker IDs
belong in `detailed_description`, never in `retention_analysis`. The Validator recommends 350–500 English words in
Ref2VA `detailed_description` and one or two style-establishing sentences before `[Shot 1]`; these length/style checks
are warnings, while missing/invented labels and incompatible markers are errors.

For a person in image 1 holding the exact product from image 2, use:

```text
<Subject 1> is the exact person identity and intrinsic physical appearance from <Picture 1>; explicit wardrobe
instructions in the source prompt take precedence.
<Subject 2> is the exact product design from <Picture 2>; preserve its shape, colors, controls, and markings.
```

Natural positional wording such as `the person in image 1`, `the product in image 2`, motion from `video 1`, or voice
from `audio 1` is normalized generically. Subject numbering is independent from asset numbering: the first reusable
entity is `<Subject 1>` even when its provenance is `<Picture 2>`. Reveal, preservation, and retention requirements
attach to the resulting subject rather than to the source picture. Repeated aliases for the same human/style/object
in one asset are merged, while the most specific role phrase is retained. Phrases such as `version ... in image N`
become alternate versions of the primary identity rather than unrelated duplicate Subjects. There is no
scenario-specific production logic. Connected pictures without a declared role are not silently converted into
subjects; if a model nevertheless invents an orphan `<Subject N>`, the enhancer replaces it with the strongly
specified ordinary-character description from the source prompt when one is available.

### Exact frames and duration

`frame_count=0` is the normal setting: the node uses `duration_seconds` (4–15 seconds). A nonzero frame count is for a
downstream H3 workflow that requires the exact `17 × n + 5` grid:

```text
5, 22, 39, 56, 73, 90, 107, ...
```

The `17` is the step between valid latent lengths, `n` is any non-negative integer, and `+5` is the grid offset. Thus
`90 = 17 × 5 + 5`; it is an exact frame count, not “17k plus 5 thousand.” At H3's 24 fps timing convention, a supplied
frame count becomes the authoritative effective duration (`frame_count / 24`) returned by the node. The validator
reports an error when the effective duration falls outside 4–15 seconds, and warns when it differs from the entered
duration by more than 0.5 seconds. In practice, leave it at zero unless the sampler or workflow explicitly asks for an
exact frame value.

Combining the grid with this node's 4–15 second envelope leaves these accepted nonzero counts:

```text
107, 124, 141, 158, 175, 192, 209, 226, 243, 260, 277, 294, 311, 328, 345
```

For example, 243 frames produce an effective duration of 10.125 seconds. Exact shot-plan durations must sum to that
value, not to the separately entered `duration_seconds`.

`aspect_ratio` does not set pixels; it adds target geometry to the writing/validation contract and is returned unchanged
through the appended `aspect_ratio` output. Supported values are `auto`, `21:9`, `16:9`, `4:3`, `1:1`, `3:4`, and
`9:16`. Configure the actual H3 width/height consistently in the downstream workflow or feed the output into routing
logic that also knows the intended megapixel budget.

## Output metadata

Both enhancer nodes serialize their two diagnostic objects as indented JSON strings. They are designed for inspection,
routing, logging, or downstream parsing; neither object is an H3 conditioning prompt.

### Validation report

Normal single-generation modes return this shape:

```json
{
  "valid": true,
  "mode": "t2va",
  "errors": [],
  "warnings": [],
  "sections": [
    "integrated_multimodal_description",
    "overall_soundscape",
    "non_diegetic_music"
  ],
  "shotCount": 2,
  "aspectRatio": "16:9",
  "mediaManifest": {"items": [], "mode": "", "warnings": [], "errors": []},
  "generationProfile": {
    "valid": true,
    "errors": [],
    "warnings": [],
    "durationSeconds": 8.0,
    "effectiveDurationSeconds": 8.0,
    "frameCount": 0,
    "aspectRatio": "16:9"
  },
  "shotPlan": {
    "schemaVersion": 1,
    "timingMode": "auto",
    "shots": [],
    "provided": false,
    "applied": false,
    "shotCount": 0,
    "effectiveDurationSeconds": 8.0,
    "totalDurationSeconds": 0.0,
    "durationToleranceSeconds": 0.05,
    "expectedCutTimesSeconds": [],
    "digest": "",
    "canonicalJson": "{\"schemaVersion\":1,\"shots\":[],\"timingMode\":\"auto\"}"
  }
}
```

`chained_multishot` replaces `sections`/`shotCount` with `promptCount` and otherwise carries the generation, media,
and shot-plan context. `errors` are contract violations and make `valid=false`; `warnings` do not. The media object in
this report is normalized but can still contain user-supplied analyses and transcripts.

### Enhancement manifest

The manifest combines reproducibility and lifecycle information. Common fields include:

| Field | Meaning |
|---|---|
| `provider` | `local_chat_api` for an endpoint or `managed_llama_server` for direct GGUF |
| `mode` | Resolved lowercase mode |
| `durationSeconds` | Original duration widget value |
| `effectiveDurationSeconds` | Actual duration after a nonzero frame count overrides the widget |
| `frameCount`, `aspectRatio` | Generation geometry contract |
| `valid` | Final selected candidate's validation state |
| `repairAttemptsUsed` | Number of main repair calls attempted, even if an earlier candidate remained best |
| `descriptionEnhanced` | Whether active directorial enhancement was enabled |
| `ambienceFoleyPolicy`, `backgroundScorePolicy`, `voicePerformance` | Applied audio controls |
| `instrumentalDescription` | Present as text only when `add_instrumental` was active; otherwise empty |
| `multishotPromptCount`, `multishotLocksApplied` | Chained item count and number of non-empty locks |
| `creativeTreatment`, `cinematography`, `shotPlan`, `shotsPackage` | Canonical creative, presentation, planning, and per-shot metadata described above |
| `mediaManifestDigest` | SHA-256 of the raw non-empty manifest JSON; the raw manifest itself is not copied here |
| `dialogueLedgerLineCount`, `dialogueLedgerDigest` | Planned-dialogue count and non-plaintext digest |
| `dialoguePlanningRepairAttemptsUsed` | Dedicated ledger repair count |
| `suppressedDialogueCount`, `voiceControlGuarantee` | Suppressed quoted-line count and best-effort flag for silent mouth acting |

Endpoint manifests also record `endpoint`, selected `model`, `temperature`, `maxTokens`, `thinkingDisabled`, and
`lmStudioNativePreferred`. Managed-GGUF manifests record `modelPath`, `serverExecutable`, private `serverEndpoint`,
`gpuLayers`, `contextSize`, `threads`, generation settings, loopback status, whether the server was kept/reused, and
whether it was unloaded after the run. API keys and the random private-server token are never included.

Several integer version fields (`promptContractVersion`, `referenceSemanticsVersion`, `audioPolicyVersion`, and the
schema/catalog versions) let downstream code reject an incompatible future contract instead of guessing.

## Installation

### ComfyUI Manager

Until a Registry entry is published, use **Install via Git URL**:

```text
https://github.com/hyukudan/ComfyUI-MiniMax-H3-Prompt-Enhancer.git
```

Restart ComfyUI after installation.

### Git

From `ComfyUI/custom_nodes`:

```bash
git clone https://github.com/hyukudan/ComfyUI-MiniMax-H3-Prompt-Enhancer.git
```

This node pack has no mandatory third-party Python dependencies. Python 3.10+ and a current ComfyUI installation are
required. The optional direct-GGUF route additionally needs a native `llama-server` executable; it cannot be installed
through Python requirements and is not bundled by this repository.

Registry metadata is included in `pyproject.toml` for future publication.

## Models and llama.cpp

### Remote API behavior

The endpoint must be an absolute HTTP(S) URL. Supplying the API root is clearest, but a URL ending in
`/chat/completions` is reduced to its root automatically. With an explicit model ID, enhancement goes directly to that
model and does not require `/models`. With a blank ID, the node calls `/models`, removes IDs containing obvious
embedding/reranking tokens, and prefers a compact (roughly 0.x–8B or E4B) instruct/chat-looking candidate before
falling back to server order. This is a convenience heuristic, not a quality benchmark.

When `disable_thinking=true`, the endpoint route first tries LM Studio's native `/api/v1/chat` with `reasoning=off` and
`store=false`. If that route is unavailable or returns no usable message, it falls back to OpenAI-compatible
`/chat/completions` with `chat_template_kwargs.enable_thinking=false`. Other servers may ignore that optional argument.
With `disable_thinking=false`, the node uses `/chat/completions` directly and sends no reasoning-disable option.

An empty API-key widget falls back to `MINIMAX_H3_PROMPT_ENHANCER_API_KEY` during enhancement. Browser model discovery
does not read that environment fallback; on an authenticated server, enter the model ID manually or temporarily enter
the key to refresh the picker. The backend sends it only as `Authorization: Bearer ...`.

### GGUF discovery

The main dropdown scans text GGUF files under:

```text
ComfyUI/models/llm_gguf/
```

Multimodal projection files whose names contain `mmproj` are excluded because enhancement is text-only. The same
dropdown also scans roots in `MINIMAX_H3_GGUF_MODEL_DIRS`. The specialized GGUF node accepts any model under a ComfyUI
registered model root, the standard LM Studio cache, the environment roots, or its explicit
`registered_model_dirs`. A path outside those roots is rejected even when the file exists.

When discovery finds at least one usable model, the sorted first model is the default dropdown value. The sentinel
`(no GGUF models found)` is emitted only when no usable text GGUF exists.

### llama-server discovery

The main node searches, in order:

1. `MINIMAX_H3_LLAMA_SERVER`;
2. `llama-server` available on `PATH`;
3. runtimes below `ComfyUI/models/prompt_enhancers/runtimes/`.

This dropdown selects an executable build of llama.cpp, not another language model or API provider. More than one entry
can appear when several compatible `llama-server` builds are installed. LM Studio, Ollama, and other already-running
servers use the OpenAI-compatible endpoint route instead.

Install llama.cpp from its [official releases](https://github.com/ggml-org/llama.cpp/releases) or build it for your
platform. The extension never downloads or updates the executable silently. If another node has already installed a
compatible `llama-server` below `ComfyUI/models/prompt_enhancers/runtimes/`, this extension discovers and reuses it;
ownership and updates remain with the component that installed it.

The managed command binds to loopback on an ephemeral port and uses `--parallel 1`, `--jinja`, the selected context,
and a random API key. A non-`auto` GPU-layer value is passed through `--n-gpu-layers`; a positive thread count is
passed through `--threads`. Startup waits on `/health` and includes the tail of server output in early-exit/timeout
errors. On Windows the process launches without a console window.

Environment variables:

| Variable | Purpose |
|---|---|
| `MINIMAX_H3_PROMPT_ENHANCER_API_KEY` | Remote enhancement bearer token when the API-key widget is blank |
| `MINIMAX_H3_LLAMA_SERVER` | Exact preferred `llama-server` executable for discovery |
| `MINIMAX_H3_GGUF_MODEL_DIRS` | Additional trusted/searchable GGUF roots separated by the OS path separator or newlines |

### Model recommendations

- Official Qwen 3 4B GGUF Q4_K_M is a compact multilingual starting point.
- Official Gemma 4 E4B QAT GGUF offers higher quality with greater memory use and requires a recent llama.cpp build.
- Community uncensored/abliterated variants may reduce refusals but can weaken section discipline or instruction fidelity.
- Quantization and runtime compatibility evolve independently; update llama.cpp when a GGUF reports an unsupported tensor or architecture type.

## Memory policy

`keep_server_loaded=false` is the production-safe default:

- start private server;
- load GGUF;
- enhance and optionally repair;
- terminate server;
- return all model RAM/VRAM to the operating system.

`keep_server_loaded=true` reuses an identical model/runtime/context configuration across queued enhancements. Changing the model or runtime automatically closes the previous cached server. Use **Unload GGUF Prompt Model** before H3 when memory pressure matters. ComfyUI shutdown also closes the cached process.

There is one process-wide cached prompt server. Its reuse signature is the server executable, GGUF path, GPU-layer
selection, context size, and thread count. A dead process or any signature change is replaced automatically. A
non-persistent invocation first unloads an existing cache, runs its own private server, and always stops it in a
`finally` path, including completion failures.

Keeping a model loaded saves startup time but reserves its VRAM. It does not improve generation quality.

## Workflow compatibility and migration

Creative direction was added without reordering the v0.5.0 positional inputs. `creative_treatment_json`,
`shot_plan_json`, and `cinematography_json` are optional neutral fields appended after every legacy input on the main enhancer, specialized GGUF
enhancer, Guide Builder, and Validator. Existing output names/order are unchanged; per-shot extraction uses the new
Shot Selector node instead of changing enhancer outputs. Old workflows therefore retain their backend, audio,
duration, reference, and output connections.

Version 0.6.x appends `instrumental_style` after those fields on the main enhancer, specialized GGUF enhancer, and
Guide Builder. Its neutral default is `none`; no earlier widget position or output changes.

On load, the frontend repairs known historical serialization shifts:

- obsolete serialized model-refresh/model-picker values are removed from the positional list;
- a context-size value displaced into `instrumental_description` is moved back when it is clearly a context value;
- zero or non-numeric migrated context/startup values resolve to 16384/180;
- enums, booleans, strings, timeouts, token limits, frame counts, local paths, and hidden runtime values are
  type/range checked before ComfyUI builds the execution request;
- the visual Creative direction, Cinematography, and Shot/Segment plan panels are reconstructed from three persistent
  JSON fields and are themselves non-persistent;
- imported creative state is reduced to supported schema-v1 selections; imported incomplete exact timing is
  downgraded as a whole to automatic timing, never left half timed.

These repairs address displaced widget data, not meaningful user mistakes. Malformed direct JSON, unsupported
profiles, invalid frame grids, blank explicit shot descriptions, and conflicting shot counts remain visible errors.
After updating the extension, restart ComfyUI and hard-refresh the frontend (`Ctrl+F5`); reopen the workflow so the
configuration hook can run before queueing it.

## Privacy and security

- Remote endpoints are blocked unless they are loopback or `allow_remote_endpoint=true`.
- API keys are sent only as authorization headers and are excluded from manifests.
- The password-style API-key widget masks the value on screen but ComfyUI may still serialize it in the workflow.
  Clear it before sharing workflow JSON, or leave it blank and use `MINIMAX_H3_PROMPT_ENHANCER_API_KEY`.
- A remote endpoint receives the basic prompt, generated guide, reference notes, media metadata, shot descriptions,
  and any exact dialogue needed for rewriting. It never receives actual image/video/audio bytes from this node, but
  the text may still be sensitive. Use only an endpoint whose privacy policy you accept.
- The private GGUF server binds to `127.0.0.1`, uses a random port and a random per-process API key.
- Subprocesses launch with `shell=False` and are terminated on normal completion, errors, configuration changes, explicit unload, or ComfyUI shutdown.
- GGUF paths must be under registered model roots.
- GGUF files are native-runtime inputs. Obtain models and llama.cpp builds from trusted sources and verify published checksums where possible.

Diagnostic outputs are credential-safe, not necessarily content-free. `validation_report.mediaManifest` can contain
analyses/transcripts; an active `enhancement_manifest.shotPlan` contains row descriptions; `shotsPackage` can contain
the full enhanced prompt; and a managed-GGUF manifest contains local executable/model paths. Sanitize these outputs
before publishing logs or bug reports. A SHA-256 digest is useful for equality/reproducibility, not encryption of
guessable short text.

## Troubleshooting

### Local model or llama-server dropdown is empty

Place text GGUF files in `ComfyUI/models/llm_gguf`. Put `llama-server` on `PATH`, set `MINIMAX_H3_LLAMA_SERVER`, or place it below the documented runtime directory. Restart ComfyUI or refresh node definitions afterward.

### Widgets or outputs extend beyond the node frame

Reload the browser with `Ctrl+F5` after updating the extension. The frontend recalculates the node size when it is
created, configured, or switched between remote and local modes. Model discovery itself does not resize the node, and
multiline fields are not measured from their stretched DOM height; this prevents repeated refreshes from making
Reference notes or Media metadata grow indefinitely.

### Creative controls are missing or still show old labels

Restart ComfyUI, hard-refresh with `Ctrl+F5`, then reopen the workflow. The browser extension supplies the English
**Model setup**, **Creative direction**, **Cinematography**, **Shot plan**, **Segment plan**, **Advanced settings**, **+ Add shot**, and
**+ Add independent segment** UI. The
canonical values are still stored in `creative_treatment_json`, `cinematography_json`, and `shot_plan_json`; do not add duplicate manual
widgets to compensate for a stale browser bundle.

### Creative-treatment, Cinematography, or shot-plan JSON is rejected

Use `schemaVersion: 1`, the exact camelCase keys, and only tokens listed in this README. Remove comments and trailing
commas because the fields require standard JSON. Automatic timing must contain no `durationSeconds`; exact timing
must contain a positive numeric value on every row. Ensure IDs are unique, descriptions are non-empty, the row count
does not conflict with literal source cuts or `multishot_shot_count`, and exact durations use the effective
frame-derived duration when `frame_count` is nonzero.

`cinematography_json` accepts at most 32,768 characters. `cameraAmplitude` and `cameraSpeed` must remain `auto` when
`cameraMotion` is `none`, `static`, or `pov`; Arc, Tracking, and POV also work best when the Basic prompt or shot row
names an unambiguous focal subject or point-of-view owner.

The visual editor repairs unsupported imported presentation state, but values injected directly through API-format
workflows are intentionally strict and fail before an LLM call.

### Exact timing changes when I add, remove, or change mode

This is expected editor behavior. Switching to exact timing evenly allocates the effective duration; adding/removing
rows, changing `duration_seconds`/`frame_count`, or switching between a normal mode and `chained_multishot` rebalances
the rows. In a normal mode, the last row absorbs rounding so the sum stays exact. In chained mode, every row is reset
to the full uniform per-segment duration. Manual duration edits are preserved but the status line remains invalid
until the required sum/uniformity is restored.

### Shot Selector returns a blank `shot_prompt`

Read `autonomous` and the status text. Blank output is a safety result, not lost data: the source prompt may have
failed validation, extraction may be incomplete, a local keyframe anchor may be missing, or Ref2VA retention/audio
may not be safely separable. `timeline_body` remains available for inspection. Render the complete
`enhanced_prompt`, use a truly autonomous `chained_multishot` item, or author/regenerate a standalone prompt; do not
route the fragment around the guard.

### Model discovery fails or returns non-JSON

Confirm that the endpoint is the OpenAI-compatible API root (commonly `http://127.0.0.1:11434/v1` for Ollama or
`http://127.0.0.1:1234/v1` for LM Studio), not its web page and not the full `/chat/completions` URL. Restart ComfyUI once after
installing a version that introduces the discovery backend, then use `Ctrl+F5`. A 404/405 generally means that route
has not been loaded yet. A server that does not implement `/models` can still be used: type the exact server model ID
manually. Blank **API model ID** requires a working `/models` response.

### GGUF reports an unsupported tensor type

Update llama.cpp. A new GGUF quantization may be newer than the selected runtime. This is one reason the extension does not pin an in-process `llama-cpp-python` wheel.

### Managed GGUF enhancement is slower than an already-running API server

Per-run mode includes process startup and model loading. Enable `keep_server_loaded` for repeated prompt iteration when sufficient VRAM is available, or use an already-running OpenAI-compatible endpoint such as Ollama or LM Studio.

### `input out of range` after updating the node

Refresh node definitions after updating. Older workflows may deserialize newly introduced local-runtime widgets as zero; zero is accepted as automatic and normalized to the safe context and startup-timeout defaults. The frontend also repairs those values when the workflow is opened.

The frontend also repairs two historical serialization cases: a context value shifted into
`instrumental_description`, and the former serialized refresh/model-picker helpers shifting later widget values. It
also type-checks the complete enhancer form: modes, durations, model-generation limits, timeouts, policies, booleans,
text fields, and every hidden local-runtime value. Invalid or displaced values are restored to documented defaults
before ComfyUI builds the execution request. This matters even in remote mode because ComfyUI validates hidden widgets
too. Semantic mistakes that reflect real user input—such as malformed manifest JSON or a nonzero frame count outside
H3's grid—remain visible validation errors instead of being silently rewritten. The frontend reapplies remote/local
visibility after ComfyUI finishes configuring the node.

### Dialogue disappears or has no language tag

Update to the latest node version and inspect `validation_report`. Spoken quoted source content should be present verbatim inside `<d>[Language] ...</d>`. Include an explicit phrase such as `says in Catalan` when the language matters.

### The result is valid but the description is shallow

Do not increase `max_tokens` first. A complete short answer usually reflects model capability, sparse source facts, or
too many competing style instructions rather than output truncation. Select a stronger chat/instruct model explicitly,
add concrete subject/position/action/contact/final-state facts, provide reliable reference analysis, add shot rows where
boundaries matter, and use only the Creative/Cinematography choices that contribute useful direction. Ref2VA below the
recommended 350-word depth produces a warning; warnings do not trigger the repair loop.

If the output instead ends abruptly, omits required final sections, or contains malformed JSON, increase
`max_tokens` and ensure `context_size` can hold the complete system/user instructions plus the answer. Large chained
packages may need a 32k context or smaller batches because a repair call also includes the previous complete candidate.

### The validator still reports errors

On an enhancer, increase `repair_attempts` to one or two. Structural validity does not guarantee that a small model
can follow a complex prompt; try a stronger instruct GGUF or an endpoint model.

The enhancer can exhaust repairs and still return its best invalid candidate. Read the concrete `errors` array rather
than assuming the last completion was selected. The standalone Validator never repairs; send its report back through
your external LLM or use the integrated enhancer. For source-fidelity errors, supply the same original
`source_prompt`, reference context, media manifest, and controls that were used to author the prompt.

### HTTP 401, 404, or timeout

Verify endpoint root, API key, model ID, server status, and timeout. Use the API root such as `/v1`, not the full `/chat/completions` URL unless the server requires it.

If enhancement works through the environment API key but **Refresh API model list** returns 401, enter the exact model
ID manually; discovery does not consume the environment-key fallback. For local GGUF startup timeouts, increase
`startup_timeout` and inspect the included llama-server log tail. Unsupported quantization/architecture messages call
for a newer llama.cpp build, while an out-of-memory error calls for fewer GPU layers, a smaller context/model, or CPU
offload.

## Development

Run from the repository root:

```bash
python -m pytest -q
ruff check .
node --check web/backend_toggle.js
git diff --check
```

The current suite contains 217 automated tests. They cover all H3 modes, timing, exact-frame profiles, aspect ratios,
media manifests and limits, chained multishot output, alignment, single-shot simultaneity and gradual progression, shot
budgets, all four creative-profile catalogs, cinematography controls and H3 camera grammar, anime inheritance and deduplication, strict JSON and shot-plan limits,
exact cut normalization, no-op compatibility, legacy positional/widget layouts, manifest digests, autonomous shot
selection and cross-shot audio/dialogue isolation, exact-once dialogue/language preservation, untagged vocal-cue
rejection, explicit age-category retention, internal voiceover, reference alias/variant merging, best-candidate repair
selection, rejection of invented dialogue and music, independent audio policies, endpoint/model discovery policy,
GGUF discovery, process isolation, persistent reuse, explicit unload, and failure cleanup.

Bug reports should include the ComfyUI version, extension commit, backend, model identifier, resolved mode, sanitized source prompt, and complete validation/error report. GGUF reports should also include the llama.cpp build and quantization. Never attach API keys or private reference content.

## Guide basis

The implementation is based on MiniMax's public
[base Video Prompt Writing Guide](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/docs/VIDEO_PROMPT_WRITING_GUIDE_base_en.md),
[full-reference Video Prompt Writing Guide](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/docs/VIDEO_PROMPT_WRITING_GUIDE_ref_en.md),
and [official H3 launch documentation](https://minimaxi.com/blog/minimax-h3), with additional defensive validation and
workflow-oriented controls. It is an original implementation and is not an official MiniMax or ComfyUI product.

As of 9 August 2026, those two prompt-writing guides are the complete functional documentation in the official H3
repository's `docs` directory (the remaining file covers licensing). This pack implements their documented prompt
contracts for T2VA, I2VA, FL2VA, L2VA, and Ref2VA: section order, alignment sentences, chronological descriptions,
shot numbering and cut timing, first/last-frame development, natural camera vocabulary including POV and optional
amplitude/speed, speaker IDs, exact-language dialogue and lyrics, voiceover, cross-cut speech, visible text,
soundscape/music separation, reference definitions and labels, task summaries, retention relationships, reference
audio behavior, and the normal Ref2VA description-depth recommendation.

This coverage claim applies to prompt writing, normalization, and structural validation. Resolution, frame geometry,
sampler, steps, CFG, scheduler, model/LoRA weights, reference tensors, masks, and native H3 conditioning remain the
responsibility of the surrounding ComfyUI workflow. The optional optics, depth-of-field, grain, diffusion, halation,
and motion-rendering selectors are conservative natural-language directing aids; the official guides do not define
them as deterministic H3 runtime parameters.

## Project status and license

The project is beta software. Prompt validation and backend lifecycle behavior are tested, but model outputs remain nondeterministic.

Licensed under [GPL-3.0-only](LICENSE).
