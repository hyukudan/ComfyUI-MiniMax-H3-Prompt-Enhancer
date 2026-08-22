# SPDX-License-Identifier: GPL-3.0-only
"""Deterministic camera ownership by shot, phase, and aspect."""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any

try:
    from .camera_state import resolve_camera_end
    from .diagnostics import (
        CameraAspect,
        DiagnosticCode,
        DiagnosticCollector,
        DiagnosticLocation,
        DiagnosticResource,
        LocationScope,
        ResourceKind,
    )
except ImportError:
    from camera_state import resolve_camera_end
    from diagnostics import (
        CameraAspect,
        DiagnosticCode,
        DiagnosticCollector,
        DiagnosticLocation,
        DiagnosticResource,
        LocationScope,
        ResourceKind,
    )


class CameraPhase(str, Enum):
    START = "start"
    PATH = "path"
    END = "end"
    WHOLE_SHOT = "whole_shot"


class CameraSourceKind(str, Enum):
    SOURCE_PROMPT = "source_prompt"
    VIDEO_REFERENCE = "video_reference"
    SHOT_PLAN = "shot_plan"
    GLOBAL_CINEMATOGRAPHY = "global_cinematography"
    GENERATED_PROSE = "generated_prose"
    CREATIVE_TREATMENT = "creative_treatment"


CAMERA_AUTHORITY = MappingProxyType({
    CameraSourceKind.SOURCE_PROMPT: 100,
    CameraSourceKind.VIDEO_REFERENCE: 90,
    CameraSourceKind.SHOT_PLAN: 80,
    CameraSourceKind.GLOBAL_CINEMATOGRAPHY: 60,
    CameraSourceKind.GENERATED_PROSE: 40,
    CameraSourceKind.CREATIVE_TREATMENT: 20,
})


class ShadowReason(str, Enum):
    SHOT_OVERRIDES_GLOBAL = "shot_overrides_global"
    LOWER_AUTHORITY = "lower_authority"
    COMPATIBLE = "compatible"


@dataclass(frozen=True)
class CameraClaim:
    shot_id: str
    aspect: CameraAspect
    phase: CameraPhase
    value: Any
    source_kind: CameraSourceKind
    source_id: str
    confidence: float
    location: DiagnosticLocation
    authority: int = field(init=False)
    value_key: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _require_id(self.shot_id, "claim shot id")
        _require_id(self.source_id, "claim source id")
        if not isinstance(self.aspect, CameraAspect):
            raise TypeError("claim aspect must be a CameraAspect")
        if not isinstance(self.phase, CameraPhase):
            raise TypeError("claim phase must be a CameraPhase")
        if not isinstance(self.source_kind, CameraSourceKind):
            raise TypeError("claim source kind must be a CameraSourceKind")
        if not isinstance(self.location, DiagnosticLocation):
            raise TypeError("claim location must be a DiagnosticLocation")
        if not isinstance(self.confidence, (int, float)) or isinstance(self.confidence, bool):
            raise TypeError("claim confidence must be numeric")
        if not 0 <= self.confidence <= 1 or not math.isfinite(self.confidence):
            raise ValueError("claim confidence must be finite and between 0 and 1")
        value_key = _canonical_json(self.value)
        object.__setattr__(self, "value", _freeze_json(json.loads(value_key)))
        object.__setattr__(self, "value_key", value_key)
        object.__setattr__(self, "authority", CAMERA_AUTHORITY[self.source_kind])

    @property
    def claim_id(self) -> str:
        return ":".join((
            self.source_kind.value, self.source_id, self.shot_id, self.phase.value, self.aspect.value,
        ))

    def to_dict(self) -> dict[str, Any]:
        return {
            "shotId": self.shot_id,
            "aspect": self.aspect.value,
            "phase": self.phase.value,
            "value": _thaw_json(self.value),
            "sourceKind": self.source_kind.value,
            "sourceId": self.source_id,
            "authority": self.authority,
            "confidence": self.confidence,
            "location": self.location.to_dict(),
        }


@dataclass(frozen=True)
class CameraOwner:
    shot_id: str
    phase: CameraPhase
    aspect: CameraAspect
    claim: CameraClaim
    supporting_claims: tuple[CameraClaim, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "shotId": self.shot_id,
            "phase": self.phase.value,
            "aspect": self.aspect.value,
            "claim": self.claim.to_dict(),
            "supportingClaims": [item.to_dict() for item in self.supporting_claims],
        }


