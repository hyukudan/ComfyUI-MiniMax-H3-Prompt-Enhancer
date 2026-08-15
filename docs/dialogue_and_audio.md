# Dialogue, Multilingual Speech & Audio Architecture

This document details the multilingual dialogue engine, speech extraction rules, audio reference binding, and acoustic sound policies for MiniMax H3.

---

## Contents

- [The Mandatory Dialogue Contract](#the-mandatory-dialogue-contract)
- [Multilingual Engine & Regional Dialects](#multilingual-engine--regional-dialects)
- [Visible On-Screen Text vs. Spoken Dialogue](#visible-on-screen-text-vs-spoken-dialogue)
- [Speaker IDs & Vocal Attribution](#speaker-ids--vocal-attribution)
- [Cross-Modal Audio References (`<Audio N>`)](#cross-modal-audio-references-audio-n)
- [Advanced Dialogue Markers (`<scenetrans>`, `<cutoff>`)](#advanced-dialogue-markers-scenetrans-cutoff)
- [Audio Policies](#audio-policies)
  - [Ambience & Foley](#ambience--foley)
  - [Background Instrumental Score](#background-instrumental-score)
  - [Voice Performance Modes](#voice-performance-modes)
  - [Acoustic Space](#acoustic-space)
  - [Dialogue Coverage](#dialogue-coverage)

---

## The Mandatory Dialogue Contract

MiniMax H3 requires spoken content to be wrapped inside a canonical dialogue tag:

```text
The woman (S1) speaks warmly: <d>[Spanish] Hola, ¿cómo estás hoy?</d>.
```

### Core Invariants

1. **Verbatim Preservation**: Spoken quotes from the source prompt are copied 100% verbatim into the target prompt—without translation, paraphrase, censorship, or softening.
2. **Language Tagging**: Every `<d>` tag must start with an official canonical English language name in brackets, e.g. `<d>[Spanish] ...</d>`, `<d>[French] ...</d>`, `<d>[German] ...</d>`, `<d>[Japanese] ...</d>`.
3. **Zero Deprecated Tags**: Legacy or ambiguous tags like `[Original language]` or `[Language]` are automatically resolved to their true detected language or widget override.
4. **Single Timeline Occurrence**: Each source dialogue quote occurs exactly once in the visual timeline.

---

## Multilingual Engine & Regional Dialects

The built-in language detection engine identifies 18+ canonical languages and dozens of regional variants, dialects, and unaccented inputs:

| Canonical H3 Language | Supported Regional Aliases & Dialect Phrases |
|---|---|
| **Spanish** | `castilian`, `castellano`, `español de españa`, `español latino`, `latinoamericano`, `mexican`, `argentino`, `colombiano`, `andaluz` |
| **Catalan** | `català`, `valenciano`, `valencià`, `balear`, `mallorquín` |
| **French** | `français`, `québécois`, `canadian french`, `belgian french`, `suisse romand` |
| **German** | `deutsch`, `austrian german`, `österreichisches deutsch`, `swiss german`, `schweizerdeutsch` |
| **Portuguese** | `português`, `português do brasil`, `brazilian portuguese`, `português europeu` |
| **Dutch** | `nederlands`, `flemish`, `vlaams`, `belgian dutch`, `hollands` |
| **Italian** | `italiano`, `siciliano`, `napoletano` |
| **Chinese** | `mandarin`, `putonghua`, `simplified chinese`, `traditional chinese`, `guoyu` |
| **Cantonese** | `yue`, `cantonés`, `guangdonghua`, `hong kong cantonese` |
| **Japanese** | `nihongo`, `japanese` |
| **Korean** | `hangul`, `korean` |
| **Russian** | `русский`, `russian` |
| **Arabic** | `العربية`, `standard arabic`, `egyptian arabic`, `levantine arabic` |
| **Hindi** | `हिन्दी`, `hindi`, `hindustani` |
| **Turkish** | `türkçe`, `turkish` |
| **Polish** | `polski`, `polish` |
| **English** | `english`, `british english`, `american english`, `australian english` |

### Dialogue Language Widget

All prompt enhancer and validator nodes include a `dialogue_language` widget:
- `auto` (default): Automatically detects language from the prompt text, speech cues, or quote contents.
- `[Explicit Language]`: Forces a specific language tag for newly authored or resolved dialogue lines.

---

## Visible On-Screen Text vs. Spoken Dialogue

A crucial distinction in the enhancer is separating **on-screen visual text** from **spoken character speech**:

- **Visual Text (Signs, Doors, Titles, Labels, Clothes)**: Phrases like `a title card on the door saying "XYZ bar"` or `a hammer with "1T" written on it` are preserved as regular double-quoted text:
  ```text
  A large title card above the door reads "XYZ bar".
  A heavy wooden hammer with "1T" written on it appears...
  ```
  They are **never** wrapped in `<d>` tags, avoiding phantom speaker attribution and audio sync errors.
- **Spoken Speech (Dialogue)**: Phrases preceded by speech verbs (`says`, `asks`, `dice`, `grita`, `dit`, `sagt`, `zegt`...) attached to living characters are wrapped in `<d>[Language] ...</d>`.

---

## Speaker IDs & Vocal Attribution

Every audible speaking character receives a stable speaker identifier: `(S1)`, `(S2)`, `(S3)`...

1. **Visible Dialogue**: The character ID, vocal verb, delivery description, and `<d>` tag reside in the same sentence:
   ```text
   The detective (S1) replies firmly: <d>[English] We need to leave now.</d>.
   ```
2. **Off-Screen Voiceover / Narration**:
   ```text
   <Subject 1> (S1) says in an off-screen voiceover: <d>[Spanish] Todo comenzó aquella noche...</d>, while his on-screen lips remain completely closed.
   ```
3. **Internal Monologue**: Treated as audible off-screen voiceover while keeping the on-screen character's lips closed.

---

## Cross-Modal Audio References (`<Audio N>`)

MiniMax H3 Ref2VA supports cross-modal reference pairing where an `<Audio N>` file provides the vocal timbre, delivery, and rhythm for an on-screen character:

### 1. Voice Timbre Reference (Vocal Cloning)
When natural phrasing binds an audio track to a character (e.g. `"la mujer habla con la voz de audio 1"`, `"el personaje de imagen 1 usa el audio 1 para su voz"`, `"the man in image 2 with voice from audio 2"`):

- **Subject Definition**:
  ```text
  <Audio 1> is the supplied audio signal used exclusively as the voice-timbre and delivery reference for <Subject 1> (S1)'s newly generated dialogue; its original words and unrelated sounds are not copied.
  ```
- **Retention Analysis**: `<Audio 1>: reference`
- **Timeline Binding**: Links `<Audio 1>` to `<Subject 1> (S1)`. Newly generated dialogue in `<d>` will render in the voice of `<Audio 1>`.

### 2. Synchronized Audio Layer (Audio Copying)
When the prompt asks to copy, reuse, or pair an exact audio track (`"copy audio 1"`, `"reutiliza el audio 1"`):
- **Retention Analysis**: `<Audio 1>: partially_copy` or `fully_copy`
- **Timeline Binding**: Attributed directly to `<Audio 1>` as a synchronized diegetic layer.

---

## Advanced Dialogue Markers (`<scenetrans>`, `<cutoff>`)

- **`<scenetrans>` (Dialogue across cuts)**: When one sentence crosses a cut boundary, keep the full line in a single `<d>` block in the shot where it begins. Place `<scenetrans>` outside `<d>` at the connecting point in both shots, with a continuity statement:
  ```text
  [Shot 1] The speaker (S1) says <d>[English] We must move quickly before...</d> <scenetrans> as the audio continues seamlessly across the cut.
  [Shot 2] At 00:03.000, <scenetrans> The camera cuts to the hallway while the speech continues uninterrupted into the next shot.
  ```
- **`<cutoff>` (Interrupted final speech)**: Placed inside the final `<d>` block when the video ends before an utterance finishes:
  ```text
  The speaker (S1) shouts: <d>[English] Look out behind you<cutoff></d>.
  ```

---

## Audio Policies

The three audio gates operate independently across all enhancer and validator nodes:

### Ambience & Foley
- `auto`: Naturally describes environmental and physical sounds implied by the scene.
- `ensure_audible`: Explicitly mandates concrete physical contact sounds, footsteps, and room acoustics.
- `off`: Suppresses all ambient and foley audio.

### Background Instrumental Score
- `follow_prompt`: Adds score only if requested in the source prompt.
- `add_instrumental`: Enforces a dedicated non-diegetic score block from 24 curated musical styles (`cinematic_orchestral`, `hybrid_orchestral_electronic`, `action_cinematic`, `synthwave`, `jazz`, `horror_tension`, `chinese_martial_arts`, `chiptune_16bit`...).
- `off`: Outputs `non_diegetic_music: N/A`.

### Voice Performance Modes
- `audible`: Normal mode preserving verbatim speech in `<d>[Language] ...</d>`.
- `silent_mouth_acting_experimental`: Strips `<d>` blocks and directs silent, natural lip and jaw articulation matching spoken cadence.
- `none`: Suppresses all speech and vocal performance.

### Acoustic Space (`acoustic_space`)
Shapes the physical reverberation profile generated natively by MiniMax H3:
- `small_reflective_interior`: Short bright early reflections, close localized foley.
- `large_reverberant_interior`: Long decaying tail, distant perspective on voices and impacts.
- `damped_interior`: Soft furnished room, absorbed highs, intimate close sound.
- `open_exterior`: Wide exterior, no room tail, natural distance attenuation.

### Dialogue Coverage (`dialogue_coverage`)
When set to `on`, mandates that each speaking character's mouth and eyes remain unobstructed and in sharp focus at medium close-up or tighter during their line, maximizing lip-sync fidelity.
