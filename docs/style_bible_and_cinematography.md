# Style Bible, Creative Treatments & Cinematography Guide

This document provides the complete specification for 125 curated creative treatments, 13 cinematography dimensions, conflict resolution precedence, and the explicit shot-plan editor for MiniMax H3.

---

## Contents

- [The Style Bible Architecture](#the-style-bible-architecture)
- [How Styles are Expanded for the Diffusion Model](#how-styles-are-expanded-for-the-diffusion-model)
- [Visual Language Catalog (61 Profiles)](#visual-language-catalog-61-profiles)
- [World Aesthetic Catalog (20 Profiles)](#world-aesthetic-catalog-20-profiles)
- [Mood Catalog (tone, 18 Profiles)](#mood-catalog-tone-18-profiles)
- [Narrative Genre Catalog (12 Profiles)](#narrative-genre-catalog-12-profiles)
- [Content Format Catalog (18 Profiles)](#content-format-catalog-18-profiles)
- [13-Dimensional Cinematography Controls](#13-dimensional-cinematography-controls)
- [Precedence & Conflict Resolution Engine](#precedence--conflict-resolution-engine)
- [Explicit Shot-Plan Editor](#explicit-shot-plan-editor)

---

## The Style Bible Architecture

Rather than passing raw preset names or abstract keywords (which AI diffusion models often misunderstand or over-generalize), the enhancer translates selections into an executable **Physical Production Bible** across 8 tangible dimensions:

```
Creative Preset Selection
 ├── 1. Production Design & Materials (Fabric weave, metal specularity, surface wear)
 ├── 2. Lighting & Colorimetry        (Motivated key light, shadow falloff, contrast curve)
 ├── 3. Camera & Framing             (Lens focal length, spatial depth, perspective)
 ├── 4. Editing & Pacing              (Action-reaction cadence, anticipation, hold times)
 ├── 5. Blocking & Performance        (Eyelines, physical weight transfer, micro-expressions)
 ├── 6. Permitted Sound Treatment     (Room acoustics, direct sound, diegetic foley)
 ├── 7. Safe Unspecified Fill        (Allowable background atmosphere)
 └── 8. Forbidden Inventions         (Strict guards against unrequested cliché props/VFX)
```

The compiled result is injected as a **Canonical Resolved Presentation Signature** directly into the prompt description.

---

## How Styles are Expanded for the Diffusion Model

MiniMax H3 responds to concrete physical descriptors rather than abstract labels:

- **Instead of `"cyberpunk"`**, it receives:  
  *“High-tech/low-life material contrast, repaired surfaces, modular infrastructure, signage density, and visible utility systems when unspecified and compatible.”*
- **Instead of `"cinematic live action"`**, it receives:  
  *“Composed live-action cinematography with intentional shot scale, stable screen direction, controlled foreground and background depth, natural key-to-fill falloff, and protected skin tones.”*
- **Instead of `"anime retro"`**, it receives:  
  *“Late-1970s-to-1980s Japanese cel animation with decisive key poses, sparse controlled in-betweens, angular interior facial lines, and two- or three-band hard-edged cel shadows.”*

---

## Visual Language Catalog (61 Profiles)

Visual Language describes rendering and production vocabulary; it does not imply narrative Genre or scene-wide Mood. The Studio groups choices by broad family, era/technique, and variant. Names remain brand-safe: they describe periods and craft instead of studios, artists, franchises, or look-alike substitutes. Every profile carries a `must_not_invent` guard so the rendering choice cannot add its usual subject matter, plot, dialogue, or audio.

| ID | Description |
|---|---|
| `live_action_cinematic` | Composed 35mm live-action craft with deliberate narrative coverage, natural key-to-fill falloff, protected skin tones, and physical camera operation. |
| `live_action_naturalistic` | Unadorned realist cinematography with truthful white balance, available light response, and unobtrusive camera placement. |
| `1970s_new_hollywood` | Location-shot 35mm American drama with longer-lens observation, slow motivated zooms, window halation, and warm Eastman negative grain. |
| `live_action_gritty` | Raw practical illumination, tactile high-texture surfaces, sharp shadow edges, and street-level handheld energy. |
| `giallo` | Theatrical primary lighting (crimson reds, cobalt blues, acid yellows), sharp motivated chiaroscuro, canted angles, and severe close framing. |
| `storybook_symmetrical` | Planimetric one-point perspective, plumb verticals, level horizontals, axial symmetry, balanced lateral tableaux, and flat color fields. |
| `documentary_observational` | Unobtrusive shoulder-height camera, available practical lighting, natural spatial geography, and continuous real-time pacing. |
| `surveillance_found_footage` | Wide-angle slightly distorted fixed lens, high mounted viewpoint, available-light limits, and flat compressed contrast. |
| `home_camcorder_1990s` | Consumer small-sensor deep focus, handheld micro-jitter, hunting autofocus, abrupt motorized zooms, and analog video color bleed. |
| `live_action_midcentury_technicolor_epic` | Saturated three-strip dye-transfer palette (emerald greens, crimson reds), broad proscenium staging, and high-key studio light. |
| `live_action_classic_black_and_white` | Panchromatic tonal scale with deep blacks, luminous mid-greys, hard key light, and crisp rim highlights. |
| `anime_shonen` | Hand-authored 2D action anime with clean cel fills, decisive contours, model-sheet construction, and anticipation-action-impact rhythm. |
| `anime_ultradetailed_cinematic` | High-density feature-animation layouts with exact perspective, deep multi-plane staging, and complex painted background transitions. |
| `anime_retro_dramatic` | Serious 1970s–80s cel animation with angular facial lines, hard-edged shadow bands, and disciplined key poses. |
| `vintage_rubberhose_2d` | Early theatrical ink-and-cel construction with rounded graphic forms, variable contours, and readable elastic spacing. |
| `cable_angular_graphic_comedy` | Late-1990s-to-2000s angular television graphics with flat saturated shapes, selective replacement drawings, and dry holds. |
| `contemporary_vector_2d` | Contemporary Bézier-authored animation with modular articulation, crisp scalable edges, controlled easing, and layered vector depth. |
| `manga_monochrome_print` | Monochrome ink, screentone, hatching, and white-space composition adapted to stable moving illustration without page furniture. |
| `anime_1960s70s_limited_cel` | Early Japanese television cel with a short palette, economical model sheets, purposeful body holds, and selective facial replacement. |
| `mecha_super_robot_cel` | Classic mechanical cel vocabulary applied only when supplied machinery exists, with legible joints, bold silhouettes, and strict no-invention guards. |
| `anime_ova_mechanical_detail` | 1980s OVA-like fine line hierarchy, multi-band cel shadows, material detail, and controlled high-detail redraws. |
| `anime_1990s_broadcast_cel` | Late broadcast cel, warm telecined color, airbrushed background transitions, compact shadow bands, and economical replacement drawings. |
| `anime_digital_compositing` | Contemporary digital anime linework, controlled gradients, painted layers, and restrained 2.5D parallax without gratuitous particles or glow. |
| `pixel_art_16bit` | Native integer-grid pixel art with hard nearest-neighbor clusters, indexed palette, and grid-aligned motion. |
| `stop_motion_handcrafted` | Physical handcrafted animation with miniature-scale optics, tactile clay/silicone/fabric textures, and replacement-like timing. |
| `rotoscope_animation` | Animation traced over filmed live action: natural human weight under a boiling line with flat painted fills. |
| `painterly_2d` | Hand-painted hand-authored 2D animation with visible brushwork, painted depth planes, and pigment-like color relationships. |
| `watercolor_2d` | Luminous translucent washes, visible paper tooth, granulation, soft edges, and airy depth. |
| `cel_shaded_3d` | Stable modeled 3D with clean two/three-band toon shading, attached outlines, and volumetric parallax. |
| `clean_commercial` | Premium exposure, precise hierarchy, stable product geometry, and controlled specular highlights. |

*(Includes additional specialized profiles such as `tokusatsu_sentai`, `kaiju_suitmation`, `supermarionation`, `graphic_noir`, `low_poly_3d`, etc.)*

---

## World Aesthetic Catalog (20 Profiles)

- `cyberpunk`: Layered infrastructure, modular repaired surfaces, signage density, and practical screen illumination.
- `film_noir`: Geometric depth, reflections, motivated chiaroscuro, and contained performance.
- `nordic_noir`: Functional modernity, pale matte materials, low-angle daylight, clean geometry, and quiet ambience.
- `solarpunk`: Climate-responsive, repairable design, natural wood/metal finishes, and integrated daylight.
- `steampunk`: Period mechanical mechanisms, brass/iron fasteners, gauges, and effortful mechanical operation.
- `dieselpunk`: Interwar riveted steel plates, cast housings, art-deco stepped geometry, and heavy fabrics.
- `retrofuturism_cassette`: Modular 1970s–80s tactile cassette-futurist vocabulary, CRT displays, and physical switches.
- `retrofuturism_y2k`: Late-1990s translucent plastics, rounded metallic edges, and cyber-aesthetic styling.
- `liminal_institutional`: Maintained institutional corridors, even overhead fluorescent lighting, and reverberant building ambience.
- `urban_industrial`, `post_apocalyptic`, `high_fantasy`, `gothic`, `historical_period`, `science_fiction`, `near_future_functional`, etc.

---

## Mood Catalog (tone, 18 Profiles)

Mood is scene-wide: it shapes staging, camera, light, performance, and mix without adding facts or dialogue. It is separate from **Delivery** and **Voice color**, which describe how one quoted line sounds in the node's prompt toolbar.

`epic`, `intimate`, `dark`, `tense`, `hopeful`, `melancholic`, `playful`, `restrained`, `serene`, `eerie`, `whimsical`, `surreal`, `clinical`, `raw`, `kinetic`, `pulp_heightened`, `stoic`, `none`.

In Prompt Studio, Mood is a searchable combobox grouped by meaning: **Energy & scale**, **Warmth & play**, **Closeness & feeling**, **Weight & unease**, and **Restraint & precision**. Each result carries a short guardrail description; the footer repeats that Mood never adds facts, dialogue, or music. The stored key and tokens remain unchanged, including `pulp_heightened`, whose UI label is **Heightened (pulp)**. Unknown future tokens remain visible and untouched until the user explicitly chooses another value.

---

## Narrative Genre Catalog (12 Profiles)

`action`, `horror`, `thriller`, `romance`, `comedy`, `drama`, `adventure`, `mystery`, `crime`, `western`, `sports_competition`, `none`.

---

## Content Format Catalog (18 Profiles)

`narrative_animation_short`, `opening_title_sequence`, `brand_promo`, `co_op_game_intro`, `handdrawn_live_fusion`, `minimalist_product_ad`, `lyric_music_video`, `progressive_metaphor_explainer`, `mechanism_explainer`, `general_educational_explainer`, `product_demo_tutorial`, `procedural_how_to`, `cinematic_teaser`, `interview_mini_profile`, `performance_music_video`, `music_driven_visual_sequence`, `seamless_loop`, `none`.

---

## 13-Dimensional Cinematography Controls

| Axis | Options | Optical & Rendering Function |
|---|---|---|
| **`optics`** | `lens_18mm`, `lens_35mm`, `lens_50mm`, `lens_85mm_compressed`, `wide_perspective`, `natural_perspective`, `compressed_telephoto` | Controls field of view, spatial compression, and near-to-far perspective ratios. |
| **`depth_of_field`** | `shallow`, `balanced`, `deep` | Controls focal plane isolation and background bokeh falloff. |
| **`exposure_contrast`** | `high_contrast`, `soft_contrast`, `high_key`, `low_key`, `chiaroscuro` | Shapes the tonal curve, shadow density, and highlight retention. |
| **`color_palette`** | `teal_orange`, `bleach_bypass`, `sepia`, `saturated_slide_film`, `neon_cyan_magenta`, `infrared_aerochrome`, `monochrome` (14 total) | Applies non-destructive color grading with strict guards against inventing false physical light sources. |
| **`image_texture`** | `clean_digital`, `subtle_stable_grain`, `film_16mm`, `film_35mm`, `vhs_analog_video`, `early_digital_dv` | Establishes sensor noise, photochemical grain, or analog video texture. |
| **`camera_motion`** | `static`, `push_in`, `pull_out`, `pan_left`, `pan_right`, `truck_left`, `truck_right`, `tilt_up`, `tilt_down`, `pedestal_up`, `pedestal_down`, `arc`, `tracking`, `shake`, `roll_clockwise`, `roll_counterclockwise`, `zoom_in`, `zoom_out` | Native H3 camera movement syntax. |
| **`camera_amplitude`** | `small`, `medium`, `large` | Motion amplitude modifier. |
| **`camera_speed`** | `slow`, `normal`, `fast` | Camera travel velocity. |
| **`camera_angle`** | `eye_level`, `low_angle`, `high_angle`, `overhead`, `dutch_static`, `worms_eye` | Elevation and horizon tilt. |
| **`camera_viewpoint`**| `pov`, `over_the_shoulder`, `mirror_or_reflection` | Spatial point-of-view owner. |
| **`lens_effects`** | `clean`, `subtle_diffusion`, `restrained_halation` | Optical bloom and highlight halation. |
| **`motion_rendering`**| `crisp`, `natural_blur`, `energetic_blur` | Shutter speed and motion blur emulation. |
| **`shot_scale`** | `extreme_wide`, `wide`, `medium_wide`, `medium`, `medium_close_up`, `close_up`, `extreme_close_up` | Framing proximity. |

Creative Treatment and Cinematography are authored as schema v2 documents. Their normative schemas are [`creative_treatment_v2.schema.json`](schemas/creative_treatment_v2.schema.json) and [`cinematography_v2.schema.json`](schemas/cinematography_v2.schema.json). The runtime accepts legacy v1 inputs for saved-workflow compatibility, normalizes them to v2 in memory, and never rewrites the source JSON.

---

## Precedence & Conflict Resolution Engine

The enhancer evaluates styling directives in a strict domain order:

$$\text{User Content Facts} > \text{Audio Gates} > \text{Shot Plan Rows} > \text{Cinematography} > \text{Tone} > \text{World Aesthetic} > \text{Visual Language} > \text{Genre}$$

### Conflict Pruning
When opposing tags collide (e.g. `cameraMotion: static` chosen alongside an `action` genre that implies dynamic camera), the lower-precedence dynamic camera lines are automatically dropped, and a warning is emitted in `treatment_warnings`. The user's explicit choice is never overridden.

---

## Explicit Shot-Plan Editor

The visual shot plan editor lets you design exact multi-shot sequences without writing timeline boilerplate:

```json
{
  "schemaVersion": 1,
  "timingMode": "exact",
  "shots": [
    {"id": "s1", "description": "The detective approaches the car.", "durationSeconds": 2.0, "cameraMotion": "push_in"},
    {"id": "s2", "description": "He opens the door and sits down.", "durationSeconds": 3.0, "transitionIn": "match_cut"},
    {"id": "s3", "description": "He turns to camera and drives away.", "durationSeconds": 5.0}
  ]
}
```

- **`timingMode: "auto"`**: The LLM distributes the duration naturally across shots.
- **`timingMode: "exact"`**: Enforces precise mathematical cut points matching `durationSeconds`.
