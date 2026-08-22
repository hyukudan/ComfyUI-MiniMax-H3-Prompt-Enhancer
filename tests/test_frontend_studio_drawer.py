# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path


ROOT = Path(__file__).parents[1]
WEB = ROOT / "web"


def test_studio_drawer_has_accessible_navigation_review_and_resizing():
    drawer = (WEB / "studio" / "drawer.js").read_text(encoding="utf-8")
    styles = (WEB / "studio" / "styles.js").read_text(encoding="utf-8")
    tokens = (WEB / "studio" / "tokens.js").read_text(encoding="utf-8")
    for tab in ("Overview", "Shots", "Subjects", "Environments", "Media", "Camera", "Look"):
        assert f'"{tab}"' in drawer
    assert '"Review"' in drawer
    assert 'setAttribute("role", "dialog")' in drawer
    assert 'setAttribute("aria-modal", "false")' in drawer
    assert 'setAttribute("role", "tablist")' in drawer
    assert 'setAttribute("role", "tabpanel")' in drawer
    assert 'setAttribute("role", "separator")' in drawer
    assert 'event.key === "Escape"' in drawer
    assert "document.body.appendChild(drawer)" in drawer
    assert "position: fixed" in styles
    assert "STUDIO_MIN_WIDTH = 420" in tokens
    assert "STUDIO_MAX_WIDTH = 1100" in tokens
    assert "prefers-reduced-motion" in styles


def test_dashboard_is_nonpersistent_dom_and_does_not_add_canonical_widgets():
    entrypoint = (WEB / "backend_toggle.js").read_text(encoding="utf-8")
    drawer = (WEB / "studio" / "drawer.js").read_text(encoding="utf-8")
    assert "createStudioDashboard(node, studioController)" in entrypoint
    assert "node.addWidget" not in drawer
    assert "node.addDOMWidget" not in drawer
    assert "createStudioDashboard" in drawer
    assert "data-studio-tab" in drawer


def test_shot_editor_supports_v2_camera_end_delta_and_fixed_row_virtualization():
    shots = (WEB / "studio" / "tab_shots.js").read_text(encoding="utf-8")
    assert "SHOT_ROW_HEIGHT = 60" in shots
    assert "SHOT_OVERSCAN = 5" in shots
    assert "visibleShotRange" in shots
    assert '"cameraStart"' in shots
    assert '"cameraEnd"' in shots
    assert "shot.cameraPath" in shots
    assert "inherits start" in shots
    assert "plan.shots.length >= 64" in shots


def test_legacy_boolean_shot_storage_is_blank_without_hydration_writes():
    schema = (WEB / "studio" / "schema.js").read_text(encoding="utf-8")
    backend = (WEB / "backend_toggle.js").read_text(encoding="utf-8")
    assert 'typeof parsed === "boolean" || parsed === null' in schema
    assert "allowLegacyBlankScalars: widgetName === SHOT_PLAN_WIDGET" in backend
    shot_document = backend[backend.index("shotDocument() {"):backend.index("commitShotPlan(raw)")]
    assert "writeJsonStorage" not in shot_document


def test_media_master_detail_contributes_its_intrinsic_height_to_the_section_grid():
    styles = (WEB / "studio" / "styles.js").read_text(encoding="utf-8")
    assert ".minimax-h3-section-media > .minimax-h3-master-detail {" in styles
    media_fix = styles[styles.index(".minimax-h3-section-media > .minimax-h3-master-detail {"):]
    media_fix = media_fix[:media_fix.index("}")]
    assert "min-height: auto" in media_fix
    assert "align-self: start" in media_fix


def test_studio_field_checkboxes_do_not_inherit_full_width_text_input_geometry():
    styles = (WEB / "studio" / "styles.js").read_text(encoding="utf-8")
    assert '.minimax-h3-studio-field input:not([type="checkbox"]):not([type="radio"]),' in styles
    assert '.minimax-h3-studio-field input[type="checkbox"],' in styles
    assert "justify-self: start" in styles


def test_v2_project_tabs_cover_entities_states_views_assets_and_bindings():
    subjects = (WEB / "studio" / "tab_subjects.js").read_text(encoding="utf-8")
    environments = (WEB / "studio" / "tab_environments.js").read_text(encoding="utf-8")
    references = (WEB / "studio" / "tab_references.js").read_text(encoding="utf-8")
    assert "appearanceStates" in subjects
    assert "identityAssetIds" in subjects
    assert "permanent" in environments
    assert "temporary" in environments
    assert "views" in environments
    assert "generation.bindings" in references
    assert "physicalLabel" in references