@dataclass(frozen=True)
class ShadowedCameraClaim:
    winner: CameraClaim
    shadowed: CameraClaim
    phase: CameraPhase
    reason: ShadowReason

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase.value,
            "reason": self.reason.value,
            "winner": self.winner.to_dict(),
            "shadowed": self.shadowed.to_dict(),
        }


@dataclass(frozen=True)
class CameraConflict:
    shot_id: str
    phase: CameraPhase
    aspect: CameraAspect
    winner: CameraClaim
    competing: CameraClaim

    def to_dict(self) -> dict[str, Any]:
        return {
            "shotId": self.shot_id,
            "phase": self.phase.value,
            "aspect": self.aspect.value,
            "winner": self.winner.to_dict(),
            "competing": self.competing.to_dict(),
        }


@dataclass(frozen=True)
class CameraAuthorityResolution:
    owners: tuple[CameraOwner, ...]
    shadowed: tuple[ShadowedCameraClaim, ...]
    conflicts: tuple[CameraConflict, ...]

    @property
    def valid(self) -> bool:
        return not self.conflicts

    def owner_for(
        self,
        shot_id: str,
        phase: CameraPhase,
        aspect: CameraAspect,
    ) -> CameraOwner | None:
        exact = next((
            owner for owner in self.owners
            if owner.shot_id == shot_id and owner.phase is phase and owner.aspect is aspect
        ), None)
        if exact is not None or phase is CameraPhase.WHOLE_SHOT:
            return exact
        return next((
            owner for owner in self.owners
            if owner.shot_id == shot_id and owner.phase is CameraPhase.WHOLE_SHOT and owner.aspect is aspect
        ), None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "owners": [owner.to_dict() for owner in self.owners],
            "shadowed": [item.to_dict() for item in self.shadowed],
            "conflicts": [conflict.to_dict() for conflict in self.conflicts],
        }


def resolve_camera_authority(
    claims: Iterable[CameraClaim],
    collector: DiagnosticCollector | None = None,
) -> CameraAuthorityResolution:
    """Resolve owners without inventing defaults for absent camera aspects."""
    collected = tuple(claims)
    if any(not isinstance(claim, CameraClaim) for claim in collected):
        raise TypeError("camera authority accepts CameraClaim instances")
    diagnostic_collector = collector if collector is not None else DiagnosticCollector()
    owners: list[CameraOwner] = []
    shadowed: list[ShadowedCameraClaim] = []
    conflicts: list[CameraConflict] = []
    for shot_id, aspect, phase, group in _resolution_groups(collected):
        ordered = sorted(group, key=_claim_sort_key)
        winner = ordered[0]
        supporting: list[CameraClaim] = []
        seen_claims = {(winner.source_kind, winner.source_id, winner.value_key)}
        for competing in ordered[1:]:
            identity = (competing.source_kind, competing.source_id, competing.value_key)
            if identity in seen_claims:
                continue
            seen_claims.add(identity)
            compatible = camera_values_compatible(winner.value, competing.value)
            if compatible:
                supporting.append(competing)
                if winner.value_key != competing.value_key:
                    shadowed.append(ShadowedCameraClaim(winner, competing, phase, ShadowReason.COMPATIBLE))
                continue
            if _explicit_conflict(winner.source_kind, competing.source_kind):
                conflict = CameraConflict(shot_id, phase, aspect, winner, competing)
                conflicts.append(conflict)
                _emit_conflict(diagnostic_collector, conflict)
                continue
            reason = (
                ShadowReason.SHOT_OVERRIDES_GLOBAL
                if {winner.source_kind, competing.source_kind} == {
                    CameraSourceKind.SHOT_PLAN, CameraSourceKind.GLOBAL_CINEMATOGRAPHY,
                }
                else ShadowReason.LOWER_AUTHORITY
            )
            shadowed.append(ShadowedCameraClaim(winner, competing, phase, reason))
        owners.append(CameraOwner(shot_id, phase, aspect, winner, tuple(supporting)))
    return CameraAuthorityResolution(tuple(owners), tuple(shadowed), tuple(conflicts))


