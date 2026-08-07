# ComfyUI MiniMax H3 Prompt Enhancer

Guide-constrained prompt enhancement, repair, and validation nodes for MiniMax H3 workflows in ComfyUI.

[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB.svg)](pyproject.toml)
[![Status: Beta](https://img.shields.io/badge/status-beta-orange.svg)](#project-status-and-license)

The main node turns a short request into MiniMax H3's documented audiovisual prompt structure. It can use either:

1. an OpenAI-compatible endpoint such as LM Studio; or
2. a local GGUF selected from `ComfyUI/models/llm_gguf`, launched through an isolated `llama-server` process.

The package does not bundle model weights or llama.cpp, does not inspect reference pixels, and does not replace H3 conditioning. It prepares and validates text for native or custom H3 workflows.

## Contents

- [Why use it?](#why-use-it)
- [Backend design](#backend-design)
- [Quick start](#quick-start)
- [Interface behavior](#interface-behavior)
- [Nodes](#nodes)
- [Exact wiring](#exact-wiring)
- [Prompt contracts](#prompt-contracts)
- [Dialogue, language, and exact text](#dialogue-language-and-exact-text)
- [Audio policies](#audio-policies)
- [References](#references)
- [Installation](#installation)
- [Models and llama.cpp](#models-and-llamacpp)
- [Memory policy](#memory-policy)
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
| Feed duration downstream | `duration_seconds` output on both enhancer nodes |
| Drive chained multishot samplers | `chained_multishot` mode plus Chained Multishot Output |
| Ground prompts in connected media metadata | Optional JSON media manifest and Manifest Validator |
| Reclaim VRAM before H3 | Per-run unload by default, with optional persistent mode |

Validation is a structural gate. It cannot guarantee visual quality, identity fidelity, physical correctness, or diffusion-model compliance.

## Backend design

| Route | Runtime | Best for | Memory lifecycle |
|---|---|---|---|
| OpenAI-compatible | LM Studio, Ollama, or another compatible API | Existing local/remote LLM services | Controlled by that service |
| Local GGUF | Standalone `llama-server` | Direct use of GGUF files without LM Studio running | Close after every prompt by default, or keep loaded on request |
| Existing ComfyUI LLM node | QwenVL/GGUF/other node plus Guide Builder | Reusing a loader already present in the graph | Controlled by that node |

### Why standalone llama-server?

Some ComfyUI prompt enhancers import `llama-cpp-python` inside the long-running ComfyUI process. This pack deliberately uses a standalone `llama-server` for its direct GGUF route:

- newer llama.cpp builds can support newer architectures or quantizations without replacing a Python/CUDA wheel shared by other custom nodes;
- a native-model crash is isolated from ComfyUI;
- terminating the process releases its RAM and VRAM deterministically;
- the same OpenAI-compatible request pipeline is used for remote and local execution.

The trade-off is model startup time when `keep_server_loaded` is disabled. Users with sufficient VRAM can keep the process alive between prompt-enhancement calls.

`llama-server` is required only for the local GGUF route. The endpoint route, Guide Builder, and Validator do not need it.

## Quick start

### Remote or LM Studio

1. Install the node pack and restart ComfyUI.
2. Start an OpenAI-compatible server. LM Studio commonly uses `http://127.0.0.1:1234/v1`.
3. Add **MiniMax H3 Prompt Enhancer** from `MiniMax H3 → Prompting`.
4. Leave `use_remote_model=true`.
5. Enter the endpoint and API key if required, then press **Refresh API model list**.
6. Choose the model under **Available API models**, or type its exact server ID into **API model ID**. Leaving the ID blank asks the node to choose a suitable chat/instruct model automatically.
7. Connect `enhanced_prompt` to H3 conditioning and `duration_seconds` to the downstream duration control.

Loopback endpoints work by default. Sending prompts to another host requires `allow_remote_endpoint=true`.

### Local GGUF without LM Studio

1. Install a current official llama.cpp build containing `llama-server` or `llama-server.exe`.
2. Place one or more text-generation GGUF files in `ComfyUI/models/llm_gguf/`.
3. Restart ComfyUI or refresh node definitions.
4. Add **MiniMax H3 Prompt Enhancer** and set `use_remote_model=false`.
5. Select `local_model` and the detected `llama_server_path` from their dropdowns.
6. Leave `keep_server_loaded=false` when H3 needs the VRAM immediately afterward.

## Interface behavior

The main node presents only the controls relevant to the current selection:

- **Use LM Studio / API model** enabled: shows endpoint, API model ID, API key, remote-host permission, model picker, and refresh button.
- **Use LM Studio / API model** disabled: shows local GGUF, llama.cpp server, GPU layers, context, threads, startup timeout, and model-retention controls.
- `add_instrumental`: reveals **Instrumental description**.
- `chained_multishot`: reveals the multishot count and identity/voice/setting locks.
- `ref2va`: reveals **Reference notes**. **Show advanced controls** additionally reveals media metadata JSON and exact frame count.

Hidden fields retain their saved values, but only the selected backend is executed. The discovery picker and refresh button are UI helpers and are deliberately not serialized into the workflow. This prevents them from shifting saved widget values when the extension is updated.

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
| `enhanced_prompt` | Normalized prompt for H3 conditioning |
| `validation_report` | Resolved mode, errors, and recommendations |
| `enhancement_manifest` | Backend/model/mode/memory metadata; never contains an API key |
| `duration_seconds` | Effective downstream duration; when exact frames are set this is `frame_count / 24` |

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
| `temperature` | `0.2` | Low variance for structured rewriting |
| `max_tokens` | `4096` | Completion budget |
| `repair_attempts` | `2` | Re-prompts with validator errors (0-4); source-fidelity errors receive priority |
| `disable_thinking` | enabled | Requests direct structured output where supported |
| `use_remote_model` | enabled | Endpoint when enabled; local GGUF when disabled |
| `enhance_description` | enabled | Adds bounded cinematic direction while preserving source facts and exact text |
| `ambience_foley_policy` | `auto` | Controls non-musical, non-spoken scene sound: environment plus physical action sounds |
| `background_score_policy` | `follow_prompt` | Follow the source, add an instrumental score, or force music off |
| `instrumental_description` | empty | When `add_instrumental` is selected, describe instrumentation, tempo, rhythm, and dynamics; mood wording is translated into audible parameters |
| `voice_performance` | `audible` | Audible dialogue, experimental silent mouth acting, or no voice performance |

Remote-only controls include `endpoint`, `model`, `api_key`, and `allow_remote_endpoint`. Their values remain saved in
the workflow when hidden. Local-only controls include `local_model`, `llama_server_path`, `gpu_layers`, `context_size`,
`threads`, `startup_timeout`, and `keep_server_loaded`.

In remote mode, press **Refresh API model list** after entering the endpoint and API key. ComfyUI requests the
endpoint's `/models` resource through its own same-origin backend, avoiding browser CORS restrictions. It filters
obvious embedding and reranking models and fills **Available API models**. Selecting an entry copies its exact model
ID into the saved **API model ID** field. The model string must be the ID reported by the server, not a model file path
or a display name invented by this extension. Manual IDs and blank automatic selection remain available for servers
that do not implement discovery. Non-local endpoints still require the explicit safety toggle.

`context_size=0` and `startup_timeout=0` are migration-safe automatic values. They resolve to 16384 tokens and 180 seconds respectively. This prevents workflows saved before those local controls existed from failing ComfyUI's input-range validation.

### MiniMax H3 GGUF Prompt Enhancer

The specialized direct-GGUF node exposes both model and runtime paths, extra registered model roots, GPU-layer offload, context, threads, timeouts, and the persistent-process toggle. It returns the same four outputs as the main enhancer.

Use it when you need custom paths or prefer a graph dedicated to GGUF. The main node is simpler for models under `ComfyUI/models/llm_gguf`.

### MiniMax H3 Unload GGUF Prompt Model

Stops the optional persistent prompt-model server and releases its RAM/VRAM. It is safe to queue when no persistent model is loaded.

### MiniMax H3 Prompt Guide Builder

Builds `system_prompt`, `user_prompt`, and `resolved_mode` without calling an LLM. Connect the two prompt outputs to an existing QwenVL, GGUF, Ollama, or other text-generation node, then validate its result.

### MiniMax H3 Prompt Validator

Validates enhanced or manually authored prompts without running an LLM. It checks section order, alignment instructions, shot numbering and timing, language-tagged dialogue, exact quoted content, reference labels, and full-reference definitions.

### MiniMax H3 Media Manifest Validator

Normalizes a JSON media inventory, assigns effective `<Picture N>`, `<Video N>`, and `<Audio N>` labels in input order, and checks the documented reference limits. Enabled video soundtracks consume an audio ordinal before later standalone audio. It also emits text context suitable for the enhancer.

### MiniMax H3 Chained Multishot Output

Validates canonical `{"prompts":[...]}` output from `chained_multishot`, produces the `---`-separated script accepted by chained H3 samplers, and reports total planned duration. Each item is an independent conditioning pass, not a `[Shot N]` inside one generation.

## Exact wiring

### Switchable main node

```text
basic prompt → MiniMax H3 Prompt Enhancer → enhanced_prompt → H3 conditioning
                                      ├──→ validation_report
                                      ├──→ enhancement_manifest
                                      └──→ duration_seconds → video-duration control
```

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
basic prompt → Prompt Guide Builder.system_prompt ─┐
               Prompt Guide Builder.user_prompt ──┼→ existing LLM → Prompt Validator → H3
```

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

The current Ref2VA summary task names are `keyframe completion`, `reference generation`, `video editing`, `video continuation`, `audio reuse`, and `audio reference`; multiple relationships use the exact ` + ` separator. Dialogue validation accepts the official natural vocal forms (`says`, `replies`, group shouts, singing, and compound speaker IDs) while still enforcing stable sources, exact text, language tags, and no invented speech.

`chained_multishot` deliberately does not use the three- or six-section single-generation contracts. It repeats supplied identity, wardrobe, setting, style, and voice facts in each autonomous prompt and treats the often-cited ~2.5 spoken words/second only as a warning heuristic. It never invents dialogue to fill silence.

## Description enhancement

`enhance_description` controls whether the LLM acts as a restrained director or only as a format adapter.

When enabled, it develops terse source wording into concrete staging, composition, performance, lighting, camera
motion, pacing, action continuity, physical sound, and requested music. It may introduce a cut only when the cut
provides a meaningful change in viewpoint, time, location, scale, or information. Otherwise it prefers a motivated
continuous camera move.

Short prompts of five seconds or less that explicitly describe simultaneous action with `while` or `mientras`
receive a one-shot and simultaneity contract unless the source requests an edit or sequence. Gradual progressions such
as materializations, reveals, or actions developing `poco a poco` also remain one continuous take at any duration when
the source supplies no explicit cut structure. Other sources without explicit edits prefer one shot and are capped at
two, preventing arbitrary evenly spaced three-second divisions. Numeric event times invented inside shot prose are
rejected; absolute cut times belong only in later `[Shot N]` headers.

When disabled, it performs a conservative conversion into MiniMax H3's required structure and preserves the source's
original level of detail. Both modes keep quoted dialogue, reference bindings, identities, requested actions, timing,
and the intended ending authoritative.

## Dialogue, language, and exact text

MiniMax's guide requires spoken content inside a dialogue block:

```text
The speaker (S1) says: <d>[Catalan] A ver, cabrones, quiero flaó de ese</d>.
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
- after the final tagged line, the generated prompt closes the speaker's mouth and explicitly states that every
  character remains vocally silent through the final frame;
- when a short line precedes a long visual continuation, validation requires at least two concrete non-verbal sounds
  inside the remaining timeline instead of leaving an unplanned audio gap;
- absent non-diegetic music requests resolve to `N/A` instead of invented scoring.

Visible on-screen text is also preserved exactly, but it is not converted to dialogue unless the source contains a speech cue.

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

Selecting `add_instrumental` reveals an **Instrumental description** text box. Its contents become authoritative musical
direction for the enhancer (instrumentation, tempo, rhythm, and dynamics). Abstract mood wording is converted to those
audible parameters rather than repeated in the final field. Leaving it empty lets the model choose concrete musical
parameters. The field remains hidden and is ignored under the other score policies.

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
     "sources": ["<Picture 1>", "<Picture 2>"]}
  ]
}
```

Supported item types are `picture`/`image`, `video`, and `audio`. Optional fields include `role`, `analysis`,
`duration_seconds`, `audio_mode` (`off`, `paired`, `alone`), and `transcript`. Known video/audio durations must be
2–15 seconds and each media-type total must not exceed 15 seconds. A video transcript is imported only when its
soundtrack is enabled. Optional `subjects` entries provide authoritative many-to-many identity mappings: one asset
may define several subjects and one subject may cite several assets. The manifest is metadata supplied by the
workflow; the enhancer does not pretend to analyze media tensors itself.

The Manifest Validator enforces the documented Ref2VA envelope: at most 9 pictures, 3 videos, 3 audio references
(enabled video soundtracks count as audio), and 12 media files overall. Known video and audio items must each be 2–15
seconds; total referenced video and total referenced audio must each be at most 15 seconds. Audio cannot be the only
reference modality. Labels are assigned by input order, with an enabled video soundtrack consuming its `<Audio N>`
number before later standalone audio.

MiniMax full-reference semantics separate reusable content from standalone media structure:

- `<Subject N>` represents reusable identity, appearance, object design, style, or motion. Its definition cites the
  source asset, for example `The person identity from <Picture 1>` or `The object design from <Picture 2>`.
- `<Picture N>` is defined independently only when the image itself is a first/last frame, storyboard panel,
  composition, or other frame-level anchor.
- `<Video N>` is defined independently only for global editing, continuation, or temporal-structure use. Motion or
  identity extracted from a video becomes a `<Subject N>`.
- `<Audio N>` remains an audio-signal definition and uses the appropriate copy/reference retention marker.

For a person in image 1 holding the exact product from image 2, use:

```text
<Subject 1> is the exact person identity and wardrobe from <Picture 1>.
<Subject 2> is the exact product design from <Picture 2>; preserve its shape, colors, controls, and markings.
```

Natural positional wording such as `the person in image 1`, `the product in image 2`, motion from `video 1`, or voice
from `audio 1` is normalized generically. Subject numbering is independent from asset numbering: the first reusable
entity is `<Subject 1>` even when its provenance is `<Picture 2>`. Reveal, preservation, and retention requirements
attach to the resulting subject rather than to the source picture. Repeated aliases for the same human/style/object
in one asset are merged, while the most specific role phrase is retained. Phrases such as `version ... in image N`
become alternate versions of the primary identity rather than unrelated duplicate Subjects. There is no
scenario-specific production logic.

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

This node pack has no mandatory third-party Python dependencies. Python 3.10+ and a current ComfyUI installation are required.

Registry metadata is included in `pyproject.toml` for future publication.

## Models and llama.cpp

### GGUF discovery

The main dropdown scans text GGUF files under:

```text
ComfyUI/models/llm_gguf/
```

Multimodal projection files whose names contain `mmproj` are excluded because enhancement is text-only. The specialized GGUF node can additionally use trusted roots registered through `MINIMAX_H3_GGUF_MODEL_DIRS`.

### llama-server discovery

The main node searches, in order:

1. `MINIMAX_H3_LLAMA_SERVER`;
2. `llama-server` available on `PATH`;
3. runtimes below `ComfyUI/models/prompt_enhancers/runtimes/`.

Install llama.cpp from its [official releases](https://github.com/ggml-org/llama.cpp/releases) or build it for your platform. The extension never downloads or updates the executable silently.

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

Keeping a model loaded saves startup time but reserves its VRAM. It does not improve generation quality.

## Privacy and security

- Remote endpoints are blocked unless they are loopback or `allow_remote_endpoint=true`.
- API keys are sent only as authorization headers and are excluded from manifests.
- The private GGUF server binds to `127.0.0.1`, uses a random port and a random per-process API key.
- Subprocesses launch with `shell=False` and are terminated on normal completion, errors, configuration changes, explicit unload, or ComfyUI shutdown.
- GGUF paths must be under registered model roots.
- GGUF files are native-runtime inputs. Obtain models and llama.cpp builds from trusted sources and verify published checksums where possible.

## Troubleshooting

### Local model or llama-server dropdown is empty

Place text GGUF files in `ComfyUI/models/llm_gguf`. Put `llama-server` on `PATH`, set `MINIMAX_H3_LLAMA_SERVER`, or place it below the documented runtime directory. Restart ComfyUI or refresh node definitions afterward.

### Widgets or outputs extend beyond the node frame

Reload the browser with `Ctrl+F5` after updating the extension. The frontend recalculates the node size when it is
created, configured, or switched between remote and local modes. Model discovery itself does not resize the node, and
multiline fields are not measured from their stretched DOM height; this prevents repeated refreshes from making
Reference notes or Media metadata grow indefinitely.

### Model discovery fails or returns non-JSON

Confirm that the endpoint is the OpenAI-compatible API root (for LM Studio, commonly
`http://127.0.0.1:1234/v1`), not its web page and not the full `/chat/completions` URL. Restart ComfyUI once after
installing a version that introduces the discovery backend, then use `Ctrl+F5`. A 404/405 generally means that route
has not been loaded yet. A server that does not implement `/models` can still be used: type the exact server model ID
manually, or leave **API model ID** blank for automatic selection.

### GGUF reports an unsupported tensor type

Update llama.cpp. A new GGUF quantization may be newer than the selected runtime. This is one reason the extension does not pin an in-process `llama-cpp-python` wheel.

### GGUF enhancement is slower than LM Studio

Per-run mode includes process startup and model loading. Enable `keep_server_loaded` for repeated prompt iteration when sufficient VRAM is available, or use the already-running LM Studio endpoint.

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

### The validator still reports errors

Increase `repair_attempts` to one or two. Structural validity does not guarantee that a small model can follow a complex prompt; try a stronger instruct GGUF or an endpoint model.

### HTTP 401, 404, or timeout

Verify endpoint root, API key, model ID, server status, and timeout. Use the API root such as `/v1`, not the full `/chat/completions` URL unless the server requires it.

## Development

Run from the repository root:

```bash
python -m pytest -q
ruff check .
node --check web/backend_toggle.js
git diff --check
```

The current suite contains 103 automated tests. They cover all H3 modes, timing, exact-frame profiles, aspect ratios,
media manifests and limits, chained multishot output, alignment, single-shot simultaneity and gradual progression, shot budgets,
exact-once dialogue/language preservation, untagged vocal-cue rejection, explicit age-category retention, internal
voiceover, reference alias/variant merging, best-candidate repair selection, rejection of invented dialogue and music,
independent audio policies, endpoint/model discovery policy, GGUF discovery, process isolation, persistent reuse,
explicit unload, and failure cleanup.

Bug reports should include the ComfyUI version, extension commit, backend, model identifier, resolved mode, sanitized source prompt, and complete validation/error report. GGUF reports should also include the llama.cpp build and quantization. Never attach API keys or private reference content.

## Guide basis

The implementation is based on MiniMax's public base and full-reference Video Prompt Writing Guides and the official
H3 prompt-writing skill, with additional defensive validation and workflow-oriented controls. It is an original
implementation and is not an official MiniMax or ComfyUI product.

## Project status and license

The project is beta software. Prompt validation and backend lifecycle behavior are tested, but model outputs remain nondeterministic.

Licensed under [GPL-3.0-only](LICENSE).
