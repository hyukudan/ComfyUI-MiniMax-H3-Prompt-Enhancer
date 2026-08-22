# SPDX-License-Identifier: GPL-3.0-only
"""Appearance and environment state inheritance for logical media projects."""

from __future__ import annotations

import hashlib
import json
from typing import Any


MAX_STATE_DEPTH = 8


def _issue(code: str, message: str, field: str, **data: Any) -> dict[str, Any]:
    return {"code": code, "message": message, "field": field, "data": data}


def validate_state_graph(
    states: list[dict[str, Any]],
    *,
    entity_kind: str,
    entity_id: str,
) -> list[dict[str, Any]]:
    """Validate references, cycles and the bounded inheritance depth."""
    table = {state.get("id"): state for state in states}
    issues: list[dict[str, Any]] = []
    code = f"{entity_kind}.state.cycle"
    for state in states:
        state_id = state["id"]
        parent = state.get("extends")
        field = f"{entity_kind}s.{entity_id}.states.{state_id}.extends"
        if parent and parent not in table:
            issues.append(_issue(code, f"State {state_id!r} extends unknown state {parent!r}", field))
            continue
        path: list[str] = []
        current = state_id
        while current:
            if current in path:
                cycle = path[path.index(current):] + [current]
                issues.append(_issue(code, f"State inheritance cycle: {' -> '.join(cycle)}", field, path=cycle))
                break
            path.append(current)
            if len(path) > MAX_STATE_DEPTH:
                issues.append(_issue(code, f"State {state_id!r} exceeds inheritance depth {MAX_STATE_DEPTH}", field, path=path))
                break
            current_state = table.get(current)
            current = str(current_state.get("extends", "")) if current_state else ""
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for issue in issues:
        unique[(issue["message"], issue["field"])] = issue
    return list(unique.values())


def resolve_state(states: list[dict[str, Any]], state_id: str, value_field: str) -> dict[str, Any]:
    """Merge a valid state chain from ancestor to child."""
    table = {state["id"]: state for state in states}
    chain: list[dict[str, Any]] = []
    seen: set[str] = set()
    current = state_id
    while current and current in table and current not in seen and len(chain) <= MAX_STATE_DEPTH:
        seen.add(current)
        chain.append(table[current])
        current = str(table[current].get("extends", ""))
    resolved: dict[str, Any] = {}
    sources: list[dict[str, Any]] = []
    controls: list[str] = []
    for state in reversed(chain):
        resolved.update(state.get(value_field, {}))
        for control in state.get("controls", ()):
            if control not in controls:
                controls.append(control)
        if state.get("source"):
            sources.append(state["source"])
    return {
        "stateId": state_id,
        "name": table.get(state_id, {}).get("name", state_id),
        value_field: resolved,
        "controls": controls,
        "sources": sources,
        "description": table.get(state_id, {}).get("description", ""),
    }