def claims_from_shot_plan(shot_plan: Mapping[str, Any]) -> tuple[CameraClaim, ...]:
    if shot_plan.get("schemaVersion") != 2:
        return ()
    claims: list[CameraClaim] = []
    for index, shot in enumerate(shot_plan.get("shots", ())):
        if not isinstance(shot, Mapping):
            continue
        shot_id = str(shot.get("id", ""))
        base_field = f"shot_plan_json.shots.{index}"
        start = shot.get("cameraStart", {})
        if isinstance(start, Mapping):
            claims.extend(_frame_claims(
                shot_id, CameraPhase.START, start, CameraSourceKind.SHOT_PLAN,
                f"shot:{shot_id}", base_field + ".cameraStart",
            ))
        end_delta = shot.get("cameraEnd", {})
        if isinstance(end_delta, Mapping):
            end = resolve_camera_end(start if isinstance(start, Mapping) else {}, end_delta)
            claims.extend(_frame_claims(
                shot_id, CameraPhase.END, end, CameraSourceKind.SHOT_PLAN,
                f"shot:{shot_id}", base_field + ".cameraEnd",
            ))
        elif start:
            claims.extend(_frame_claims(
                shot_id, CameraPhase.END, start, CameraSourceKind.SHOT_PLAN,
                f"shot:{shot_id}", base_field + ".cameraStart",
            ))
        path = shot.get("cameraPath")
        if isinstance(path, Mapping) and path.get("motionType"):
            claims.append(CameraClaim(
                shot_id, CameraAspect.MOTION, CameraPhase.PATH, dict(path),
                CameraSourceKind.SHOT_PLAN, f"shot:{shot_id}", 1.0,
                DiagnosticLocation(LocationScope.CONFIGURATION, base_field + ".cameraPath", shot_id=shot_id,
                                   shot_index=index),
            ))
    return tuple(claims)


def claims_from_global_cinematography(
    cinematography: Mapping[str, Any],
    shot_ids: Iterable[str],
) -> tuple[CameraClaim, ...]:
    claims: list[CameraClaim] = []
    values: list[tuple[CameraAspect, Any, str]] = []
    simple_fields = (
        ("shotScale", CameraAspect.FRAMING),
        ("cameraAngle", CameraAspect.ANGLE),
        ("cameraViewpoint", CameraAspect.VIEWPOINT),
        ("depthOfField", CameraAspect.FOCUS),
    )
    for field_name, aspect in simple_fields:
        value = cinematography.get(field_name)
        if value not in (None, "", "none", "auto"):
            values.append((aspect, value, field_name))
    motion = cinematography.get("cameraMotion")
    if motion not in (None, "", "none", "auto"):
        motion_value = {"motionType": motion}
        for field_name, output_name in (("cameraAmplitude", "amplitude"), ("cameraSpeed", "speed")):
            value = cinematography.get(field_name)
            if value not in (None, "", "none", "auto"):
                motion_value[output_name] = value
        values.append((CameraAspect.MOTION, motion_value, "cameraMotion"))
    lens_value = {
        key: cinematography[key]
        for key in ("optics", "lensEffects")
        if cinematography.get(key) not in (None, "", "none", "auto")
    }
    if lens_value:
        values.append((CameraAspect.LENS, lens_value, "optics"))
    for shot_id in shot_ids:
        for aspect, value, field_name in values:
            claims.append(CameraClaim(
                str(shot_id), aspect, CameraPhase.WHOLE_SHOT, value,
                CameraSourceKind.GLOBAL_CINEMATOGRAPHY, "cinematography:global", 1.0,
                DiagnosticLocation(LocationScope.CONFIGURATION, f"cinematography_json.{field_name}",
                                   shot_id=str(shot_id)),
            ))
    return tuple(claims)


