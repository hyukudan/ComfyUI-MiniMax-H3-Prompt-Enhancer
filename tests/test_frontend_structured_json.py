# SPDX-License-Identifier: GPL-3.0-only

import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
FRONTEND = ROOT / "web" / "backend_toggle.js"
FIXTURE = ROOT / "tests" / "fixtures" / "structured_widgets_no_clobber.json"


def _function(source: str, name: str, next_name: str) -> str:
    return source.split(f"function {name}", 1)[1].split(f"function {next_name}", 1)[0]


def test_fixture_covers_all_three_structured_widgets_and_preservation_states():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert fixture["widgetNames"] == [
        "creative_treatment_json",
        "shot_plan_json",
        "cinematography_json",
    ]
    assert set(fixture["cases"]) == {"blank", "v1", "malformed", "future"}
    assert all(len(values) == 3 for values in fixture["cases"].values())


def test_hydration_never_writes_structured_widget_storage():
    source = FRONTEND.read_text(encoding="utf-8")
    hydrate = _function(source, "hydrateCreativeDirectionPanel", "wrapJsonStorageCallback")
    assert "writeJsonStorage(" not in hydrate
    assert "commitStructuredStorage(" not in hydrate
    assert "structuredWidgetStore" in hydrate
    # Creative Treatment and Cinematography are native v2 documents. Only the
    # legacy shot-plan editor still performs its explicit first-edit migration.
    assert hydrate.count('kind === "v1"') == 1
    assert hydrate.count('kind === "v2"') == 2
    assert "defaultCreativeTreatment()" in hydrate
    assert "defaultShotPlan()" in hydrate
    assert "defaultCinematography()" in hydrate


def test_all_structured_commits_pass_through_the_no_clobber_store():
    source = FRONTEND.read_text(encoding="utf-8")
    commit_paths = {
        "commitCreativeTreatment": "commitNativeStructuredStorage(",
        "commitCinematography": "commitNativeStructuredStorage(",
        "commitShotPlan": "commitStructuredStorage(",
    }
    for name, expected_path in commit_paths.items():
        start = source.index(f"function {name}")
        body = source[start:source.index("\n}\n", start) + 3]
        assert expected_path in body
        assert "writeJsonStorage(" not in body


def test_malformed_and_future_documents_are_exposed_as_read_only():
    source = FRONTEND.read_text(encoding="utf-8")
    hydrate = _function(source, "hydrateCreativeDirectionPanel", "wrapJsonStorageCallback")
    assert "creativeReadOnly" in hydrate
    assert "shotsReadOnly" in hydrate
    assert "cinematographyReadOnly" in hydrate
    assert ".inert =" in hydrate
    assert "has been preserved without changes" in hydrate


def test_all_four_canonical_json_widgets_stay_hidden_without_contract_conversion():
    source = FRONTEND.read_text(encoding="utf-8")
    assert 'const MEDIA_PROJECT_WIDGET = "media_manifest"' in source
    assert "STUDIO_JSON_STORAGE_WIDGETS.has(widget.name)" in source
    visibility = _function(source, "enforceConditionalVisibility", "conditionalVisibilitySignature")
    assert "hideJsonStorageWidget(manifest)" in visibility
    assert "setWidgetVisible(manifest" not in visibility

    helper = (ROOT / "web" / "studio" / "storage_visibility.js").read_text(encoding="utf-8")
    assert "widget.hidden = true" in helper
    assert "widget.options.hidden = true" in helper
    assert "widget.type =" not in helper
    assert "widget.serialize =" not in helper
    assert "widget.serializeValue =" not in helper


def test_v2_media_source_is_available_only_inside_collapsed_source_tools():
    overview = (ROOT / "web" / "studio" / "overview.js").read_text(encoding="utf-8")
    tools = overview.split("function sourceTools", 1)[1].split("function healthSummary", 1)[0]
    assert 'model.sources.project.kind === "v2"' in tools
    assert 'name: "Media project v2"' in tools
    source_card = (ROOT / "web" / "studio" / "components" / "source_state.js").read_text(encoding="utf-8")
    assert 'if (state.kind === "v2") appendRawViewer(card, state);' in source_card
