from __future__ import annotations

from typing import Iterable, List

from .models import IntuneMapping, MappingConflict, MappingInputControl, ResolverResult
from .rules import MappingRule, STARTER_RULES


IMPLEMENTATION_PRIORITY = {
    "endpoint_security": 0,
    "settings_catalog": 1,
    "administrative_template": 2,
    "custom_oma_uri": 3,
    "manual_review": 4,
}


def _manual_mapping(control: MappingInputControl) -> IntuneMapping:
    return IntuneMapping(
        cis_id=control.control_id,
        title=control.title,
        implementation_type="manual_review",
        intune_area="Manual Review",
        setting_name="Unmapped control",
        value="N/A",
        confidence=0.0,
        rule_id="fallback.manual_review",
        notes="No starter rule matched; requires analyst validation.",
    )


def resolve_control(
    control: MappingInputControl,
    rules: Iterable[MappingRule] = STARTER_RULES,
) -> tuple[IntuneMapping, MappingConflict | None]:
    matches: List[IntuneMapping] = []

    for rule in rules:
        if rule.matches(control):
            matches.append(rule.apply(control))

    if not matches:
        return _manual_mapping(control), None

    selected = sorted(
        matches,
        key=lambda m: (
            IMPLEMENTATION_PRIORITY.get(m.implementation_type, 99),
            -m.confidence,
            m.rule_id,
        ),
    )[0]

    conflict = None
    if len(matches) > 1:
        conflict = MappingConflict(
            cis_id=control.control_id,
            title=control.title,
            selected_rule_id=selected.rule_id,
            selected_implementation_type=selected.implementation_type,
            matched_rule_ids=[m.rule_id for m in matches],
            matched_implementation_types=[m.implementation_type for m in matches],
        )

    return selected, conflict


def resolve_controls(
    controls: Iterable[MappingInputControl],
    rules: Iterable[MappingRule] = STARTER_RULES,
) -> ResolverResult:
    mappings: List[IntuneMapping] = []
    conflicts: List[MappingConflict] = []

    for control in controls:
        mapping, conflict = resolve_control(control, rules=rules)
        mappings.append(mapping)

        if conflict:
            conflicts.append(conflict)

    return ResolverResult(mappings=mappings, conflicts=conflicts)
