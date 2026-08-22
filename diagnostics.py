# SPDX-License-Identifier: GPL-3.0-only
"""Stable structured diagnostics for prompt planning and validation."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any


DIAGNOSTIC_REPORT_SCHEMA_VERSION = 1
DIAGNOSTIC_CATALOG_VERSION = 1
MAX_EXCERPT_LENGTH = 160


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    ADVICE = "advice"
    INFO = "info"


class Category(str, Enum):
    SCHEMA = "schema"
    CONFIGURATION = "configuration"
    STRUCTURE = "structure"
    FIDELITY = "fidelity"
    CAMERA = "camera"
    APPEARANCE = "appearance"
    ENVIRONMENT = "environment"
    REFERENCE = "reference"
    TIMING = "timing"
    STYLE = "style"
    COACH = "coach"


class Basis(str, Enum):
    CONTRACT = "contract"
    CONFIGURATION = "configuration"
    DERIVED = "derived"
    HEURISTIC = "heuristic"


class LocationScope(str, Enum):
    INPUT = "input"
    CONFIGURATION = "configuration"
    OUTPUT = "output"


class ResourceKind(str, Enum):
    ASSET = "asset"
    SUBJECT = "subject"
    ENVIRONMENT = "environment"
    GENERATION = "generation"
    SHOT = "shot"
    CAMERA_CLAIM = "camera_claim"
    DIAGNOSTIC = "diagnostic"


class LegacyBucket(str, Enum):
    COVERAGE_GAPS = "coverageGaps"
    STYLE_COVERAGE_GAPS = "styleCoverageGaps"
    CONTENT_FORMAT_COVERAGE_GAPS = "contentFormatCoverageGaps"


class CameraAspect(str, Enum):
    MOTION = "motion"
    FRAMING = "framing"
    ANGLE = "angle"
    VIEWPOINT = "viewpoint"
    COMPOSITION = "composition"
    FOCUS = "focus"
    DISTANCE = "distance"
    STABILITY = "stability"
    LENS = "lens"
    PARALLAX = "parallax"


class EntityKind(str, Enum):
    SUBJECT = "subject"
    ENVIRONMENT = "environment"


class DiagnosticCode(str, Enum):
    MEDIA_MANIFEST_INVALID_JSON = "schema.media_manifest.invalid_json"
    MEDIA_MANIFEST_UNSUPPORTED_VERSION = "schema.media_manifest.unsupported_version"
    SHOT_PLAN_INVALID_JSON = "schema.shot_plan.invalid_json"
    SHOT_PLAN_UNSUPPORTED_VERSION = "schema.shot_plan.unsupported_version"
    ACTIVATION_UNKNOWN_RESOURCE = "reference.activation.unknown_resource"
    ACTIVATION_REQUIRED_EXCLUDED = "reference.activation.required_excluded"
    BINDING_MISSING = "reference.binding.missing"
    BINDING_DUPLICATE_SLOT = "reference.binding.duplicate_slot"
    BINDING_TYPE_MISMATCH = "reference.binding.type_mismatch"
    REFERENCE_CAPACITY_EXCEEDED = "reference.capacity.exceeded"
    OUTPUT_INACTIVE_LABEL = "reference.output.inactive_label"
    OUTPUT_ACTIVE_UNUSED = "reference.output.active_unused"
    APPEARANCE_STATE_CYCLE = "appearance.state.cycle"
    APPEARANCE_TRANSITION_FROM_MISMATCH = "appearance.transition.from_mismatch"
    APPEARANCE_TRANSITION_SUBJECT_ABSENT = "appearance.transition.subject_absent"
    APPEARANCE_IDENTITY_ILLEGAL_CHANGE = "appearance.identity.illegal_change"
    APPEARANCE_OUTPUT_TRANSITION_MISSING = "appearance.output.transition_missing"
    ENVIRONMENT_STATE_CYCLE = "environment.state.cycle"
    ENVIRONMENT_TRANSITION_FROM_MISMATCH = "environment.transition.from_mismatch"
    ENVIRONMENT_STATE_PERMANENT_MUTATION = "environment.state.permanent_mutation"
    ENVIRONMENT_OUTPUT_TRANSITION_MISSING = "environment.output.transition_missing"
    CAMERA_AUTHORITY_EXPLICIT_CONFLICT = "camera.authority.explicit_conflict"
    CAMERA_AUTHORITY_OUTPUT_CONTRADICTION = "camera.authority.output_contradiction"
    CAMERA_AUTHORITY_OUTPUT_AMBIGUOUS = "camera.authority.output_ambiguous"
    CAMERA_PATH_QUALIFIER_WITHOUT_MOTION = "camera.path.qualifier_without_motion"
    CAMERA_OUTPUT_CLAIM_MISSING = "camera.output.claim_missing"
    COACH_LOCOMOTION_UNDER_SPECIFIED = "coach.action.locomotion_under_specified"
    COACH_ORIENTATION_UNDER_SPECIFIED = "coach.action.orientation_under_specified"
    COACH_MANIPULATION_UNDER_SPECIFIED = "coach.action.manipulation_under_specified"
    COACH_AMBIGUOUS_PRONOUN = "coach.identity.ambiguous_pronoun"
    COACH_OPENING_DUPLICATE = "coach.action.opening_duplicate"
    COACH_WEAK_CUT = "coach.cut.weak"
    COACH_DIALOGUE_TIMING_PRESSURE = "coach.dialogue.timing_pressure"
    COACH_AESTHETIC_NOISE = "coach.prose.aesthetic_noise"


@dataclass(frozen=True)
class DiagnosticBlocks:
    valid: bool = False
    quality: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.valid, bool) or not isinstance(self.quality, bool):
            raise TypeError("diagnostic block flags must be booleans")

    def to_dict(self) -> dict[str, bool]:
        return {"valid": self.valid, "quality": self.quality}


@dataclass(frozen=True)
class DiagnosticDefinition:
    category: Category
    severity: Severity
    basis: Basis
    blocks: DiagnosticBlocks = DiagnosticBlocks()
    repair_priority: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.category, Category) or not isinstance(self.severity, Severity):
            raise TypeError("diagnostic definitions require Category and Severity values")
        if not isinstance(self.basis, Basis) or not isinstance(self.blocks, DiagnosticBlocks):
            raise TypeError("diagnostic definitions require Basis and DiagnosticBlocks values")
        if not isinstance(self.repair_priority, int) or isinstance(self.repair_priority, bool):
            raise TypeError("repair priority must be an integer")
        if not 0 <= self.repair_priority <= 100:
            raise ValueError("repair priority must be between 0 and 100")


_CONFIG_ERROR = DiagnosticDefinition(
    Category.CONFIGURATION, Severity.ERROR, Basis.CONFIGURATION, DiagnosticBlocks(valid=True),
)
_REFERENCE_ERROR = DiagnosticDefinition(
    Category.REFERENCE, Severity.ERROR, Basis.CONFIGURATION, DiagnosticBlocks(valid=True),
)
_APPEARANCE_ERROR = DiagnosticDefinition(
    Category.APPEARANCE, Severity.ERROR, Basis.CONFIGURATION, DiagnosticBlocks(valid=True),
)
_ENVIRONMENT_ERROR = DiagnosticDefinition(
    Category.ENVIRONMENT, Severity.ERROR, Basis.CONFIGURATION, DiagnosticBlocks(valid=True),
)
_COACH_ADVICE = DiagnosticDefinition(Category.COACH, Severity.ADVICE, Basis.HEURISTIC)


DIAGNOSTIC_CATALOG: Mapping[DiagnosticCode, DiagnosticDefinition] = MappingProxyType({
    DiagnosticCode.MEDIA_MANIFEST_INVALID_JSON: DiagnosticDefinition(
        Category.SCHEMA, Severity.ERROR, Basis.CONTRACT, DiagnosticBlocks(valid=True),
    ),
    DiagnosticCode.MEDIA_MANIFEST_UNSUPPORTED_VERSION: DiagnosticDefinition(
        Category.SCHEMA, Severity.ERROR, Basis.CONTRACT, DiagnosticBlocks(valid=True),
    ),
    DiagnosticCode.SHOT_PLAN_INVALID_JSON: DiagnosticDefinition(
        Category.SCHEMA, Severity.ERROR, Basis.CONTRACT, DiagnosticBlocks(valid=True),
    ),
    DiagnosticCode.SHOT_PLAN_UNSUPPORTED_VERSION: DiagnosticDefinition(
        Category.SCHEMA, Severity.ERROR, Basis.CONTRACT, DiagnosticBlocks(valid=True),
    ),
    DiagnosticCode.ACTIVATION_UNKNOWN_RESOURCE: _REFERENCE_ERROR,
    DiagnosticCode.ACTIVATION_REQUIRED_EXCLUDED: _REFERENCE_ERROR,
    DiagnosticCode.BINDING_MISSING: _REFERENCE_ERROR,
    DiagnosticCode.BINDING_DUPLICATE_SLOT: _REFERENCE_ERROR,
    DiagnosticCode.BINDING_TYPE_MISMATCH: _REFERENCE_ERROR,
    DiagnosticCode.REFERENCE_CAPACITY_EXCEEDED: _REFERENCE_ERROR,
    DiagnosticCode.OUTPUT_INACTIVE_LABEL: DiagnosticDefinition(
        Category.REFERENCE, Severity.ERROR, Basis.DERIVED, DiagnosticBlocks(valid=True),
    ),
    DiagnosticCode.OUTPUT_ACTIVE_UNUSED: DiagnosticDefinition(
        Category.REFERENCE, Severity.WARNING, Basis.DERIVED,
    ),
    DiagnosticCode.APPEARANCE_STATE_CYCLE: _APPEARANCE_ERROR,
    DiagnosticCode.APPEARANCE_TRANSITION_FROM_MISMATCH: _APPEARANCE_ERROR,
    DiagnosticCode.APPEARANCE_TRANSITION_SUBJECT_ABSENT: _APPEARANCE_ERROR,
    DiagnosticCode.APPEARANCE_IDENTITY_ILLEGAL_CHANGE: _APPEARANCE_ERROR,
    DiagnosticCode.APPEARANCE_OUTPUT_TRANSITION_MISSING: DiagnosticDefinition(
        Category.APPEARANCE, Severity.WARNING, Basis.DERIVED, DiagnosticBlocks(quality=True), 75,
    ),
    DiagnosticCode.ENVIRONMENT_STATE_CYCLE: _ENVIRONMENT_ERROR,
    DiagnosticCode.ENVIRONMENT_TRANSITION_FROM_MISMATCH: _ENVIRONMENT_ERROR,
    DiagnosticCode.ENVIRONMENT_STATE_PERMANENT_MUTATION: _ENVIRONMENT_ERROR,
    DiagnosticCode.ENVIRONMENT_OUTPUT_TRANSITION_MISSING: DiagnosticDefinition(
        Category.ENVIRONMENT, Severity.WARNING, Basis.DERIVED, DiagnosticBlocks(quality=True), 75,
    ),
    DiagnosticCode.CAMERA_AUTHORITY_EXPLICIT_CONFLICT: DiagnosticDefinition(
        Category.CAMERA, Severity.ERROR, Basis.CONFIGURATION, DiagnosticBlocks(valid=True),
    ),
    DiagnosticCode.CAMERA_AUTHORITY_OUTPUT_CONTRADICTION: DiagnosticDefinition(
        Category.CAMERA, Severity.ERROR, Basis.DERIVED, DiagnosticBlocks(valid=True), 90,
    ),
    DiagnosticCode.CAMERA_AUTHORITY_OUTPUT_AMBIGUOUS: DiagnosticDefinition(
        Category.CAMERA, Severity.ADVICE, Basis.HEURISTIC,
    ),
    DiagnosticCode.CAMERA_PATH_QUALIFIER_WITHOUT_MOTION: _CONFIG_ERROR,
    DiagnosticCode.CAMERA_OUTPUT_CLAIM_MISSING: DiagnosticDefinition(
        Category.CAMERA, Severity.WARNING, Basis.DERIVED, DiagnosticBlocks(quality=True), 80,
    ),
    DiagnosticCode.COACH_LOCOMOTION_UNDER_SPECIFIED: _COACH_ADVICE,
    DiagnosticCode.COACH_ORIENTATION_UNDER_SPECIFIED: _COACH_ADVICE,
    DiagnosticCode.COACH_MANIPULATION_UNDER_SPECIFIED: _COACH_ADVICE,
    DiagnosticCode.COACH_AMBIGUOUS_PRONOUN: _COACH_ADVICE,
    DiagnosticCode.COACH_OPENING_DUPLICATE: _COACH_ADVICE,
    DiagnosticCode.COACH_WEAK_CUT: _COACH_ADVICE,
    DiagnosticCode.COACH_DIALOGUE_TIMING_PRESSURE: _COACH_ADVICE,
    DiagnosticCode.COACH_AESTHETIC_NOISE: _COACH_ADVICE,
})


@dataclass(frozen=True)
class DiagnosticLocation:
    scope: LocationScope
    field: str
    generation_id: str | None = None
    shot_id: str | None = None
    shot_index: int | None = None
    section: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None
    excerpt: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.scope, LocationScope):
            raise TypeError("location scope must be a LocationScope")
        _require_text(self.field, "location field")
        for name, value in (("generation id", self.generation_id), ("shot id", self.shot_id),
                            ("section", self.section)):
            if value is not None:
                _require_text(value, name)
        for name, value in (("shot index", self.shot_index), ("start offset", self.start_offset),
                            ("end offset", self.end_offset)):
            if value is not None:
                if not isinstance(value, int) or isinstance(value, bool):
                    raise TypeError(f"{name} must be an integer")
                if value < 0:
                    raise ValueError(f"{name} cannot be negative")
        if self.end_offset is not None and self.start_offset is None:
            raise ValueError("end offset requires start offset")
        if self.start_offset is not None and self.end_offset is not None and self.end_offset < self.start_offset:
            raise ValueError("end offset cannot precede start offset")
        if self.excerpt is not None:
            if not isinstance(self.excerpt, str):
                raise TypeError("location excerpt must be a string")
            if len(self.excerpt) > MAX_EXCERPT_LENGTH:
                raise ValueError(f"location excerpt cannot exceed {MAX_EXCERPT_LENGTH} characters")

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"scope": self.scope.value, "field": self.field}
        optional = (
            ("generationId", self.generation_id), ("shotId", self.shot_id),
            ("shotIndex", self.shot_index), ("section", self.section),
            ("startOffset", self.start_offset), ("endOffset", self.end_offset),
            ("excerpt", self.excerpt),
        )
        result.update((key, value) for key, value in optional if value is not None)
        return result

    def fingerprint_dict(self) -> dict[str, Any]:
        result = self.to_dict()
        result.pop("excerpt", None)
        return result


@dataclass(frozen=True, order=True)
class DiagnosticResource:
    kind: ResourceKind
    id: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ResourceKind):
            raise TypeError("resource kind must be a ResourceKind")
        _require_text(self.id, "resource id")

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind.value, "id": self.id}


@dataclass(frozen=True)
class DiagnosticRepair:
    eligible: bool = False
    priority: int = 0
    instruction: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.eligible, bool):
            raise TypeError("repair eligibility must be a boolean")
        if not isinstance(self.priority, int) or isinstance(self.priority, bool):
            raise TypeError("repair priority must be an integer")
        if not 0 <= self.priority <= 100:
            raise ValueError("repair priority must be between 0 and 100")
        if self.eligible:
            _require_text(self.instruction, "eligible repair instruction", maximum=500)
        elif self.priority or self.instruction is not None:
            raise ValueError("ineligible repairs cannot carry priority or instructions")

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"eligible": self.eligible, "priority": self.priority}
        if self.instruction is not None:
            result["instruction"] = self.instruction
        return result


class SafeActionKind(str, Enum):
    CLEAR_SHOT_CAMERA = "clear_shot_camera"
    CLEAR_GLOBAL_CAMERA = "clear_global_camera"
    ACTIVATE_RESOURCE = "activate_resource"
    ADD_BINDING = "add_binding"
    ALIGN_TRANSITION_FROM_STATE = "align_transition_from_state"


@dataclass(frozen=True)
class ClearShotCameraAction:
    label: str
    shot_id: str
    aspects: tuple[CameraAspect, ...]
    kind: SafeActionKind = field(default=SafeActionKind.CLEAR_SHOT_CAMERA, init=False)

    def __post_init__(self) -> None:
        _require_text(self.label, "action label")
        _require_text(self.shot_id, "shot id")
        _validate_aspects(self.aspects)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind.value, "label": self.label, "shotId": self.shot_id,
                "aspects": [aspect.value for aspect in self.aspects]}


@dataclass(frozen=True)
class ClearGlobalCameraAction:
    label: str
    aspects: tuple[CameraAspect, ...]
    kind: SafeActionKind = field(default=SafeActionKind.CLEAR_GLOBAL_CAMERA, init=False)

    def __post_init__(self) -> None:
        _require_text(self.label, "action label")
        _validate_aspects(self.aspects)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind.value, "label": self.label,
                "aspects": [aspect.value for aspect in self.aspects]}


@dataclass(frozen=True)
class ActivateResourceAction:
    label: str
    generation_id: str
    resource: DiagnosticResource
    kind: SafeActionKind = field(default=SafeActionKind.ACTIVATE_RESOURCE, init=False)

    def __post_init__(self) -> None:
        _require_text(self.label, "action label")
        _require_text(self.generation_id, "generation id")
        if self.resource.kind not in {ResourceKind.ASSET, ResourceKind.SUBJECT, ResourceKind.ENVIRONMENT}:
            raise ValueError("activate_resource supports only asset, subject, or environment resources")

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind.value, "label": self.label, "generationId": self.generation_id,
                "resource": self.resource.to_dict()}


@dataclass(frozen=True)
class AddBindingAction:
    label: str
    generation_id: str
    asset_id: str
    slot_index: int
    kind: SafeActionKind = field(default=SafeActionKind.ADD_BINDING, init=False)

    def __post_init__(self) -> None:
        _require_text(self.label, "action label")
        _require_text(self.generation_id, "generation id")
        _require_text(self.asset_id, "asset id")
        if not isinstance(self.slot_index, int) or isinstance(self.slot_index, bool):
            raise TypeError("binding slot index must be an integer")
        if not 1 <= self.slot_index <= 9:
            raise ValueError("binding slot index must be between 1 and 9")

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind.value, "label": self.label, "generationId": self.generation_id,
                "assetId": self.asset_id, "slotIndex": self.slot_index}


@dataclass(frozen=True)
class AlignTransitionFromStateAction:
    label: str
    shot_id: str
    entity_kind: EntityKind
    entity_id: str
    state_id: str
    kind: SafeActionKind = field(default=SafeActionKind.ALIGN_TRANSITION_FROM_STATE, init=False)

    def __post_init__(self) -> None:
        _require_text(self.label, "action label")
        _require_text(self.shot_id, "shot id")
        if not isinstance(self.entity_kind, EntityKind):
            raise TypeError("transition action entity kind must be an EntityKind")
        _require_text(self.entity_id, "entity id")
        _require_text(self.state_id, "state id")

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind.value, "label": self.label, "shotId": self.shot_id,
                "entityKind": self.entity_kind.value, "entityId": self.entity_id, "stateId": self.state_id}


SafeAction = (
    ClearShotCameraAction | ClearGlobalCameraAction | ActivateResourceAction | AddBindingAction
    | AlignTransitionFromStateAction
)


@dataclass(frozen=True)
class Diagnostic:
    code: DiagnosticCode
    severity: Severity
    category: Category
    confidence: float
    basis: Basis
    blocks: DiagnosticBlocks
    repair: DiagnosticRepair
    message: str
    location: DiagnosticLocation
    related: tuple[DiagnosticResource, ...] = ()
    suggestions: tuple[str, ...] = ()
    actions: tuple[SafeAction, ...] = ()
    data: Mapping[str, Any] = field(default_factory=dict)
    legacy_bucket: LegacyBucket | None = None
    fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.code, DiagnosticCode):
            raise TypeError("code must be a DiagnosticCode")
        if not isinstance(self.severity, Severity) or not isinstance(self.category, Category):
            raise TypeError("diagnostic severity and category must use their enum values")
        if not isinstance(self.basis, Basis) or not isinstance(self.blocks, DiagnosticBlocks):
            raise TypeError("diagnostic basis and blocks must use structured values")
        if not isinstance(self.repair, DiagnosticRepair) or not isinstance(self.location, DiagnosticLocation):
            raise TypeError("diagnostic repair and location must use structured values")
        if self.legacy_bucket is not None and not isinstance(self.legacy_bucket, LegacyBucket):
            raise TypeError("legacy bucket must be a LegacyBucket")
        if not isinstance(self.related, tuple) or not isinstance(self.suggestions, tuple) or not isinstance(self.actions, tuple):
            raise TypeError("diagnostic related, suggestions, and actions must be tuples")
        definition = DIAGNOSTIC_CATALOG.get(self.code)
        if definition is None:
            raise ValueError(f"diagnostic code {self.code!r} is not registered")
        if (self.severity, self.category, self.basis, self.blocks) != (
            definition.severity, definition.category, definition.basis, definition.blocks,
        ):
            raise ValueError(f"diagnostic policy for {self.code.value} must come from the catalog")
        if not isinstance(self.confidence, (int, float)) or isinstance(self.confidence, bool):
            raise TypeError("diagnostic confidence must be numeric")
        if not 0 <= self.confidence <= 1 or not math.isfinite(self.confidence):
            raise ValueError("diagnostic confidence must be a finite number between 0 and 1")
        _require_text(self.message, "diagnostic message", maximum=500)
        if len(self.suggestions) > 3:
            raise ValueError("a diagnostic can contain at most three suggestions")
        for suggestion in self.suggestions:
            _require_text(suggestion, "diagnostic suggestion", maximum=300)
        if any(not isinstance(resource, DiagnosticResource) for resource in self.related):
            raise TypeError("related values must be DiagnosticResource instances")
        if len(set(self.related)) != len(self.related):
            raise ValueError("related resources must be unique")
        if any(not isinstance(action, (
            ClearShotCameraAction, ClearGlobalCameraAction, ActivateResourceAction,
            AddBindingAction, AlignTransitionFromStateAction,
        )) for action in self.actions):
            raise TypeError("actions must be allowlisted safe action instances")
        if not isinstance(self.data, Mapping):
            raise TypeError("diagnostic data must be a mapping")
        frozen_data = _freeze_json(self.data, "diagnostic data")
        if "legacyBucket" in frozen_data:
            raise ValueError("legacyBucket is reserved diagnostic metadata")
        object.__setattr__(self, "data", frozen_data)
        object.__setattr__(self, "fingerprint", diagnostic_fingerprint(self.code, self.location, self.related))

    @classmethod
    def create(
        cls,
        code: DiagnosticCode,
        message: str,
        location: DiagnosticLocation,
        *,
        confidence: float = 1.0,
        repair_instruction: str | None = None,
        related: Iterable[DiagnosticResource] = (),
        suggestions: Iterable[str] = (),
        actions: Iterable[SafeAction] = (),
        data: Mapping[str, Any] | None = None,
        legacy_bucket: LegacyBucket | None = None,
    ) -> "Diagnostic":
        if not isinstance(code, DiagnosticCode):
            raise TypeError("code must be a DiagnosticCode")
        definition = DIAGNOSTIC_CATALOG[code]
        if definition.repair_priority:
            repair = DiagnosticRepair(True, definition.repair_priority, repair_instruction)
        else:
            if repair_instruction is not None:
                raise ValueError(f"{code.value} is not eligible for LLM repair")
            repair = DiagnosticRepair()
        return cls(
            code=code,
            severity=definition.severity,
            category=definition.category,
            confidence=confidence,
            basis=definition.basis,
            blocks=definition.blocks,
            repair=repair,
            message=message,
            location=location,
            related=tuple(related),
            suggestions=tuple(suggestions),
            actions=tuple(actions),
            data=data or {},
            legacy_bucket=legacy_bucket,
        )

    def to_dict(self) -> dict[str, Any]:
        data = _thaw_json(self.data)
        if self.legacy_bucket is not None:
            data["legacyBucket"] = self.legacy_bucket.value
        return {
            "code": self.code.value,
            "severity": self.severity.value,
            "category": self.category.value,
            "confidence": self.confidence,
            "basis": self.basis.value,
            "blocks": self.blocks.to_dict(),
            "repair": self.repair.to_dict(),
            "message": self.message,
            "location": self.location.to_dict(),
            "related": [resource.to_dict() for resource in self.related],
            "suggestions": list(self.suggestions),
            "actions": [action.to_dict() for action in self.actions],
            "data": data,
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True)
class LegacyDiagnosticProjection:
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    coverage_gaps: tuple[str, ...]
    style_coverage_gaps: tuple[str, ...]
    content_format_coverage_gaps: tuple[str, ...]
    valid: bool
    quality_valid: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "qualityValid": self.quality_valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "coverageGaps": list(self.coverage_gaps),
            "styleCoverageGaps": list(self.style_coverage_gaps),
            "contentFormatCoverageGaps": list(self.content_format_coverage_gaps),
        }


class DiagnosticCollector:
    def __init__(self, diagnostics: Iterable[Diagnostic] = ()) -> None:
        self._diagnostics: list[Diagnostic] = []
        self._fingerprints: set[str] = set()
        self._suppressed_coach = 0
        self.extend(diagnostics)

    @property
    def diagnostics(self) -> tuple[Diagnostic, ...]:
        return tuple(self._diagnostics)

    @property
    def suppressed_coach(self) -> int:
        return self._suppressed_coach

    def add(self, diagnostic: Diagnostic) -> bool:
        if not isinstance(diagnostic, Diagnostic):
            raise TypeError("collector accepts Diagnostic instances")
        if diagnostic.fingerprint in self._fingerprints:
            return False
        self._fingerprints.add(diagnostic.fingerprint)
        self._diagnostics.append(diagnostic)
        return True

    def extend(self, diagnostics: Iterable[Diagnostic]) -> None:
        for diagnostic in diagnostics:
            self.add(diagnostic)

    def emit(
        self,
        code: DiagnosticCode,
        message: str,
        location: DiagnosticLocation,
        **details: Any,
    ) -> Diagnostic:
        diagnostic = Diagnostic.create(code, message, location, **details)
        self.add(diagnostic)
        return diagnostic

    def suppress_coach(self, count: int = 1) -> None:
        if not isinstance(count, int) or isinstance(count, bool):
            raise TypeError("suppressed coach count must be an integer")
        if count < 0:
            raise ValueError("suppressed coach count cannot be negative")
        self._suppressed_coach += count

    def legacy_projection(self) -> LegacyDiagnosticProjection:
        errors: list[str] = []
        warnings: list[str] = []
        gaps = {bucket: [] for bucket in LegacyBucket}
        for diagnostic in self._diagnostics:
            if diagnostic.blocks.valid:
                errors.append(diagnostic.message)
            elif diagnostic.legacy_bucket is not None:
                gaps[diagnostic.legacy_bucket].append(diagnostic.message)
            elif diagnostic.severity is Severity.WARNING:
                warnings.append(diagnostic.message)
        valid = not any(diagnostic.blocks.valid for diagnostic in self._diagnostics)
        quality_valid = valid and not any(diagnostic.blocks.quality for diagnostic in self._diagnostics)
        return LegacyDiagnosticProjection(
            errors=tuple(errors),
            warnings=tuple(warnings),
            coverage_gaps=tuple(gaps[LegacyBucket.COVERAGE_GAPS]),
            style_coverage_gaps=tuple(gaps[LegacyBucket.STYLE_COVERAGE_GAPS]),
            content_format_coverage_gaps=tuple(gaps[LegacyBucket.CONTENT_FORMAT_COVERAGE_GAPS]),
            valid=valid,
            quality_valid=quality_valid,
        )

    def to_report(self) -> dict[str, Any]:
        counts = {severity: 0 for severity in Severity}
        for diagnostic in self._diagnostics:
            counts[diagnostic.severity] += 1
        projection = self.legacy_projection()
        return {
            "schemaVersion": DIAGNOSTIC_REPORT_SCHEMA_VERSION,
            "catalogVersion": DIAGNOSTIC_CATALOG_VERSION,
            "summary": {
                "errors": counts[Severity.ERROR],
                "warnings": counts[Severity.WARNING],
                "advice": counts[Severity.ADVICE],
                "info": counts[Severity.INFO],
                "suppressedCoach": self._suppressed_coach,
                "valid": projection.valid,
                "qualityValid": projection.quality_valid,
            },
            "diagnostics": [diagnostic.to_dict() for diagnostic in self._diagnostics],
        }

    def digest(self) -> str:
        return diagnostic_report_digest(self.to_report())


def diagnostic_fingerprint(
    code: DiagnosticCode,
    location: DiagnosticLocation,
    related: Iterable[DiagnosticResource] = (),
) -> str:
    if not isinstance(code, DiagnosticCode):
        raise TypeError("code must be a DiagnosticCode")
    resources = sorted((resource.to_dict() for resource in related), key=lambda item: (item["kind"], item["id"]))
    payload = {"code": code.value, "location": location.fingerprint_dict(), "related": resources}
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def diagnostic_report_digest(report: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(report).encode("utf-8")).hexdigest()


def compact_excerpt(value: str, maximum: int = MAX_EXCERPT_LENGTH) -> str:
    if maximum < 1 or maximum > MAX_EXCERPT_LENGTH:
        raise ValueError(f"excerpt maximum must be between 1 and {MAX_EXCERPT_LENGTH}")
    text = " ".join(str(value).split())
    if len(text) <= maximum:
        return text
    if maximum == 1:
        return "…"
    return text[:maximum - 1].rstrip() + "…"


def _require_text(value: str | None, name: str, maximum: int | None = None) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    if maximum is not None and len(value) > maximum:
        raise ValueError(f"{name} cannot exceed {maximum} characters")


def _validate_aspects(aspects: tuple[CameraAspect, ...]) -> None:
    if not isinstance(aspects, tuple):
        raise TypeError("camera action aspects must be a tuple")
    if not aspects:
        raise ValueError("camera action requires at least one aspect")
    if any(not isinstance(aspect, CameraAspect) for aspect in aspects):
        raise TypeError("camera action aspects must be CameraAspect values")
    if len(set(aspects)) != len(aspects):
        raise ValueError("camera action aspects must be unique")


def _freeze_json(value: Any, name: str) -> Any:
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{name} keys must be strings")
            frozen[key] = _freeze_json(item, name)
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item, name) for item in value)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise TypeError(f"{name} must contain only JSON-compatible values")


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
