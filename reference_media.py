# SPDX-License-Identifier: GPL-3.0-only
"""Lazy ComfyUI-native decoders for Reference Director outputs."""

from __future__ import annotations

import os
from typing import Any


def resolve_annotated(annotated: str) -> str:
    try:
        import folder_paths
        return str(folder_paths.get_annotated_filepath(annotated))
    except Exception:  # pragma: no cover - direct imports outside ComfyUI
        for suffix in (" [input]", " [output]", " [temp]"):
            if annotated.endswith(suffix):
                return annotated[:-len(suffix)]
        return annotated


def _require_file(annotated: str, label: str) -> str:
    path = resolve_annotated(annotated)
    if not path or not os.path.isfile(path):
        raise ValueError(f"{label} points to a missing ComfyUI input file: {annotated}")
    return path


def load_picture(annotated: str, label: str) -> Any:
    path = _require_file(annotated, label)
    import numpy as np
    import torch
    from PIL import Image, ImageOps
    try:
        with Image.open(path) as image:
            array = np.asarray(ImageOps.exif_transpose(image).convert("RGB"), dtype=np.float32) / 255.0
    except Exception as exc:
        raise ValueError(f"{label} could not be decoded as a picture: {exc}") from exc
    return torch.from_numpy(array)[None, ...]


def load_video_frames(annotated: str, label: str) -> tuple[Any, Any]:
    path = _require_file(annotated, label)
    try:
        import torch
        from comfy_api.latest import InputImpl
        parts = InputImpl.VideoFromFile(path).get_components()
    except Exception as exc:
        raise ValueError(f"{label} could not be decoded with ComfyUI's video loader: {exc}") from exc
    frames = parts.images
    frame_rate = float(parts.frame_rate or 24.0)
    frame_count = int(frames.shape[0])
    if frame_count < 1:
        raise ValueError(f"{label} decoded to no video frames.")
    if abs(frame_rate - 24.0) > 0.01:
        target_count = max(1, round(frame_count * 24.0 / frame_rate))
        indices = torch.linspace(0, frame_count - 1, target_count, device=frames.device).round().long()
        frames = frames[indices]
    if int(frames.shape[0]) < 5:
        raise ValueError(f"{label} is under five frames at H3's 24 fps reference rate.")
    return frames, parts.audio


def load_audio(annotated: str, label: str) -> Any:
    path = _require_file(annotated, label)
    try:
        from comfy_extras.nodes_audio import load as comfy_load
        waveform, sample_rate = comfy_load(path)
    except Exception as exc:
        raise ValueError(f"{label} could not be decoded with ComfyUI's audio loader: {exc}") from exc
    return {"waveform": waveform.unsqueeze(0), "sample_rate": int(sample_rate)}


def load_generation_media(reference_project: dict, generation_id: str = "") -> dict[str, list[Any]]:
    generations = reference_project.get("inputsByGeneration", {})
    if generation_id and generation_id not in generations:
        raise ValueError(f"Unknown reference generation {generation_id!r}.")
    selected = generation_id if generation_id in generations else next(iter(generations), "")
    pictures: list[Any] = []
    videos: list[Any] = []
    audios: list[Any] = []
    video_audios: list[Any] = []
    standalone_audios: list[Any] = []
    video_audio: dict[str, Any] = {}
    for item in generations.get(selected, []):
        source = item.get("source") or {}
        annotated = source.get("file")
        label = item.get("label") or item.get("assetId") or "reference"
        if not annotated:
            raise ValueError(f"{label} has no physical source file.")
        role = item.get("role")
        media_type = item.get("mediaType")
        if media_type == "picture":
            pictures.append(load_picture(annotated, label))
        elif media_type == "video":
            frames, soundtrack = load_video_frames(annotated, label)
            videos.append(frames)
            video_audios.append(soundtrack)
            video_audio[item.get("assetId", "")] = soundtrack
        elif media_type == "audio" and role == "video_soundtrack":
            soundtrack = video_audio.get(item.get("assetId", ""))
            if soundtrack is None:
                _frames, soundtrack = load_video_frames(annotated, label)
            if soundtrack is None:
                raise ValueError(f"{label} requests a video soundtrack, but the clip has no audio.")
            audios.append(soundtrack)
        elif media_type == "audio":
            decoded = load_audio(annotated, label)
            audios.append(decoded)
            standalone_audios.append(decoded)
    return {
        "generationId": selected,
        "pictures": pictures,
        "videos": videos,
        # Keep the historical combined audio list for saved workflows. Numbered
        # native outputs below distinguish video soundtracks from standalone audio.
        "audios": audios,
        "videoAudios": video_audios,
        "standaloneAudios": standalone_audios,
    }
