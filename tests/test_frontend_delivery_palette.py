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
