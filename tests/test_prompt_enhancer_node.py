# SPDX-License-Identifier: GPL-3.0-only

from prompt_enhancer_node import MiniMaxH3PromptGuideBuilder


def test_guide_builder_can_feed_an_existing_llm_node():
    system, user, mode = MiniMaxH3PromptGuideBuilder().build(
        'A detective enters a ramen shop and says "Good evening."', "t2va", 5.0, "",
    )
    assert "MiniMax H3" in system
    assert "TARGET DURATION: 5.000 seconds" in user
    assert '"Good evening."' in user
    assert mode == "t2va"
