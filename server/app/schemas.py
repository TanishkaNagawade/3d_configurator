"""Canonical metadata schema (per instruction §6) — validated with pydantic.

Stable domain ids only; no Three.js UUID coupling (instruction §23).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0"


class Units(BaseModel):
    sourceLength: str
    runtimeLength: str
    sourceToRuntimeScale: float


class MassProperties(BaseModel):
    mass: float = 0.0
    density: float = 0.0
    volume: float = 0.0
    surfaceArea: float = 0.0
    centerOfGravity: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    inertiaTensor: list[float] = Field(default_factory=list)


class Bounds(BaseModel):
    min: list[float]
    max: list[float]


class Definition(BaseModel):
    definitionId: str
    modelType: Literal["part", "assembly"] = "part"
    name: str = ""
    sourceFile: str = ""
    logicalName: str = ""
    partNumber: str = ""
    description: str = ""
    parameters: dict = Field(default_factory=dict)
    units: str = ""
    materials: list = Field(default_factory=list)
    massProperties: MassProperties = Field(default_factory=MassProperties)
    bounds: Optional[Bounds] = None
    geometryRef: str = ""


class Occurrence(BaseModel):
    occurrenceId: str
    definitionId: str
    parentOccurrenceId: Optional[str] = None
    children: list[str] = Field(default_factory=list)
    componentPath: list[int] = Field(default_factory=list)
    transform: list[float]  # row-major 4x4 (16 numbers)
    visible: bool = True
    suppressed: bool = False
    skeleton: bool = False


class Mechanism(BaseModel):
    source: str = "creo"
    confidence: float = 0.0
    requiresReview: bool = True
    kind: str = "unknown"
    members: list[str] = Field(default_factory=list)
    axis: Optional[list[float]] = None
    limits: Optional[list[float]] = None


class Project(BaseModel):
    schemaVersion: str = SCHEMA_VERSION
    projectId: str = ""
    name: str = ""
    source: str = "Creo"
    rootAssemblyDefinitionId: str = ""
    units: Units
    definitions: dict[str, Definition] = Field(default_factory=dict)
    occurrences: dict[str, Occurrence] = Field(default_factory=dict)
    explodedStates: list[dict] = Field(default_factory=list)
    mechanisms: list[Mechanism] = Field(default_factory=list)
    workingPrinciple: list[dict] = Field(default_factory=list)
    conversion: dict = Field(default_factory=dict)


def validate_project(payload: dict) -> Project:
    """Raise pydantic.ValidationError on bad canonical payloads."""
    return Project.model_validate(payload)


def structural_check(p: Project) -> list[str]:
    """§15.1 structural validation — returns list of errors (empty == ok)."""
    errors: list[str] = []
    if p.rootAssemblyDefinitionId == "" and not p.definitions:
        errors.append("ROOT_ASSEMBLY_MISSING")
    for oid, occ in p.occurrences.items():
        if occ.definitionId not in p.definitions:
            errors.append(f"occurrence {oid} references missing definition {occ.definitionId}")
        if occ.parentOccurrenceId and occ.parentOccurrenceId not in p.occurrences:
            errors.append(f"occurrence {oid} has invalid parent {occ.parentOccurrenceId}")
        if len(occ.transform) != 16:
            errors.append(f"occurrence {oid} transform is not 4x4")
    ids = list(p.occurrences.keys())
    if len(ids) != len(set(ids)):
        errors.append("duplicate occurrence ids")
    return errors
