import sys
import types

import pytest

import reference_media


def _install_fake_comfy_audio(monkeypatch, waveform, sample_rate):
    package = types.ModuleType("comfy_extras")
    module = types.ModuleType("comfy_extras.nodes_audio")
    module.load = lambda _path: (waveform, sample_rate)
    monkeypatch.setitem(sys.modules, "comfy_extras", package)
    monkeypatch.setitem(sys.modules, "comfy_extras.nodes_audio", module)
    monkeypatch.setattr(reference_media, "_require_file", lambda _annotated, _label: "voice.wav")


def test_load_audio_slices_the_physical_waveform_to_the_selected_range(monkeypatch):
    torch = pytest.importorskip("torch")
    waveform = torch.arange(100, dtype=torch.float32).reshape(1, 100)
    _install_fake_comfy_audio(monkeypatch, waveform, 10)
    decoded = reference_media.load_audio(
        "voice.wav [input]", "<Audio 1>", {"startSeconds": 2.1, "endSeconds": 4.6},
    )
    assert decoded["sample_rate"] == 10
    assert decoded["waveform"].shape == (1, 1, 25)
    assert decoded["waveform"].is_contiguous()
    assert torch.equal(decoded["waveform"][0, 0], waveform[0, 21:46])


def test_load_audio_rejects_a_clip_beyond_the_decoded_source(monkeypatch):
    torch = pytest.importorskip("torch")
    _install_fake_comfy_audio(monkeypatch, torch.zeros((1, 20)), 10)
    with pytest.raises(ValueError, match="ends after the decoded audio"):
        reference_media.load_audio(
            "voice.wav [input]", "<Audio 1>", {"startSeconds": 1.0, "endSeconds": 3.0},
        )
