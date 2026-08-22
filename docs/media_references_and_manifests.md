# Media References, Manifests & Retention Analysis

This document describes how to connect, define, and validate multimodal reference assets (images, videos, and audio tracks) for MiniMax H3 Ref2VA workflows.

---

## Contents

- [Overview: Connecting Assets to H3](#overview-connecting-assets-to-h3)
- [Plain-Language Notes (`reference_context`)](#plain-language-notes-reference_context)
- [Structured Media Manifest JSON (`media_manifest`)](#structured-media-manifest-json-media_manifest)
- [Ref2VA Resource Envelopes & Quotas](#ref2va-resource-envelopes--quotas)
- [Subject Mapping & Full-Reference Semantics](#subject-mapping--full-reference-semantics)
- [Retention Analysis Markers](#retention-analysis-markers)
- [Media Manifest Validator Node](#media-manifest-validator-node)

---

## Overview: Connecting Assets to H3

The enhancer does not read pixel tensors directly; it receives metadata explaining to MiniMax H3 how connected assets should be utilized during generation:

1. **`reference_context`**: Quick, plain-text descriptions for manual node wiring.
2. **`media_manifest`**: Legacy manifests and versioned logical media projects for automated pipelines.

---

## Plain-Language Notes (`reference_context`)

For standard ComfyUI graphs, enter direct plain-text notes into `reference_context`:

```text
Picture 1 supplies the woman's facial identity and hair;
Picture 2 supplies the red leather jacket design;
Audio 1 supplies her Spanish speaking voice and cadence.
```

The enhancer parses these references and automatically constructs the official `subject_definitions:` and `retention_analysis:` blocks.

---

## Structured Media Manifest JSON (`media_manifest`)

For programmatic workflows or upstream vision analysis nodes, supply a structured JSON manifest:

The unversioned `items` form below remains byte-compatible for existing workflows. New projects should use
`schemaVersion: 2`; its normative Draft 2020-12 schema is
[`schemas/media_manifest_v2.schema.json`](schemas/media_manifest_v2.schema.json). V2 separates stable logical
asset IDs from generation-local physical labels, and adds subjects, appearance-state graphs, environments with
role-scoped views, temporary environment states, activation, bindings, and explicit carry/reset policies.

### Minimal Schema

```json
{
  "mode": "ref2va",
  "items": [
    {"type": "picture", "role": "identity", "analysis": "woman with brown curly hair"},
    {"type": "video", "role": "motion", "duration": 6, "audio_mode": "paired"},
    {"type": "audio", "role": "voice", "duration": 4,
     "transcript": {"language": "Spanish", "text": "Hola, ¿cómo estás?"}}
  ],
  "subjects": [
    {
      "id": 1,
      "description": "the same woman with brown curly hair",
      "sources": ["<Picture 1>", "<Video 1>"]
    }
  ]
}
```

### Manifest Fields Specification

| Field | Location | Description |
|---|---|---|
| `mode` | Root | Explicit mode token (`ref2va`, `t2va`, `i2va`, `fl2va`, `l2va`). |
| `items` | Root | Array of media assets. |
| `subjects` | Root | Authoritative many-to-many subject identity definitions. |
| `type` | Item | Asset type: `"picture"` (or `"image"`), `"video"`, or `"audio"`. |
| `role` | Item | Role string: `"identity"`, `"motion"`, `"style"`, `"first_frame"`, `"voice"`. |
| `duration_seconds` | Item | Duration in seconds (2–15s for video/audio). |
| `audio_mode` | Video Item | Soundtrack routing: `"off"` (default), `"paired"`, or `"alone"`. |
| `transcript` | Audio Item | Transcript string or object (`{"language": "...", "text": "..."}`). |
| `sources` | Subject | Assigned canonical labels (e.g. `["<Picture 1>", "<Video 1>"]`). |

### Logical project v2

Prompt Studio uses a two-step media workflow. **+ Add reference** registers a logical reference in the project
library; it stores metadata and never uploads or connects a file. The physical picture, video, or audio must be
connected in the generation node and assigned to that generation's binding. A logical record without a matching
physical binding is not presented to H3 as connected media.

Each v2 generation independently resolves an active dependency closure and an `inputMap`. A logical asset such
as `ana.identity` can therefore be `<Picture 1>` in one generation while that same physical slot is reused by a
different asset in another. Logical IDs are authoritative; `<Picture N>`, `<Video N>`, and `<Audio N>` are derived
labels, never persistent identity.

Activation may be `auto`, or `explicit` with logical roots. Required dependencies include subject identity
pictures, the source of the selected appearance state, selected environment views, and enabled video
soundtracks. Excluding a required dependency is an error. Every active asset needs exactly one binding and an
inactive asset cannot retain one. Slot collisions and per-generation H3 media quotas are validated
deterministically.

Appearance state inheritance and environment state inheritance are acyclic, have a maximum depth of eight, and
remain separate from permanent identity or geometry. The first generation cannot use `carry`; later generations
may carry, explicitly select, or reset to the declared base/default state. A discontinuous explicit selection
requires a reason.

Backend callers use `parse_media_project()` and `manifest_context_for_generation()`. The latter emits only the
active definitions and bindings for the requested generation, preventing reference bleed. `parse_media_manifest()`
and `manifest_context()` remain the legacy compatibility APIs.

---

## Ref2VA Resource Envelopes & Quotas

The Manifest Validator strictly enforces MiniMax H3's official reference envelope:

| Asset Type | Maximum Allowed Items | Duration Limits |
|---|---|---|
| **Pictures (`<Picture N>`)** | Max 9 images | N/A |
| **Videos (`<Video N>`)** | Max 3 videos | 2–15 seconds each (max 15s total) |
| **Audios (`<Audio N>`)** | Max 3 audio tracks | 2–15 seconds each (max 15s total) |
| **Total Media Files** | Max 12 files overall | Audio cannot be the sole reference modality |

*Note: Enabled video soundtracks (`audio_mode: "paired"` or `"alone"`) consume an `<Audio N>` index.*

---

## Subject Mapping & Full-Reference Semantics

MiniMax H3 separates reusable content from literal media files:

- **`<Subject N>`**: Represents reusable human identity, wardrobe, object design, style, or motion extracted from an asset (e.g. `<Subject 1> is the character from <Picture 1>`).
- **`<Picture N>`**: Declared independently only when the picture itself is a whole-frame composition anchor (first/last frame).
- **`<Video N>`**: Declared independently only for global video continuation or editing.
- **`<Audio N>`**: Represents an audio signal reference (voice clone reference or synchronized layer).

---

## Retention Analysis Markers

Every Ref2VA prompt includes a `retention_analysis:` block assigning an official marker to each reference:

| Reference Kind | Official Accepted Markers | Purpose |
|---|---|---|
| **Visual (`<Subject N>`, `<Picture N>`, `<Video N>`)** | `fully_preserved` | Keep exact identity, geometry, and design. |
| | `partially_preserved` | Preserve core identity while allowing wardrobe/action changes. |
| | `attribute_transfer` | Transfer specific traits (e.g. texture, color) onto another subject. |
| | `weak_reference` | Loose atmospheric or compositional inspiration. |
| **Audio (`<Audio N>`)** | `reference` | Use exclusively as voice-timbre and cadence reference for a character. |
| | `fully_copy` / `partially_copy` | Reusable synchronized diegetic audio track. |
| | `weak_reference` | Loose acoustic reference. |

---

## Media Manifest Validator Node

The **MiniMax H3 Media Manifest Validator** node validates manifests upstream before LLM execution. Legacy
manifests use the original compatibility checks; v2 projects use strict structural and cross-reference validation:

- Checks version, allowed fields, types and required fields.
- Validates media count and duration limits.
- Verifies subject-to-source label mappings.
- Outputs `manifest_is_valid` (boolean), `validated_manifest_json`, and detailed error logs.

For v2, normalized output must use the parser's `canonicalJson`, which contains only the supplied project data in
stable key order. Computed activation closures, physical maps, state resolutions, and digests are intentionally
not written back into the manifest.
