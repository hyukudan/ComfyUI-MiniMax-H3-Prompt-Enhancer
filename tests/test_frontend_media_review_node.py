# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path

from prompt_enhancer_node import MiniMaxH3GGUFPromptEnhancer, MiniMaxH3PromptEnhancer


ROOT = Path(__file__).parents[1]


def test_compact_node_preserves_eight_legacy_outputs_before_native_compose_outputs():
    legacy_types = ("STRING", "STRING", "STRING", "FLOAT", "STRING", "STRING", "INT", "INT")
    legacy_names = (
        "enhanced_prompt", "validation_report", "enhancement_manifest", "duration_seconds",
        "aspect_ratio", "treatment_warnings", "width", "height",
    )
    compose_types = ("H3_REFERENCE_PROJECT", "IMAGE", "IMAGE", "AUDIO", "STRING")
    compose_names = ("reference_project", "pictures", "videos", "audios", "reference_project_json")
    for node_class in (MiniMaxH3PromptEnhancer, MiniMaxH3GGUFPromptEnhancer):
        assert node_class.RETURN_TYPES == legacy_types + compose_types
        assert node_class.RETURN_NAMES == legacy_names + compose_names


def test_node_frontend_groups_controls_without_new_persistent_widgets():
    source = (ROOT / "web" / "backend_toggle.js").read_text(encoding="utf-8")
    assert 'always_re_enhance: "Re-enhance on every run"' in source
    assert 'editing_intent: "Editing intent (Ref2VA)"' in source
    assert 'lora_trigger_words: "LoRA trigger words"' in source
    assert "createAudioSettingsDetails" in source
    assert "mountCompactCreativePanel" in source
    assert "const treatmentDetails" not in source
    assert "const cinematographyDetails" not in source
    assert "const shotDetails" not in source
    assert 'modeWidget.value === "ref2va"' in source
    assert 'markPanelWidgetNonPersistent(panelWidget)' in source
    assert '"visual_style_preset"' in source


def test_resolution_budget_reuses_the_canonical_float_with_user_facing_effective_size():
    source = (ROOT / "web" / "backend_toggle.js").read_text(encoding="utf-8")
    resolution = (ROOT / "web" / "studio" / "media_resolution.js").read_text(encoding="utf-8")
    assert 'target_megapixels: "Resolution budget"' in source
    assert "Target megapixels (0 = auto)" not in source
    assert "Target Megapixels (0.0 = auto)" not in source
    assert "function createResolutionBudgetControl" in source
    assert 'class="minimax-h3-resolution-mode"' not in source
    assert 'createPanelElement("div", "minimax-h3-resolution-mode")' in source
    assert 'button.addEventListener("click", () => commitMode(value))' in source
    assert 'custom.addEventListener("input", () => commitCustomBudget())' not in source
    assert "let editingCustom = false" in source
    assert "if (!editingCustom)" in source
    assert 'custom.addEventListener("focus", () => { editingCustom = true; })' in source
    assert 'custom.addEventListener("blur", () => { editingCustom = false; sync(); })' in source
    assert 'if (event.key === "Enter")' in source
    assert 'if (event.key === "Escape")' in source
    assert "custom.disabled = automatic" in source
    assert 'custom.addEventListener("input"' in source
    assert 'custom.type = "text"' in source
    assert 'custom.inputMode = "decimal"' in source
    assert 'replace(",", ".")' in source
    assert 'custom.addEventListener("change", () => commitCustomBudget())' in source
    assert 'custom.focus()' in source
    assert 'name === "target_megapixels"' in source
    assert "refused to write a Shot Plan payload into cinematography_json" in source
    assert "formatResolutionLabel(effectiveH3Resolution(aspectRatio, megapixels))" in source
    assert 'wrapRefreshCallback(node, "aspect_ratio", refreshResolutionBudget)' in source
    assert "Math.sqrt" in resolution
    assert "roundHalfEven" in resolution
    for node_class in (MiniMaxH3PromptEnhancer, MiniMaxH3GGUFPromptEnhancer):
        specification = node_class.INPUT_TYPES()["optional"]["target_megapixels"]
        assert specification[0] == "FLOAT"
        assert specification[1]["default"] == 0.0
        assert "min" not in specification[1]
        assert "max" not in specification[1]
        assert specification[1]["step"] == 0.01


