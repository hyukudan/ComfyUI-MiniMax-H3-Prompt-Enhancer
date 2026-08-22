# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[1] / "web" / "delivery_palette.js").read_text(encoding="utf-8")
BACKEND_TOGGLE = (Path(__file__).resolve().parents[1] / "web" / "backend_toggle.js").read_text(encoding="utf-8")


def test_delivery_voice_color_and_mood_copy_stay_distinct():
    assert 'heading.textContent = "Delivery"' in SOURCE
    assert 'dialogTitle.textContent = "Voice color"' in SOURCE
    assert 'toggle.textContent = "Voice…"' in SOURCE
    assert "Emotional tone" not in SOURCE
    assert 'segment("Verbs", delivery)' in SOURCE
    assert 'segment("Channel", channel)' in SOURCE
    assert 'segment("Timing", timing)' in SOURCE
    assert 'label: "Mood (tone)"' in BACKEND_TOGGLE
    assert "For how a spoken line sounds, use Delivery under the prompt." in BACKEND_TOGGLE


def test_voice_color_dialog_has_keyboard_and_lifecycle_contracts():
    assert 'dialog.setAttribute("role", "dialog")' in SOURCE
    assert 'toggle.setAttribute("aria-controls", dialog.id)' in SOURCE
    assert 'toggle.setAttribute("aria-haspopup", "dialog")' in SOURCE
    assert 'event.key === "Escape"' in SOURCE
    assert 'event.key !== "Tab"' in SOURCE
    assert 'window.addEventListener("scroll", viewportDismiss, true)' in SOURCE
    assert 'window.addEventListener("resize", viewportDismiss)' in SOURCE
    assert 'document.removeEventListener("pointerdown", outside)' in SOURCE
    assert 'nodeType.prototype.onRemoved' in SOURCE
    assert 'state.destroy?.()' in SOURCE
    assert 'clearLine.textContent = "Clear marks on this line"' in SOURCE
    assert "editDeliveryMark(" in SOURCE
    assert "clearDeliveryMarksOnLine(" in SOURCE


def test_voice_color_is_labelled_and_responsive_at_narrow_widths():
    for family in ("Angry & hard", "Shaken", "Sad & breaking", "Warm & bright", "Flat & dry", "Pressed"):
        assert f'group: "{family}"' in SOURCE
    for label in ("angry, held back", "near tears", "through laughter", "cold, level", "conspiratorial"):
        assert f'label: "{label}"' in SOURCE
    assert "flex-wrap:wrap;max-width:100%" in SOURCE
    assert "width:min(340px,calc(100vw - 16px))" in SOURCE
    assert "window.innerWidth - rect.width - 8" in SOURCE


def test_delivery_feedback_explains_prose_and_warns_about_unquoted_lines():
    assert "Marks resolve to plain prose — they never appear in the final prompt." in SOURCE
    assert 'status.setAttribute("role", "status")' in SOURCE
    assert 'status.setAttribute("aria-live", "polite")' in SOURCE
    assert "will be written as prose, not shown in the final prompt" in SOURCE


def test_resting_chips_are_neutral_and_only_real_line_marks_look_selected():
    assert "var(--h3-success" not in SOURCE
    assert "rgba(74,222,128" not in SOURCE
    assert "rgba(122,184,255" not in SOURCE
    assert "rgba(244,195,106" not in SOURCE
    assert 'button.setAttribute("aria-pressed", "false")' in SOURCE
    assert 'control.setAttribute("aria-pressed", String(selected))' in SOURCE
    assert 'line.includes(token)' in SOURCE
    assert 'button.addEventListener("pointerenter"' in SOURCE
    assert 'button.addEventListener("pointerleave"' in SOURCE
    assert 'mark.segment === "channel"' in SOURCE
    assert 'mark.segment === "timing"' in SOURCE


def test_help_and_recent_are_progressive_without_flow_expansion():
    assert 'document.createElement("details")' not in SOURCE
    assert 'helpButton.textContent = "How marks work"' in SOURCE
    assert 'help.setAttribute("role", "dialog")' in SOURCE
    assert 'position:fixed' in SOURCE
    assert 'RECENT_STORAGE_KEY = "minimax_h3_delivery_recent_v1"' in SOURCE
    assert "updateRecentDeliveryMarks(" in SOURCE
    assert 'root.getBoundingClientRect().width < 420' in SOURCE
