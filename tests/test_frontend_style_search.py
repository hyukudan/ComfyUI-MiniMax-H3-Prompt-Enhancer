# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path


ROOT = Path(__file__).parents[1] / "web"
FRONTEND = ROOT / "backend_toggle.js"
CAMERA_LOOK = ROOT / "studio" / "tab_camera_look.js"


def test_visual_language_search_filters_display_options_without_changing_canonical_values():
    source = FRONTEND.read_text(encoding="utf-8")
    camera = CAMERA_LOOK.read_text(encoding="utf-8")
    helper = camera.split("function visualLanguageField", 1)[1]

    assert 'search.type = "search"' in helper
    assert 'search.placeholder = "Search visual languages…"' in helper
    assert 'trigger.setAttribute("role", "combobox")' in helper
    assert 'list.setAttribute("role", "listbox")' in helper
    assert "popover.hidden = true" in helper
    assert 'trigger.addEventListener("click"' in helper
    assert "visualLanguageHierarchy(choices, search.value, normalizedSearchText)" in helper
    assert 'option.dataset.preview = preview.status' in helper
    assert 'option.setAttribute("role", "option")' in helper
    assert "commit(token)" in helper
    assert 'searchStatus.setAttribute("aria-live", "polite")' in helper
    assert "No matching visual languages" in helper
    assert 'event.key === "Escape"' in helper
    assert '["ArrowDown", "Enter", " "].includes(event.key)' in helper
    assert "focusOption(0)" in helper

    assert 'key === "visualLanguage"' in camera
    assert "visualLanguageField(" in camera
    assert "controller.visualLanguageGroups?.()" in camera
    assert "serializeCreativeTreatment(node.__minimaxCreativeTreatmentState)" in source
