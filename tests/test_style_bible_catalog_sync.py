import re
from pathlib import Path

from content_formats import CONTENT_FORMAT_PROFILES


ROOT = Path(__file__).resolve().parents[1]


def test_style_bible_content_format_tokens_match_runtime_catalog():
    source = (ROOT / "docs" / "style_bible_and_cinematography.md").read_text(encoding="utf-8")
    section = re.search(
        r"## Content Format Catalog \(18 Profiles\)\s+(.*?)\s+---",
        source,
        re.DOTALL,
    )
    assert section, "Content Format Catalog section is present"
    documented = set(re.findall(r"`([a-z0-9_]+)`", section.group(1)))
    assert documented == set(CONTENT_FORMAT_PROFILES)