def test_studio_owns_visual_language_search_and_sanitized_look_transfer():
    backend = (ROOT / "web" / "backend_toggle.js").read_text(encoding="utf-8")
    camera = (ROOT / "web" / "studio" / "tab_camera_look.js").read_text(encoding="utf-8")
    assert "createVisualLanguageSearch" not in backend
    assert "visualLanguageGroups()" in backend
    assert 'trigger.setAttribute("role", "combobox")' in camera
    assert 'list.setAttribute("role", "listbox")' in camera
    assert 'search.type = "search"' in camera
    assert 'button("Export JSON"' in camera
    assert 'button(lookState.transferMode === "import" ? "Apply JSON" : "Import JSON"' in camera
    assert "MAX_LOOK_PAYLOAD_LENGTH" in backend
    import_method = backend[backend.index('importLook(payload) {'):backend.index('exploreLook(fullCinematography', backend.index('importLook(payload) {'))]
    assert "sanitizeLookEnvelope" in import_method
    assert "schemaVersion !== LOOK_SCHEMA_VERSION" in import_method
    assert "applyLookEnvelope" in import_method
    assert "commitShotPlan" not in import_method
    export_method = backend[backend.index('exportLook(name = "") {'):backend.index('importLook(payload)', backend.index('exportLook(name = "") {'))]
    assert "serializeLookEnvelope" in export_method


def test_creative_and_cinematography_are_native_v2_with_explicit_legacy_import():
    backend = (ROOT / "web" / "backend_toggle.js").read_text(encoding="utf-8")
    catalogs = (ROOT / "web" / "studio" / "catalogs.js").read_text(encoding="utf-8")
    camera = (ROOT / "web" / "studio" / "tab_camera_look.js").read_text(encoding="utf-8")
    assert "creativeTreatment: 2" in catalogs
    assert "cinematography: 2" in catalogs
    assert 'const creative = creativeDocument.kind === "v2"' in backend
    assert 'const cinematography = cinematographyDocument.kind === "v2"' in backend
    assert 'if (!["blank", "v2"].includes(this.creativeDocument()?.kind)) return false;' in backend
    assert 'if (!["blank", "v2"].includes(this.cinematographyDocument()?.kind)) return false;' in backend
    assert "importCreativeSource(raw)" in backend
    assert "importCinematographySource(raw)" in backend
    assert "nativeLookTargetsAreEditable(node)" in backend
    assert "sanitizeCreativeTreatment(source, { allowLegacy: true })" in backend
    assert "sanitizeCinematography(source, { allowLegacy: true })" in backend
    assert '["blank", "v2"].includes(creativeDocument.kind)' in camera
    assert '["blank", "v2"].includes(cameraDocument.kind)' in camera
    assert 'button(documentState.kind === "v1" ? "Import v1 as v2"' in camera
    assert 'sources.details.open = false' in camera
    assert "nativeStructuredDocumentView" in catalogs
    assert "nativeDocumentViewForWidget" in backend
    assert "commitNativeStructuredStorage" in backend
    native_commit = backend[backend.index("function commitNativeStructuredStorage"):backend.index("function markPanelWidgetNonPersistent")]
    assert "writeJsonStorage" in native_commit
    hydrate = backend[backend.index("function hydrateCreativeDirectionPanel"):backend.index("function wrapJsonStorageCallback")]
    assert "writeJsonStorage" not in hydrate


def test_review_frontend_exposes_every_contract_safe_action():
    source = (ROOT / "web" / "studio" / "coach_actions.js").read_text(encoding="utf-8")
    for kind in (
        "clear_shot_camera", "clear_global_camera", "activate_resource", "add_binding",
        "align_transition_from_state",
    ):
        assert f'"{kind}"' in source
