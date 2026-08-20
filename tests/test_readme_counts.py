# SPDX-License-Identifier: GPL-3.0-only
"""The catalogue sizes quoted in the README must match the catalogue.

They drifted once and drifted upward: every figure counted the "none" placeholder as though it
were a curated profile, so 116 profiles were advertised as 131+. Deriving the numbers here means
the next profile added either updates the README or fails the build.
"""

import pathlib
import re

import content_formats
import creative_treatments
import prompt_guides

README = pathlib.Path(__file__).resolve().parent.parent / "README.md"


def _size(catalogue):
    """Curated entries only: "none" means no profile, not a profile."""
    return len([name for name in catalogue if name != "none"])


def _counts():
    return {
        "visual languages": _size(creative_treatments.VISUAL_LANGUAGE_PROFILES),
        "world aesthetics": _size(creative_treatments.WORLD_AESTHETIC_PROFILES),
        "tones": _size(creative_treatments.TONE_PROFILES),
        "genres": _size(creative_treatments.GENRE_PROFILES),
        "content formats": _size(content_formats.CONTENT_FORMAT_PROFILES),
    }


def test_readme_quotes_the_real_profile_totals():
    text = README.read_text(encoding="utf-8")
    counts = _counts()
    total = sum(counts.values())

    assert f"**{total} curated profiles**" in text, f"README should say {total} curated profiles"
    for label, count in counts.items():
        assert f"{count} {label}" in text, f"README should say {count} {label}"


def test_documentation_hub_agrees_with_the_catalogue():
    text = README.read_text(encoding="utf-8")
    hub = [line for line in text.splitlines() if "Style Bible & Cinematography" in line]
    assert hub, "the documentation hub row went missing"
    counts = _counts()
    for count, label in (
        (counts["visual languages"], "Visual Languages"),
        (counts["world aesthetics"], "World Aesthetics"),
        (counts["tones"], "Tones"),
        (counts["genres"], "Genres"),
        (counts["content formats"], "Content Formats"),
        (len(creative_treatments.CINEMATOGRAPHY_CHOICES), "Cinematography Axes"),
    ):
        assert f"{count} {label}" in hub[0], f"hub should say {count} {label}"


def test_language_figures_are_real():
    text = README.read_text(encoding="utf-8")
    canonical = len([name for name in prompt_guides.DIALOGUE_LANGUAGE_CHOICES if name != "auto"])
    aliases = len(prompt_guides._LANGUAGE_ALIASES)
    assert f"{canonical} Canonical Languages" in text
    assert f"{aliases} Dialect Aliases" in text
    assert f"{canonical} canonical languages" in text
    assert f"{aliases} regional dialect aliases" in text


def test_readme_examples_are_written_in_english():
    """This is an English README; a Spanish sample line reads as an oversight."""
    text = README.read_text(encoding="utf-8")
    for stray in ("No me toques", "escúchame", "Fuera de mi casa", "No me dejes", "La mujer"):
        assert stray not in text, f"{stray!r} left in an English document"
