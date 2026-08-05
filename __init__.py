# SPDX-License-Identifier: GPL-3.0-only
"""Standalone MiniMax H3 prompt enhancement nodes for ComfyUI."""

if __package__:
    from .prompt_enhancer_node import (
        MiniMaxH3PromptEnhancer,
        MiniMaxH3PromptGuideBuilder,
        MiniMaxH3PromptValidator,
    )

    NODE_CLASS_MAPPINGS = {
        "MiniMaxH3PromptGuideBuilder": MiniMaxH3PromptGuideBuilder,
        "MiniMaxH3PromptEnhancer": MiniMaxH3PromptEnhancer,
        "MiniMaxH3PromptValidator": MiniMaxH3PromptValidator,
    }
    NODE_DISPLAY_NAME_MAPPINGS = {
        "MiniMaxH3PromptGuideBuilder": "MiniMax H3 Prompt Guide Builder",
        "MiniMaxH3PromptEnhancer": "MiniMax H3 Prompt Enhancer",
        "MiniMaxH3PromptValidator": "MiniMax H3 Prompt Validator",
    }
else:  # pragma: no cover
    NODE_CLASS_MAPPINGS = {}
    NODE_DISPLAY_NAME_MAPPINGS = {}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
