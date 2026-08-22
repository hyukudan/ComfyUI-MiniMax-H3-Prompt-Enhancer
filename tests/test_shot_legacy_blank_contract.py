# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import pytest

from creative_treatments import parse_shot_plan


@pytest.mark.parametrize("legacy_blank", (False, True, "false", "true", " null "))
def test_legacy_boolean_and_null_shot_storage_is_the_neutral_empty_plan(legacy_blank):
    parsed = parse_shot_plan(legacy_blank, 5.0, mode="t2va")
    blank = parse_shot_plan("", 5.0, mode="t2va")
    assert parsed == blank
    assert parsed["schemaVersion"] == 1
    assert parsed["provided"] is False
    assert parsed["applied"] is False
    assert parsed["shots"] == []


@pytest.mark.parametrize("unsupported_scalar", (0, "0", '"false"', "[]"))
def test_other_shot_scalar_storage_values_remain_invalid(unsupported_scalar):
    with pytest.raises(ValueError, match="JSON object|blank, a JSON object string, or a mapping"):
        parse_shot_plan(unsupported_scalar, 5.0, mode="t2va")


@pytest.mark.parametrize(
    "invalid_source",
    (
        '{"schemaVersion":99,"shots":[]}',
        '{"schemaVersion":2,"shots":[',
        '{"schemaVersion":2,"timingMode":"auto","shots":[],"future":true}',
    ),
)
def test_future_malformed_and_unknown_shot_objects_remain_strict(invalid_source):
    with pytest.raises(ValueError):
        parse_shot_plan(invalid_source, 5.0, mode="t2va")
