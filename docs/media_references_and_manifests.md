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
2. **`media_manifest`**: Strict, typed JSON for automated pipelines and programmatic workflows.

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

The **MiniMax H3 Media Manifest Validator** node validates JSON manifests upstream before LLM execution:

- Checks schema version and type correctness.
- Validates media count and duration limits.
- Verifies subject-to-source label mappings.
- Outputs `manifest_is_valid` (boolean), `validated_manifest_json`, and detailed error logs.
