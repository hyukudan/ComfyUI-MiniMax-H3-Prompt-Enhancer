# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path


FRONTEND = Path(__file__).parents[1] / "web" / "backend_toggle.js"


def test_visual_language_search_filters_display_options_without_changing_canonical_values():
    source = FRONTEND.read_text(encoding="utf-8")
    helper = source.split("function createVisualLanguageSearch", 1)[1].split(
        "function ensureUnavailableOption", 1,
    )[0]
    assert 'input.type = "search"' in helper
    assert 'input.placeholder = "Search visual styles…"' in helper
    assert "choiceLabel} ${value} ${groups.get(value)" in helper
    assert "terms.every((term) => text.includes(term))" in helper
    assert "visibleValues.add(selectedValue)" in helper
    assert "ensureUnavailableOption(select, selectedValue)" in helper
    assert 'status.setAttribute("aria-live", "polite")' in helper
    assert "No matching styles" in helper
    assert 'event.key === "Escape"' in helper
    assert 'event.key === "ArrowDown" || event.key === "Enter"' in helper

    panel = source.split("function addCreativeDirectionPanel", 1)[1]
    assert 'definition.key === "visualLanguage"' in panel
    assert "createVisualLanguageSearch(node, select, definition.label)" in panel
    assert "creativeFilters[definition.key] = filter" in panel
    assert "filter.sync(creative[definition.key])" in source
    assert "serializeCreativeTreatment(node.__minimaxCreativeTreatmentState)" in source