def compile_generation_states(project: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Resolve every generation's deterministic starting state and selected views."""
    subjects = {subject["id"]: subject for subject in project.get("subjects", ())}
    environments = {environment["id"]: environment for environment in project.get("environments", ())}
    issues: list[dict[str, Any]] = []
    resolved: dict[str, dict[str, Any]] = {}
    previous_subjects: dict[str, str] = {}
    previous_environments: dict[str, str] = {}
    previous_views: dict[str, list[str]] = {}

    for generation_index, generation in enumerate(sorted(project.get("generations", ()), key=lambda item: item["order"])):
        generation_id = generation["id"]
        subject_states = dict(previous_subjects) if generation_index else {
            subject_id: subject["baseAppearanceStateId"] for subject_id, subject in subjects.items()
        }
        environment_states = dict(previous_environments) if generation_index else {
            environment_id: environment["defaultStateId"] for environment_id, environment in environments.items()
        }
        environment_views = {key: list(value) for key, value in previous_views.items()}
        seen_subjects: set[str] = set()
        for selection in generation.get("subjectStates", ()):
            subject_id = selection["subjectId"]
            field = f"generations.{generation_id}.subjectStates"
            if subject_id in seen_subjects:
                issues.append(_issue("appearance.state.duplicate_selection", f"Subject {subject_id!r} has multiple initial-state selections", field))
                continue
            seen_subjects.add(subject_id)
            subject = subjects.get(subject_id)
            if subject is None:
                issues.append(_issue("appearance.state.unknown_subject", f"Unknown subject {subject_id!r}", field))
                continue
            policy = selection["policy"]
            if policy == "carry":
                if generation_index == 0:
                    issues.append(_issue("appearance.state.invalid_carry", "The first generation cannot carry subject state", field))
                state_id = previous_subjects.get(subject_id, subject["baseAppearanceStateId"])
            else:
                state_id = selection["stateId"]
                known = {state["id"] for state in subject["appearanceStates"]}
                if state_id not in known:
                    issues.append(_issue("appearance.state.unknown", f"Unknown appearance state {state_id!r} for subject {subject_id!r}", field))
                    continue
                if policy == "reset" and state_id != subject["baseAppearanceStateId"]:
                    issues.append(_issue("appearance.state.invalid_reset", f"Reset for subject {subject_id!r} must select its base state", field))
                previous = previous_subjects.get(subject_id)
                if generation_index and policy == "explicit" and previous and previous != state_id and not selection.get("reason"):
                    issues.append(_issue("appearance.state.discontinuity_reason", f"Explicit discontinuity for subject {subject_id!r} requires a reason", field))
            subject_states[subject_id] = state_id

        seen_environments: set[str] = set()
        for selection in generation.get("environmentStates", ()):
            environment_id = selection["environmentId"]
            field = f"generations.{generation_id}.environmentStates"
            if environment_id in seen_environments:
                issues.append(_issue("environment.state.duplicate_selection", f"Environment {environment_id!r} has multiple initial-state selections", field))
                continue
            seen_environments.add(environment_id)
            environment = environments.get(environment_id)
            if environment is None:
                issues.append(_issue("environment.state.unknown_environment", f"Unknown environment {environment_id!r}", field))
                continue
            policy = selection["policy"]
            if policy == "carry":
                if generation_index == 0:
                    issues.append(_issue("environment.state.invalid_carry", "The first generation cannot carry environment state", field))
                state_id = previous_environments.get(environment_id, environment["defaultStateId"])
            else:
                state_id = selection["stateId"]
                known = {state["id"] for state in environment["states"]}
                if state_id not in known:
                    issues.append(_issue("environment.state.unknown", f"Unknown environment state {state_id!r} for {environment_id!r}", field))
                    continue
                if policy == "reset" and state_id != environment["defaultStateId"]:
                    issues.append(_issue("environment.state.invalid_reset", f"Reset for environment {environment_id!r} must select its default state", field))
                previous = previous_environments.get(environment_id)
                if generation_index and policy == "explicit" and previous and previous != state_id and not selection.get("reason"):
                    issues.append(_issue("environment.state.discontinuity_reason", f"Explicit discontinuity for environment {environment_id!r} requires a reason", field))
            known_views = {view["id"] for view in environment["views"]}
            unknown_views = sorted(set(selection.get("viewIds", ())) - known_views)
            if unknown_views:
                issues.append(_issue("environment.view.unknown", f"Unknown views for environment {environment_id!r}: {unknown_views}", field))
            environment_states[environment_id] = state_id
            environment_views[environment_id] = list(selection.get("viewIds", ()))

        state_payload = {
            "subjects": subject_states,
            "environments": environment_states,
            "views": environment_views,
        }
        canonical = json.dumps(state_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        resolved[generation_id] = {
            **state_payload,
            "initialDigest": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        }
        previous_subjects = subject_states
        previous_environments = environment_states
        previous_views = environment_views
    return resolved, issues
