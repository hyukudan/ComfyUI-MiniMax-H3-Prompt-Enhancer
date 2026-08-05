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
- [Nodes](#nodes)
- [Exact wiring](#exact-wiring)
- [Prompt contracts](#prompt-contracts)
- [Dialogue, language, and exact text](#dialogue-language-and-exact-text)
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
| Feed duration downstream | `duration_seconds` output on both enhancer nodes |
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
5. Enter the endpoint and optionally an exact API model ID.
6. Connect `enhanced_prompt` to H3 conditioning and `duration_seconds` to the downstream duration control.

Loopback endpoints work by default. Sending prompts to another host requires `allow_remote_endpoint=true`.

### Local GGUF without LM Studio

1. Install a current official llama.cpp build containing `llama-server` or `llama-server.exe`.
2. Place one or more text-generation GGUF files in `ComfyUI/models/llm_gguf/`.
3. Restart ComfyUI or refresh node definitions.
4. Add **MiniMax H3 Prompt Enhancer** and set `use_remote_model=false`.
5. Select `local_model` and the detected `llama_server_path` from their dropdowns.
6. Leave `keep_server_loaded=false` when H3 needs the VRAM immediately afterward.

The frontend hides endpoint-only controls in local mode and hides GGUF-only controls in remote mode. It also refits the node so widgets and outputs remain inside its frame when old workflows are opened.

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
| `duration_seconds` | Unchanged requested duration for downstream wiring |

Shared controls:

| Control | Default | Behavior |
|---|---:|---|
| `mode` | `auto` | T2VA unless reference context contains H3 reference labels |
| `duration_seconds` | `5.0` | Constrains prompt timing and is forwarded as an output |
| `temperature` | `0.2` | Low variance for structured rewriting |
| `max_tokens` | `4096` | Completion budget |
| `repair_attempts` | `1` | Re-prompts with validator errors |
| `disable_thinking` | enabled | Requests direct structured output where supported |
| `use_remote_model` | enabled | Endpoint when enabled; local GGUF when disabled |

Remote-only controls include `endpoint`, `model`, `api_key`, and `allow_remote_endpoint`. Local-only controls include `local_model`, `llama_server_path`, `gpu_layers`, `context_size`, `threads`, `startup_timeout`, and `keep_server_loaded`.

Existing serialized workflows remain remote by default because `use_remote_model` defaults to enabled and the new output was appended after the three original outputs.

### MiniMax H3 GGUF Prompt Enhancer

The specialized direct-GGUF node exposes both model and runtime paths, extra registered model roots, GPU-layer offload, context, threads, timeouts, and the persistent-process toggle. It returns the same four outputs as the main enhancer.

Use it when you need custom paths or prefer a graph dedicated to GGUF. The main node is simpler for models under `ComfyUI/models/llm_gguf`.

### MiniMax H3 Unload GGUF Prompt Model

Stops the optional persistent prompt-model server and releases its RAM/VRAM. It is safe to queue when no persistent model is loaded.

### MiniMax H3 Prompt Guide Builder

Builds `system_prompt`, `user_prompt`, and `resolved_mode` without calling an LLM. Connect the two prompt outputs to an existing QwenVL, GGUF, Ollama, or other text-generation node, then validate its result.

### MiniMax H3 Prompt Validator

Validates enhanced or manually authored prompts without running an LLM. It checks section order, alignment instructions, shot numbering and timing, language-tagged dialogue, exact quoted content, reference labels, and full-reference definitions.

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
| `auto` | Conservative automatic choice | Ref2VA only when reference context contains an H3 label; otherwise T2VA |

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

Visible on-screen text is also preserved exactly, but it is not converted to dialogue unless the source contains a speech cue.

Quoted thoughts and internal monologue are treated as audible, non-lip-synced speech. The enhancer preserves the
exact words inside `<d>[Language] ...</d>`, describes them as an off-screen internal monologue, and explicitly keeps
the on-screen character's lips closed. If an explicit language is absent, conservative recognition handles clear
markers such as Spanish inverted punctuation and accented interrogatives; otherwise the non-translating
`[Original language]` marker is used.

## References

The enhancer cannot inspect attached images, video, or audio. Describe the assets passed downstream in `reference_context`:

```text
<Picture 1> is the exact person identity and wardrobe reference.
<Picture 2> is the exact product reference; preserve its shape, colors, controls, and markings.
```

Positional wording is supported generically: `image 1`, `imagen 1`, or `picture 1` maps to `<Picture 1>`; corresponding video and audio wording maps to `<Video N>` and `<Audio N>`. There is no scenario-specific production logic.

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

Reload the browser after updating the extension. The frontend recalculates the node size when it is created, configured, or switched between remote and local modes. Old saved dimensions are expanded automatically.

### GGUF reports an unsupported tensor type

Update llama.cpp. A new GGUF quantization may be newer than the selected runtime. This is one reason the extension does not pin an in-process `llama-cpp-python` wheel.

### GGUF enhancement is slower than LM Studio

Per-run mode includes process startup and model loading. Enable `keep_server_loaded` for repeated prompt iteration when sufficient VRAM is available, or use the already-running LM Studio endpoint.

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

Tests cover all H3 modes, timing, alignment, exact dialogue/language preservation, references, endpoint policy, repair, GGUF discovery, process isolation, persistent reuse, explicit unload, and failure cleanup.

Bug reports should include the ComfyUI version, extension commit, backend, model identifier, resolved mode, sanitized source prompt, and complete validation/error report. GGUF reports should also include the llama.cpp build and quantization. Never attach API keys or private reference content.

## Guide basis

The implementation is based on MiniMax's public base and full-reference Video Prompt Writing Guides. It is an original implementation and is not an official MiniMax or ComfyUI product.

## Project status and license

The project is beta software. Prompt validation and backend lifecycle behavior are tested, but model outputs remain nondeterministic.

Licensed under [GPL-3.0-only](LICENSE).
