# SPDX-License-Identifier: GPL-3.0-only
"""Same-origin ComfyUI API routes used by the prompt-enhancer frontend."""

from __future__ import annotations

import asyncio

from aiohttp import web
from server import PromptServer

from .prompt_enhancer import discover_models


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
