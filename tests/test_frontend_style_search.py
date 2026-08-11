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
    assert 'trigger.setAttribute("role", "combobox")' in helper
    assert 'list.setAttribute("role", "listbox")' in helper
    assert 'popover.hidden = true' in helper
    assert 'trigger.addEventListener("click"' in helper
    assert "choiceLabel} ${value} ${groups.get(value)" in helper
    assert "terms.every((term) => text.includes(term))" in helper
    assert 'option.setAttribute("role", "option")' in helper
    assert 'select.dispatchEvent(new Event("change", { bubbles: true }))' in helper
    assert 'status.setAttribute("aria-live", "polite")' in helper
    assert "No matching styles" in helper
    assert 'event.key === "Escape"' in helper
    assert 'event.key === "ArrowDown" || event.key === "Enter"' in helper
    assert 'list.querySelector("[role=\'option\']")?.focus()' in helper

    panel = source.split("function addCreativeDirectionPanel", 1)[1]
    assert 'definition.key === "visualLanguage"' in panel
    assert "createVisualLanguageSearch(node, select, definition.label)" in panel
    assert "creativeFilters[definition.key] = filter" in panel
    assert "filter.sync(creative[definition.key])" in source
    assert "serializeCreativeTreatment(node.__minimaxCreativeTreatmentState)" in source
