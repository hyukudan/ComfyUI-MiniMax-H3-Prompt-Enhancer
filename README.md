# ComfyUI MiniMax H3 Prompt Enhancer

Guide-constrained prompt authoring and validation nodes for MiniMax H3 workflows in ComfyUI.

[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB.svg)](pyproject.toml)
[![Status: Beta](https://img.shields.io/badge/status-beta-orange.svg)](#project-status)

Turn a short request into MiniMax H3's documented audiovisual prompt structures, validate the result, or reuse the same guide with an LLM node you already have. The package is standalone: it does not require MiniMax Director and can be inserted into native or custom H3 workflows.

It does not bundle model weights, inspect reference pixels, or replace MiniMax H3 conditioning. It prepares text for the H3 prompt input.

## Contents

- [Why use it?](#why-use-it)
- [Quick start](#quick-start)
- [Nodes](#nodes)
- [Modes and output contracts](#modes-and-output-contracts)
- [References and exact content](#references-and-exact-content)
- [Model and endpoint selection](#model-and-endpoint-selection)
- [Installation](#installation)
- [Privacy and security](#privacy-and-security)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Project status and license](#project-status-and-license)

## Why use it?

MiniMax H3 responds best when visual action, timing, camera, dialogue and sound are expressed in the structure expected by the selected generation mode. This pack makes that structure explicit and machine-checkable.

| Need | What the pack provides |
|---|---|
| Rewrite a short idea | An OpenAI-compatible enhancer with optional repair passes |
| Reuse an existing LLM node | A guide builder that outputs separate system and user prompts |
| Check hand-written text | A model-free validator with structured errors and recommendations |
| Preserve exact content | Quoted dialogue, lyrics and visible text are carried as protected content |
| Keep references stable | Positional image/video/audio references become H3 labels without scenario-specific logic |
| Keep local prompts local | Loopback endpoints are allowed by default; remote endpoints require explicit opt-in |

The validator catches structural mistakes; it cannot guarantee visual quality, identity fidelity, physical correctness or that the diffusion model will follow every instruction.

## Quick start

1. Install the custom node and restart ComfyUI.
2. Start an OpenAI-compatible chat server such as LM Studio. The default endpoint is `http://127.0.0.1:1234/v1`.
3. Add **MiniMax H3 Prompt Enhancer** from `MiniMax H3 → Prompting`.
4. Enter a `basic_prompt`, choose the H3 mode, and set the intended duration.
5. For Ref2VA, define the available labels and their roles in `reference_context`.
6. Connect `enhanced_prompt` to the prompt input used by your H3 conditioning node.
7. Inspect `validation_report`. A green structural result is a gate, not a quality guarantee.

Typical direct wiring:

```text
basic prompt → MiniMax H3 Prompt Enhancer → H3 conditioning prompt
                                      ├──→ validation_report
                                      └──→ enhancement_manifest
```

To reuse another text-generation node:

```text
basic prompt → Prompt Guide Builder → existing LLM node → Prompt Validator → H3
```

## Nodes

### MiniMax H3 Prompt Enhancer

Calls an OpenAI-compatible chat endpoint and returns:

| Output | Meaning |
|---|---|
| `enhanced_prompt` | Normalized prompt ready for the selected H3 conditioning mode |
| `validation_report` | Resolved mode, validity, structural errors and recommendations |
| `enhancement_manifest` | Provider/model/mode and repair metadata; never contains the API key |

Important controls:

| Control | Default | Behavior |
|---|---:|---|
| `endpoint` | `http://127.0.0.1:1234/v1` | OpenAI-compatible API root |
| `model` | blank | Discovers models and prefers a compact instruct/chat entry |
| `temperature` | `0.2` | Low variance for structured rewriting |
| `max_tokens` | `4096` | Output budget for the completed prompt |
| `timeout_seconds` | `300` | Network/model timeout |
| `repair_attempts` | `1` | Re-prompts the model with validator errors, up to two times |
| `disable_thinking` | enabled | Requests non-reasoning output where the endpoint supports it |
| `allow_remote_endpoint` | disabled | Required before sending content beyond the local machine |

The node is deliberately marked as changed on each queue so prompt enhancement is not silently reused from an old ComfyUI execution cache.

### MiniMax H3 Prompt Guide Builder

Builds `system_prompt`, `user_prompt` and `resolved_mode` without calling a model. Use it with QwenVL/GGUF nodes, Ollama, LM Studio integrations or another text-generation node already installed in ComfyUI.

The builder is the best choice when you want to control model loading elsewhere in the graph or avoid a second API client.

### MiniMax H3 Prompt Validator

Validates enhanced or manually authored prompts without an LLM call. It checks:

- required section names and order;
- first/last-frame alignment instructions;
- sequential shot numbering and increasing cut times;
- dialogue tags and preservation of quoted content;
- declared reference labels;
- Ref2VA description structure and recommended detail.

It returns the original `prompt`, a Boolean `valid`, and a JSON `validation_report`. Connect `valid` to your own workflow gate if desired.

## Modes and output contracts

| Mode | Intended use | Required structure |
|---|---|---|
| `T2VA` | Text-to-video with native audio | Three-section base format |
| `I2VA` | First-frame-guided generation | Alignment instruction plus base format |
| `FL2VA` | First- and last-frame-guided generation | Dual alignment instruction plus base format |
| `L2VA` | Last-frame-guided generation | Final-frame alignment plus base format |
| `Ref2VA` | Full multimodal reference generation | Six-section reference format |
| `auto` | Conservative automatic choice | Ref2VA only when `reference_context` contains an H3 reference label; otherwise T2VA |

Base modes use these sections in order:

```text
integrated_multimodal_description:
overall_soundscape:
non_diegetic_music:
```

Ref2VA uses:

```text
subject_definitions:
summary:
retention_analysis:
detailed_description:
overall_soundscape:
non_diegetic_music:
```

`duration_seconds` constrains cut timestamps; it does not change the frame count in your generation workflow. Configure the H3 latent/video length separately.

## References and exact content

The enhancer cannot see attached images, videos or audio. `reference_context` must describe the labels that the downstream H3 node will actually receive.

Example:

```text
<Picture 1>: identity and clothing reference for the presenter.
<Picture 2>: exact product design and markings.
<Audio 1>: the presenter's vocal identity and delivery reference.
```

Then a basic request may say:

```text
The person in image 1 presents the object in image 2 and says "Here it is."
```

Positional references are generic bindings, not hard-coded objects: `image 1` maps to `<Picture 1>`, `video 2` to `<Video 2>`, and `audio 1` to `<Audio 1>`. The implementation contains no production logic for any particular weapon, character or test scene.

Quoted dialogue, lyrics and visible text are preserved rather than translated or paraphrased. The LLM can still make mistakes; always inspect the enhanced prompt and validator output before an expensive render.

## Model and endpoint selection

### LM Studio

The default works with LM Studio's local API:

```text
http://127.0.0.1:1234/v1
```

When `disable_thinking` is enabled, the client first tries LM Studio's native chat route with reasoning disabled and falls back to `/v1/chat/completions` with `enable_thinking: false`.

Leaving `model` blank queries `/v1/models`, excludes obvious embedding/reranking entries and prefers a compact instruct/chat model. This is convenient, but explicit model selection is recommended for reproducible workflows.

### Choosing a model

- A capable 4B-class instruct model is the recommended interactive starting point.
- A 27B–35B model may improve difficult Ref2VA synthesis but loads more slowly and uses substantially more memory.
- Sub-1B models frequently miss sections, reference constraints or exact dialogue.
- Uncensored/abliterated variants may reduce refusals but can also reduce instruction fidelity; validation remains necessary.

MiniMax H3's own Qwen3-VL checkpoint cannot be reused as the chat model here. ComfyUI loads a truncated conditioning encoder without a text-generation head.

Any OpenAI-compatible server can be used. Remote servers are blocked until `allow_remote_endpoint` is enabled.

## Installation

### Git

From `ComfyUI/custom_nodes`:

```bash
git clone https://github.com/hyukudan/ComfyUI-MiniMax-H3-Prompt-Enhancer.git
```

Restart ComfyUI. The nodes appear under `MiniMax H3 → Prompting`.

The project is public on GitHub but is not yet published in the Comfy Registry. Until a Registry package exists, use Git or ComfyUI Manager's **Install via Git URL** function.

### Requirements

- Python 3.10 or newer.
- A current ComfyUI installation.
- No additional Python packages for the node pack itself.
- A reachable chat endpoint only when using **Prompt Enhancer**. **Guide Builder** and **Validator** work offline.

### Update

```bash
git -C ComfyUI-MiniMax-H3-Prompt-Enhancer pull --ff-only
```

Restart ComfyUI after updating. Back up important workflows before changing versions.

### Uninstall

Stop ComfyUI and remove the `ComfyUI-MiniMax-H3-Prompt-Enhancer` directory. Existing workflow JSON files are not deleted, but ComfyUI will report the three node types as missing until the pack is reinstalled or those nodes are replaced.

## Privacy and security

- Loopback hosts are allowed by default.
- Remote hosts require `allow_remote_endpoint=true`.
- Enabling remote access sends `basic_prompt`, `reference_context` and the generated guide to that endpoint.
- API keys are used only in request headers and are excluded from manifests and logs.
- The node inherits ComfyUI's network/authentication boundary. Do not expose an unauthenticated ComfyUI instance to an untrusted network.
- Remove private prompts, paths, endpoints and keys from workflows and bug reports.

## Troubleshooting

### No model is selected

Enter the exact model ID reported by your server's `/v1/models` endpoint. Automatic selection intentionally ignores embedding and reranking models.

### The model spends the output budget thinking

Keep `disable_thinking` enabled. If the server ignores the request, use a non-thinking instruct model or configure the server's chat template directly.

### The validator rejects an otherwise good prompt

Read `validation_report` before increasing `repair_attempts`. Common causes are missing colons, reordered sections, timestamps outside the requested duration, undeclared reference labels or changed quoted text.

### Image/video/audio references are ignored

The node does not inspect media or create ComfyUI reference connections. Declare the actual downstream H3 labels in `reference_context`, and ensure the corresponding media are connected to the H3 conditioning workflow.

### HTTP 401, 404 or timeout

- Confirm the endpoint root and API key.
- Verify `/v1/models` and `/v1/chat/completions` are exposed.
- Increase `timeout_seconds` for a model that is still loading.
- For a remote host, enable `allow_remote_endpoint` only after reviewing its privacy policy.

## Development

Run the test suite from the repository root:

```bash
python -m pytest -q
```

The suite covers modes, normalization, positional-reference preservation, dialogue/text retention, endpoint policy, model selection and repair behavior.

Bug reports should include the ComfyUI version, node-pack commit, endpoint type, selected model, resolved mode, sanitized input and the complete validation/error report. Do not attach API keys or private reference content.

## Guide basis

The rule set is an original executable specification derived from MiniMax H3's public base-mode and full-reference prompt-writing guides. It does not copy those documents verbatim. See the [ComfyUI MiniMax H3 documentation](https://docs.comfy.org/tutorials/video/minimax/minimax-h3) and [official H3 weights repository](https://huggingface.co/Comfy-Org/MiniMax-H3) for the surrounding model workflow.

## Project status and license

Version `0.1.0` is a tested Beta. The documented node/output names are stable for existing workflows, but validation rules may become stricter as the public H3 guidance evolves.

Source code is licensed under [GPL-3.0-only](LICENSE). Model weights are not bundled and remain subject to their upstream licenses. This independent project is not affiliated with or endorsed by MiniMax, Comfy Org, LM Studio or any referenced model provider.