def claims_from_video_references(
    compiled_media_project: Mapping[str, Any],
    shot_plan: Mapping[str, Any],
) -> tuple[CameraClaim, ...]:
    """Grant video authority only when all five structural gates are present."""
    if compiled_media_project.get("schemaVersion") != 2 or shot_plan.get("schemaVersion") != 2:
        return ()
    project = compiled_media_project.get("project")
    if not isinstance(project, Mapping):
        return ()
    assets = {
        asset.get("id"): asset for asset in project.get("assets", ())
        if isinstance(asset, Mapping) and asset.get("type") == "video"
    }
    generations = compiled_media_project.get("generations", {})
    if not isinstance(generations, Mapping):
        return ()
    claims: list[CameraClaim] = []
    for shot_index, shot in enumerate(shot_plan.get("shots", ())):
        if not isinstance(shot, Mapping):
            continue
        shot_id = str(shot.get("id", ""))
        generation_id = str(shot.get("generationId", ""))
        resolution = generations.get(generation_id)
        if not isinstance(resolution, Mapping):
            continue
        active_ids = set(resolution.get("activeAssetIds", ()))
        input_map = resolution.get("inputMap", {})
        if not isinstance(input_map, Mapping):
            continue
        for use_index, reference_use in enumerate(shot.get("referenceUses", ())):
            if not isinstance(reference_use, Mapping) or reference_use.get("role") != "camera_transfer":
                continue
            asset_id = reference_use.get("assetId")
            asset = assets.get(asset_id)
            if not isinstance(asset, Mapping) or asset_id not in active_ids or asset_id not in input_map:
                continue
            transfer = asset.get("cameraTransfer")
            if not isinstance(transfer, Mapping):
                continue
            if transfer.get("enabled") is not True or transfer.get("role") != "camera_reference":
                continue
            allowed = set(transfer.get("aspects", ()))
            requested = reference_use.get("cameraAspects", ())
            if not isinstance(requested, (list, tuple)):
                continue
            for aspect_name in requested:
                if aspect_name not in allowed:
                    continue
                try:
                    aspect = CameraAspect(aspect_name)
                except ValueError:
                    continue
                claims.append(CameraClaim(
                    shot_id, aspect, CameraPhase.WHOLE_SHOT,
                    {"cameraReferenceAssetId": asset_id}, CameraSourceKind.VIDEO_REFERENCE,
                    f"video:{asset_id}", 1.0,
                    DiagnosticLocation(
                        LocationScope.CONFIGURATION,
                        f"shot_plan_json.shots.{shot_index}.referenceUses.{use_index}",
                        generation_id=generation_id, shot_id=shot_id, shot_index=shot_index,
                    ),
                ))
    return tuple(claims)


