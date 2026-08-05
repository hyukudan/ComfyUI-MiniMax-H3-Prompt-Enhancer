# ComfyUI MiniMax H3 Prompt Enhancer

Standalone ComfyUI nodes that rewrite a basic request into MiniMax H3's documented audiovisual prompt structures and validate the result before generation. The package does not depend on MiniMax Director and can be inserted into any native or custom MiniMax H3 workflow.

## Nodes

### MiniMax H3 Prompt Guide Builder

Produces the guide-specific `system_prompt` and `user_prompt` without loading or calling a model. This is the
interoperability path for existing ComfyUI LLM nodes: connect the outputs to their custom-system and prompt inputs,
then pass the generated text through the validator. It avoids another model dependency and lets a workflow reuse
QwenVL Prompt Enhancer, a GGUF loader, Ollama, or another text generator already present in ComfyUI.

### MiniMax H3 Prompt Enhancer

Calls any OpenAI-compatible chat endpoint and returns:

- `enhanced_prompt` — ready to connect to a MiniMax H3 prompt input.
- `validation_report` — structural errors and recommendations.
- `enhancement_manifest` — provider/model/mode settings without the API key.

Supported modes are `T2VA`, `I2VA`, `FL2VA`, `L2VA`, and full-reference `Ref2VA`. `auto` selects Ref2VA when the reference context contains an H3 reference label and otherwise selects T2VA.

The default endpoint is LM Studio at `http://127.0.0.1:1234/v1`. Leaving `model` blank ignores obvious embedding or
reranking models and prefers a compact instruct/chat model reported by `/v1/models`, avoiding accidental automatic
loading of a 30B model when a smaller model is available. Other local OpenAI-compatible servers can be used directly.
Remote endpoints are rejected unless `allow_remote_endpoint` is explicitly enabled. The API key can be supplied
through the node or `MINIMAX_H3_PROMPT_ENHANCER_API_KEY`.

`disable_thinking` is enabled by default. With LM Studio the node prefers its native `/api/v1/chat` endpoint and sends
`reasoning: off`; this prevents Qwen thinking models from spending the output budget before producing the actual
prompt. If that endpoint is unavailable, it falls back to OpenAI-compatible chat completions with the standard
`enable_thinking: false` chat-template option.

The enhancer preserves quoted dialogue and visible text, uses stable speaker/reference labels, enforces shot timing, separates diegetic sound from audience-only music, and performs one repair pass by default when validation fails.

## Local model guidance

The node does not bundle weights. For LM Studio, paste the model ID shown by its API into `model`, or leave it blank
to prefer a compact instruct model while excluding embedding/reranking entries.

- A 4B-class uncensored instruct model is the recommended interactive profile: low load time and enough instruction
  fidelity for the validator/repair loop.
- A 27B–35B model can improve difficult Ref2VA synthesis, but consumes substantially more memory and may take much
  longer to load. Thinking should remain disabled for structured prompt rewriting.
- Sub-1B models are useful for experimentation but commonly miss section, timing, or reference constraints.

MiniMax H3's own Qwen3-VL checkpoint is not a reusable chat model here. ComfyUI loads it as a truncated conditioning
encoder and does not expose a text-generation head; it can condition H3 but cannot author the prompt.

### MiniMax H3 Prompt Validator

Validates enhanced or manually authored prompts without an LLM call. It checks section order, alignment instructions, shot numbering and cut times, dialogue tags, quoted text preservation, reference labels, and the recommended Ref2VA description length.

## Installation

Clone this repository into `ComfyUI/custom_nodes`, then restart ComfyUI. There are no third-party Python dependencies.

```powershell
git clone https://github.com/hyukudan/ComfyUI-MiniMax-H3-Prompt-Enhancer.git
```

## Typical wiring

```text
basic prompt → MiniMax H3 Prompt Enhancer → MiniMax H3 conditioning prompt
                                      └──→ MiniMax H3 Prompt Validator (optional preview/gate)
```

Or reuse a pre-existing LLM node:

```text
basic prompt → MiniMax H3 Prompt Guide Builder → any local LLM node → MiniMax H3 Prompt Validator → H3
```

For full-reference mode, put the authoritative label definitions and asset roles in `reference_context`. The enhancer does not inspect image/video/audio pixels itself; it structures the information you provide.

## Guide basis

The implementation follows the public MiniMax H3 `Video Prompt Writing Guide (T2VA / I2VA / FL2VA / L2VA)` and `Full-Reference Mode Rewrite Output Format Guide`. Their rules are represented here as an original executable specification rather than copied documentation.

## Privacy and security

- Local loopback endpoints are allowed by default.
- Remote endpoints require explicit opt-in.
- API keys are never written to the manifest or logs.
- Prompt content is sent only to the endpoint selected in the node.

## License

GPL-3.0-only.
