# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path


FRONTEND = Path(__file__).parents[1] / "web" / "backend_toggle.js"
CAMERA_LOOK = Path(__file__).parents[1] / "web" / "studio" / "tab_camera_look.js"


def _function(source: str, name: str, next_name: str) -> str:
    return source.split(f"function {name}", 1)[1].split(f"function {next_name}", 1)[0]


def test_look_round_trip_carries_all_creative_and_cinematography_state_but_never_shots():
    source = FRONTEND.read_text(encoding="utf-8")
    capture = _function(source, "lookEnvelopeFromNode", "hideJsonStorageWidget")
    apply = _function(source, "applyLookEnvelope", "randomFrom")

    assert "sanitizeCreativeTreatment(node.__minimaxCreativeTreatmentState)" in capture
    assert "sanitizeCinematography(node.__minimaxCinematographyState)" in capture
    assert "shot" not in capture.casefold()
    assert "CREATIVE_TREATMENT_WIDGET" in apply
    assert "CINEMATOGRAPHY_WIDGET" in apply
    assert "hydrateCreativeDirectionPanel(node)" in apply
    assert "SHOT_PLAN" not in apply


def test_look_import_rejects_future_schema_and_sanitizes_both_payload_halves():
    source = FRONTEND.read_text(encoding="utf-8")
    sanitize = _function(source, "sanitizeLookEnvelope", "readLookPresets")

    assert "parsed.schemaVersion !== undefined" in sanitize
    assert "parsed.schemaVersion !== LOOK_SCHEMA_VERSION" in sanitize
    assert "sanitizeCreativeTreatment(parsed.creativeTreatment, { allowLegacy: true })" in sanitize
    assert "sanitizeCinematography(parsed.cinematography, { allowLegacy: true })" in sanitize


def test_look_library_is_bounded_recoverable_and_browser_local():
    source = FRONTEND.read_text(encoding="utf-8")
    camera_look = CAMERA_LOOK.read_text(encoding="utf-8")
    assert 'const LOOK_STORAGE_KEY = "minimax_h3_looks_v1"' in source
    assert "const MAX_LOOK_PRESETS = 50" in source
    assert "window.localStorage" in source
    assert "evictOldestLooks(presets)" in source
    assert "navigator?.clipboard?.writeText" in camera_look
    assert "navigator?.clipboard?.readText" in camera_look
    assert "The shot plan was left untouched" in camera_look
