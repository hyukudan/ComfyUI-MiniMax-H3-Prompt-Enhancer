# Cinematic Titles & Credits

The **MiniMax H3 Prompt Enhancer** includes a deterministic titles-and-credits director. It turns a concept, exact text and one coherent material recipe into a timed H3 briefing, then restores a strict text lock after LLM enhancement so the requested strings remain authoritative.

## Quick start

1. Add **MiniMax H3 Prompt Enhancer**.
2. Choose `auto`, `t2va`, or a reference mode. Do not use `chained_multishot` for a title sequence.
3. Set **Titles & Credits recipe** to anything except `none`.
4. Choose **Title energy**: `restrained`, `balanced`, or `spectacular`.
5. Enter **Exact main title** and/or **Credit cards**.
6. Choose whether the main title appears before or after the credits.
7. Give the sequence enough duration for formation and readable holds.

Example:

```text
Basic prompt:
A mysterious premium archive in midnight blue and warm brass.

Exact main title:
THE SIGNAL

Credit cards:
A FILM BY | MALAK
MUSIC BY | ANA TORRES
```

## Credit syntax

Each non-empty line creates one card.

```text
DIRECTED BY | MALAK
ANA TORRES
```

- `Role | Name` creates a hierarchical card and holds both strings together.
- A line without `|` creates a single-level credit.
- Empty text on either side of `|` is rejected.
- Title line breaks create one stacked title composition and are preserved exactly.
- A main title may contain at most four lines.

Quotation marks shown in the generated briefing delimit exact text; they are not rendered. Case, punctuation, accents and intentional title line breaks remain locked.

## Recipes

| Recipe | Production system |
|---|---|
| **Auto director** | Derives one coherent material, stage, typography, camera, light and sound system from the concept. |
| **Prestige imprint** | Embossing, debossing or foil stamping revealed by a physical press and raking light. |
| **Precision apparatus** | Indexed shutters, plates or machined components lock into exact glyph geometry. |
| **Analog print lab** | Exposure, emulsion, contact sheets, registration and practical print processes. |
| **Unearthed archive** | Exact inscriptions uncovered beneath dust, salt, ash, oxidation or patina. |
| **Optical luxury** | Mirrors, prisms, glass, caustics and refraction align into precise lettering. |
| **Living material** | One coherent organic, liquid, particulate, atmospheric or geological material forms every card. |

Every recipe follows the same guardrails: incomplete shapes remain abstract, wrong letters and fake words never cycle before the reveal, and completed lettering becomes still and readable.

## Timing and readability

The planner calculates, for every card:

1. Formation.
2. Settle time for camera and material motion.
3. A completely still readable hold.
4. A causal transition, except after the final card.

The final composition remains through the last frame. If the requested cards cannot fit, the node raises an actionable error telling you to increase duration, remove a card, shorten a line, add intentional title line breaks, or use a wider aspect ratio.

Narrow formats use stricter line-length limits. Text is never abbreviated or automatically rewrapped to make an invalid request appear valid.

## Interaction with the LLM

The node first creates a deterministic production briefing containing the exact cards and timed storyboard. The selected remote or local LLM expands the visual direction. After enhancement, the node appends the exact text lock again. This final lock overrides conflicting generated text and forbids extra signage, captions, dates, logos, signatures, watermarks or invented writing.

The output manifest includes:

```json
{
  "titleSequence": {
    "recipe": "Precision apparatus",
    "energy": "balanced",
    "cardCount": 3
  }
}
```

## Modes and compatibility

- Supported: `auto`, `t2va`, `i2va`, `fl2va`, `l2va`, and `ref2va` when their ordinary requirements are satisfied.
- Not supported: `chained_multishot`. It returns a JSON array of independent prompts and cannot safely carry one sequence-wide exact-text lock.
- Leaving **Titles & Credits recipe** at `none` preserves the existing prompt path exactly.

## Running all seven recipes locally

The repository includes `tools/run_title_recipe_workflows.py`. It queues the seven recipes sequentially against a running ComfyUI instance and waits for each render to finish before starting the next:

```bash
python tools/run_title_recipe_workflows.py --server http://127.0.0.1:8188
```

Use `--start 4` to resume at the fourth recipe. The script expects the local API workflow documented in its `WORKFLOW` constant; adjust that path if your workflow library is stored elsewhere.