def validate_generated_camera_claims(
    authority: CameraAuthorityResolution,
    generated_claims: Iterable[CameraClaim],
    collector: DiagnosticCollector,
    *,
    contradiction_confidence: float = 0.75,
) -> tuple[str, ...]:
    """Validate generated prose against resolved owners without granting it authority."""
    if not isinstance(authority, CameraAuthorityResolution):
        raise TypeError("authority must be a CameraAuthorityResolution")
    if not isinstance(collector, DiagnosticCollector):
        raise TypeError("collector must be a DiagnosticCollector")
    if not isinstance(contradiction_confidence, (int, float)) or isinstance(contradiction_confidence, bool):
        raise TypeError("contradiction confidence must be numeric")
    if not 0 <= contradiction_confidence <= 1:
        raise ValueError("contradiction confidence must be between 0 and 1")
    if not authority.valid:
        return ()
    generated = tuple(generated_claims)
    if any(not isinstance(claim, CameraClaim) for claim in generated):
        raise TypeError("generated camera claims must be CameraClaim instances")
    if any(claim.source_kind is not CameraSourceKind.GENERATED_PROSE for claim in generated):
        raise ValueError("generated camera validation accepts only generated_prose claims")

    emitted: list[str] = []
    authoritative_owners = tuple(
        owner for owner in authority.owners
        if owner.claim.source_kind is not CameraSourceKind.GENERATED_PROSE
    )
    for owner in authoritative_owners:
        candidates = tuple(
            claim for claim in generated
            if claim.shot_id == owner.shot_id and claim.aspect is owner.aspect
            and claim.phase in {owner.phase, CameraPhase.WHOLE_SHOT}
        )
        compatible = tuple(
            claim for claim in candidates if camera_values_compatible(owner.claim.value, claim.value)
        )
        if compatible:
            continue
        if not candidates:
            diagnostic = collector.emit(
                DiagnosticCode.CAMERA_OUTPUT_CLAIM_MISSING,
                f"Shot {owner.shot_id!r} does not observably realize the required camera "
                f"{owner.aspect.value} for phase {owner.phase.value!r}.",
                DiagnosticLocation(
                    LocationScope.OUTPUT,
                    f"camera.{owner.phase.value}.{owner.aspect.value}",
                    shot_id=owner.shot_id,
                ),
                repair_instruction=(
                    f"State the resolved {owner.aspect.value} camera direction for shot {owner.shot_id!r} "
                    f"during phase {owner.phase.value!r} without changing its owner or value."
                ),
                related=(DiagnosticResource(ResourceKind.CAMERA_CLAIM, owner.claim.claim_id),),
                data={"ownerSourceKind": owner.claim.source_kind.value},
            )
            emitted.append(diagnostic.fingerprint)
            continue
        for claim in candidates:
            if claim.confidence >= contradiction_confidence:
                diagnostic = collector.emit(
                    DiagnosticCode.CAMERA_AUTHORITY_OUTPUT_CONTRADICTION,
                    f"Generated camera {owner.aspect.value} in shot {owner.shot_id!r} contradicts the "
                    f"resolved {owner.claim.source_kind.value} owner for phase {owner.phase.value!r}.",
                    _output_location(claim),
                    confidence=claim.confidence,
                    repair_instruction=(
                        f"Replace the contradictory generated {owner.aspect.value} with the resolved owner value "
                        f"for shot {owner.shot_id!r}, phase {owner.phase.value!r}."
                    ),
                    related=(
                        DiagnosticResource(ResourceKind.CAMERA_CLAIM, owner.claim.claim_id),
                        DiagnosticResource(ResourceKind.CAMERA_CLAIM, claim.claim_id),
                    ),
                    data={"phase": owner.phase.value, "aspect": owner.aspect.value},
                )
            else:
                diagnostic = collector.emit(
                    DiagnosticCode.CAMERA_AUTHORITY_OUTPUT_AMBIGUOUS,
                    f"Generated wording may imply a different camera {owner.aspect.value} in shot "
                    f"{owner.shot_id!r}; verify it against the resolved owner.",
                    _output_location(claim),
                    confidence=claim.confidence,
                    related=(
                        DiagnosticResource(ResourceKind.CAMERA_CLAIM, owner.claim.claim_id),
                        DiagnosticResource(ResourceKind.CAMERA_CLAIM, claim.claim_id),
                    ),
                    data={"phase": owner.phase.value, "aspect": owner.aspect.value},
                )
            emitted.append(diagnostic.fingerprint)
    return tuple(emitted)


def camera_values_compatible(first: Any, second: Any) -> bool:
    first_value = _thaw_json(first)
    second_value = _thaw_json(second)
    if _canonical_json(first_value) == _canonical_json(second_value):
        return True
    if isinstance(first_value, dict) and isinstance(second_value, dict):
        shared = set(first_value) & set(second_value)
        return bool(shared) and all(
            camera_values_compatible(first_value[key], second_value[key]) for key in shared
        )
    return False


def _frame_claims(
    shot_id: str,
    phase: CameraPhase,
    frame: Mapping[str, Any],
    source_kind: CameraSourceKind,
    source_id: str,
    field_name: str,
) -> list[CameraClaim]:
    values: list[tuple[CameraAspect, Any]] = []
    for key, aspect in (
        ("framing", CameraAspect.FRAMING), ("angle", CameraAspect.ANGLE),
        ("viewpoint", CameraAspect.VIEWPOINT), ("focus", CameraAspect.FOCUS),
    ):
        if key in frame:
            values.append((aspect, frame[key]))
    composition = {
        key: frame[key] for key in (
            "composition", "compositionNote", "primaryTarget", "secondaryTarget", "foregroundTarget",
        ) if key in frame
    }
    if composition:
        values.append((CameraAspect.COMPOSITION, composition))
    distance = {key: frame[key] for key in ("distance", "distanceNote") if key in frame}
    if distance:
        values.append((CameraAspect.DISTANCE, distance))
    return [
        CameraClaim(
            shot_id, aspect, phase, value, source_kind, source_id, 1.0,
            DiagnosticLocation(LocationScope.CONFIGURATION, field_name, shot_id=shot_id),
        )
        for aspect, value in values
    ]


