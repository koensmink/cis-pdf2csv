from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class MappingInputControl(BaseModel):
    control_id: str
    title: str
    profile: str = "Unknown"
    assessment: str = "Unknown"

    description: Optional[str] = None
    rationale: Optional[str] = None
    impact: Optional[str] = None
    audit: Optional[str] = None
    remediation: Optional[str] = None
    default_value: Optional[str] = None
    references: Optional[str] = None


class IntuneMapping(BaseModel):
    cis_id: str
    title: str
    implementation_type: str
    intune_area: str
    setting_name: str
    value: str
    confidence: float

    rule_id: str
    notes: Optional[str] = None


class MappingConflict(BaseModel):
    cis_id: str
    title: str
    selected_rule_id: str
    selected_implementation_type: str
    matched_rule_ids: List[str]
    matched_implementation_types: List[str]


class ResolverResult(BaseModel):
    mappings: List[IntuneMapping]
    conflicts: List[MappingConflict]
