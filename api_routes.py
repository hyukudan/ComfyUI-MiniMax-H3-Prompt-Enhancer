# SPDX-License-Identifier: GPL-3.0-only
"""Same-origin ComfyUI API routes used by the prompt-enhancer frontend."""

from __future__ import annotations

import asyncio
import hashlib
import mimetypes
import os
from pathlib import Path
from uuid import uuid4

from aiohttp import web
from server import PromptServer

from .prompt_enhancer import discover_models
from .reference_director import (
    MAX_SOURCE_BYTES,
    SOURCE_STORAGE,
    SOURCE_SUBFOLDER,
    media_type_for_filename,
    safe_source_filename,
)


@PromptServer.instance.routes.post("/minimax_h3_prompt_enhancer/models")
async def minimax_h3_models(request):
    """Proxy model discovery through ComfyUI to avoid browser CORS limitations."""
    try:
        payload = await request.json()
        models = await asyncio.to_thread(
            discover_models,
            payload.get("endpoint", ""),
            payload.get("api_key", ""),
            bool(payload.get("allow_remote_endpoint", False)),
            15,
        )
        return web.json_response({"models": models})
    except Exception as exc:  # ComfyUI route boundary: return a concise UI-safe error.
        return web.json_response({"error": str(exc)}, status=400)


def _reference_input_root() -> Path:
    import folder_paths
    root = (Path(folder_paths.get_input_directory()) / SOURCE_SUBFOLDER).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _source_payload(path: Path, original_name: str, media_type: str, digest: str, size: int) -> dict:
    return {
        "storage": SOURCE_STORAGE,
        "file": f"{SOURCE_SUBFOLDER}/{path.name} [input]",
        "sha256": digest,
        "mediaType": media_type,
        "originalName": Path(original_name.replace("\\", "/")).name,
        "sizeBytes": size,
        "mimeType": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@PromptServer.instance.routes.post("/minimax_h3_prompt_enhancer/references/upload")
async def minimax_h3_reference_upload(request):
    """Stream one supported reference into ComfyUI's input directory without trusting its path."""
    temporary = None
    try:
        reader = await request.multipart()
        field = await reader.next()
        if field is None or field.name != "file" or not field.filename:
            raise ValueError("Choose one picture, video or audio file.")
        safe_name = safe_source_filename(field.filename)
        media_type = media_type_for_filename(safe_name)
        maximum = MAX_SOURCE_BYTES[media_type]
        root = _reference_input_root()
        temporary = root / f".upload-{uuid4().hex}.tmp"
        digest = hashlib.sha256()
        size = 0
        with temporary.open("xb") as stream:
            while True:
                chunk = await field.read_chunk(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > maximum:
                    raise ValueError(f"{media_type.title()} references may not exceed {maximum // (1024 * 1024)} MB.")
                digest.update(chunk)
                stream.write(chunk)
        if size == 0:
            raise ValueError("The selected reference file is empty.")
        hex_digest = digest.hexdigest()
        source_path = Path(safe_name)
        final_name = f"{source_path.stem}-{hex_digest[:12]}{source_path.suffix.lower()}"
        final_path = root / final_name
        if final_path.exists():
            temporary.unlink(missing_ok=True)
        else:
            os.replace(temporary, final_path)
        return web.json_response({"source": _source_payload(final_path, field.filename, media_type, hex_digest, size)})
    except Exception as exc:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        return web.json_response({"error": str(exc)}, status=400)


@PromptServer.instance.routes.post("/minimax_h3_prompt_enhancer/references/probe")
async def minimax_h3_reference_probe(request):
    """Report whether a Director-owned annotated input still exists and still matches its digest."""
    try:
        payload = await request.json()
        annotated = str(payload.get("file", ""))
        expected = str(payload.get("sha256", ""))
        prefix, suffix = f"{SOURCE_SUBFOLDER}/", " [input]"
        if not annotated.startswith(prefix) or not annotated.endswith(suffix):
            raise ValueError("Probe accepts only Reference Director input files.")
        name = annotated[len(prefix):-len(suffix)]
        if Path(name).name != name:
            raise ValueError("Invalid reference filename.")
        path = (_reference_input_root() / name).resolve()
        path.relative_to(_reference_input_root())
        if not path.is_file():
            return web.json_response({"available": False, "matches": False})
        digest = await asyncio.to_thread(_sha256_file, path)
        return web.json_response({
            "available": True,
            "matches": not expected or digest == expected,
            "sha256": digest,
            "sizeBytes": path.stat().st_size,
        })
    except Exception as exc:
        return web.json_response({"error": str(exc)}, status=400)