def _resolution_groups(
    claims: tuple[CameraClaim, ...],
) -> list[tuple[str, CameraAspect, CameraPhase, tuple[CameraClaim, ...]]]:
    grouped: dict[tuple[str, CameraAspect], list[CameraClaim]] = {}
    for claim in claims:
        grouped.setdefault((claim.shot_id, claim.aspect), []).append(claim)
    result: list[tuple[str, CameraAspect, CameraPhase, tuple[CameraClaim, ...]]] = []
    for (shot_id, aspect), aspect_claims in sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1].value)):
        whole = tuple(claim for claim in aspect_claims if claim.phase is CameraPhase.WHOLE_SHOT)
        phases = sorted(
            {claim.phase for claim in aspect_claims if claim.phase is not CameraPhase.WHOLE_SHOT},
            key=lambda phase: (CameraPhase.START, CameraPhase.PATH, CameraPhase.END).index(phase),
        )
        if not phases:
            result.append((shot_id, aspect, CameraPhase.WHOLE_SHOT, whole))
            continue
        for phase in phases:
            specific = tuple(claim for claim in aspect_claims if claim.phase is phase)
            result.append((shot_id, aspect, phase, specific + whole))
    return result


def _claim_sort_key(claim: CameraClaim) -> tuple[Any, ...]:
    return (-claim.authority, claim.source_kind.value, claim.source_id, claim.value_key)


def _explicit_conflict(first: CameraSourceKind, second: CameraSourceKind) -> bool:
    pair = {first, second}
    if pair == {CameraSourceKind.SHOT_PLAN, CameraSourceKind.GLOBAL_CINEMATOGRAPHY}:
        return False
    if CameraSourceKind.VIDEO_REFERENCE in pair and pair <= {
        CameraSourceKind.VIDEO_REFERENCE, CameraSourceKind.SHOT_PLAN,
        CameraSourceKind.GLOBAL_CINEMATOGRAPHY, CameraSourceKind.SOURCE_PROMPT,
    }:
        return True
    if CameraSourceKind.SOURCE_PROMPT in pair and pair <= {
        CameraSourceKind.SOURCE_PROMPT, CameraSourceKind.VIDEO_REFERENCE,
        CameraSourceKind.SHOT_PLAN, CameraSourceKind.GLOBAL_CINEMATOGRAPHY,
    }:
        return True
    return first is second and first in {
        CameraSourceKind.SOURCE_PROMPT, CameraSourceKind.VIDEO_REFERENCE,
        CameraSourceKind.SHOT_PLAN, CameraSourceKind.GLOBAL_CINEMATOGRAPHY,
    }


def _emit_conflict(collector: DiagnosticCollector, conflict: CameraConflict) -> None:
    winner = conflict.winner
    competing = conflict.competing
    collector.emit(
        DiagnosticCode.CAMERA_AUTHORITY_EXPLICIT_CONFLICT,
        f"Camera {conflict.aspect.value} for shot {conflict.shot_id!r} phase {conflict.phase.value!r} "
        f"has incompatible explicit owners {winner.source_id!r} and {competing.source_id!r}.",
        DiagnosticLocation(
            LocationScope.CONFIGURATION,
            f"cameraAuthority.{conflict.phase.value}.{conflict.aspect.value}",
            shot_id=conflict.shot_id,
        ),
        related=(
            DiagnosticResource(ResourceKind.CAMERA_CLAIM, winner.claim_id),
            DiagnosticResource(ResourceKind.CAMERA_CLAIM, competing.claim_id),
        ),
        data={
            "winnerSourceKind": winner.source_kind.value,
            "competingSourceKind": competing.source_kind.value,
            "phase": conflict.phase.value,
            "aspect": conflict.aspect.value,
        },
    )


def _output_location(claim: CameraClaim) -> DiagnosticLocation:
    location = claim.location
    return DiagnosticLocation(
        LocationScope.OUTPUT,
        location.field,
        generation_id=location.generation_id,
        shot_id=location.shot_id or claim.shot_id,
        shot_index=location.shot_index,
        section=location.section,
        start_offset=location.start_offset,
        end_offset=location.end_offset,
        excerpt=location.excerpt,
    )


def _require_id(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise TypeError("camera claim values must be JSON-compatible") from exc


def _freeze_json(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value
