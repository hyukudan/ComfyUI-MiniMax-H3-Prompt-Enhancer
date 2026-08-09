# SPDX-License-Identifier: GPL-3.0-only
"""Standalone MiniMax H3 prompt enhancement nodes for ComfyUI."""

if __package__:
    from . import api_routes as _api_routes  # noqa: F401 - registers same-origin frontend routes
    from .prompt_enhancer_node import (
        MiniMaxH3GGUFPromptEnhancer,
        MiniMaxH3PromptEnhancer,
        MiniMaxH3PromptGuideBuilder,
        MiniMaxH3PromptValidator,
        MiniMaxH3UnloadGGUFServer,
        MiniMaxH3MediaManifestValidator,
        MiniMaxH3ChainedMultishotOutput,
        MiniMaxH3ShotSelector,
    )

    NODE_CLASS_MAPPINGS = {
        "MiniMaxH3PromptGuideBuilder": MiniMaxH3PromptGuideBuilder,
        "MiniMaxH3PromptEnhancer": MiniMaxH3PromptEnhancer,
        "MiniMaxH3GGUFPromptEnhancer": MiniMaxH3GGUFPromptEnhancer,
        "MiniMaxH3PromptValidator": MiniMaxH3PromptValidator,
        "MiniMaxH3UnloadGGUFServer": MiniMaxH3UnloadGGUFServer,
        "MiniMaxH3MediaManifestValidator": MiniMaxH3MediaManifestValidator,
        "MiniMaxH3ChainedMultishotOutput": MiniMaxH3ChainedMultishotOutput,
        "MiniMaxH3ShotSelector": MiniMaxH3ShotSelector,
    }
    NODE_DISPLAY_NAME_MAPPINGS = {
        "MiniMaxH3PromptGuideBuilder": "MiniMax H3 Prompt Guide Builder",
        "MiniMaxH3PromptEnhancer": "MiniMax H3 Prompt Enhancer",
        "MiniMaxH3GGUFPromptEnhancer": "MiniMax H3 GGUF Prompt Enhancer",
        "MiniMaxH3PromptValidator": "MiniMax H3 Prompt Validator",
        "MiniMaxH3UnloadGGUFServer": "MiniMax H3 Unload GGUF Prompt Model",
        "MiniMaxH3MediaManifestValidator": "MiniMax H3 Media Manifest Validator",
        "MiniMaxH3ChainedMultishotOutput": "MiniMax H3 Chained Multishot Output",
        "MiniMaxH3ShotSelector": "MiniMax H3 Shot Selector",
    }
else:  # pragma: no cover
    NODE_CLASS_MAPPINGS = {}
    NODE_DISPLAY_NAME_MAPPINGS = {}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
