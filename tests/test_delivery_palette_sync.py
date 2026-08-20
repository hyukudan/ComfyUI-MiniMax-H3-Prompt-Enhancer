# SPDX-License-Identifier: GPL-3.0-only
"""The palette and the resolver must agree.

The frontend only inserts characters; every meaning lives in DELIVERY_EMOJI on the Python side.
An emoji offered by a button but unknown to the resolver would survive into the prompt and be
spoken aloud, which is precisely the failure this whole feature exists to prevent.
"""

import pathlib
import re

import prompt_guides as guides

PALETTE_JS = pathlib.Path(__file__).resolve().parent.parent / "web" / "delivery_palette.js"


def _palette_entries():
    source = PALETTE_JS.read_text(encoding="utf-8")
    block = re.search(r"const DELIVERY_EMOJI = \[(.*?)\n\];", source, re.DOTALL)
    assert block, "palette list not found; the sync guard cannot run"
    return re.findall(r'\{\s*emoji:\s*"([^"]+)",\s*tier:\s*"([^"]+)"', block.group(1))


def test_every_button_resolves_to_something_the_backend_knows():
    for emoji, _tier in _palette_entries():
        assert emoji in guides.DELIVERY_EMOJI, f"{emoji} has a button but no resolver entry"


def test_declared_tier_matches_the_backend_classification():
    for emoji, tier in _palette_entries():
        _prose, backend_kind = guides.DELIVERY_EMOJI[emoji]
        assert backend_kind == tier, f"{emoji} is {tier} in the palette but {backend_kind} in Python"


def test_palette_offers_every_documented_verb():
    # The verb-backed marks are the safest ones, so none of them should be missing from the UI.
    palette = {emoji for emoji, _tier in _palette_entries()}
    verbs = {emoji for emoji, (_prose, kind) in guides.DELIVERY_EMOJI.items() if kind == "verb"}
    assert verbs <= palette
