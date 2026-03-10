from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from .models import IntuneMapping, MappingConflict


def write_baseline_csv(mappings: Iterable[IntuneMapping], out_path: Path) -> None:
    rows = list(mappings)
    fieldnames = [
        "cis_id",
        "title",
        "implementation_type",
        "intune_area",
        "setting_name",
        "value",
        "confidence",
        "rule_id",
        "notes",
    ]

    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.model_dump())


def write_manual_review_csv(mappings: Iterable[IntuneMapping], out_path: Path) -> None:
    manual = [m for m in mappings if m.implementation_type == "manual_review"]
    write_baseline_csv(manual, out_path)


def write_conflicts_csv(conflicts: Iterable[MappingConflict], out_path: Path) -> None:
    rows = list(conflicts)
    fieldnames = [
        "cis_id",
        "title",
        "selected_rule_id",
        "selected_implementation_type",
        "matched_rule_ids",
        "matched_implementation_types",
    ]

    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for row in rows:
            data = row.model_dump()
            data["matched_rule_ids"] = ";".join(data["matched_rule_ids"])
            data["matched_implementation_types"] = ";".join(data["matched_implementation_types"])
            writer.writerow(data)


def write_intune_policies_json(mappings: Iterable[IntuneMapping], out_path: Path) -> None:
    grouped: dict[str, list[dict]] = {}

    for mapping in mappings:
        area = mapping.intune_area
        grouped.setdefault(area, []).append(
            {
                "cis_id": mapping.cis_id,
                "title": mapping.title,
                "implementation_type": mapping.implementation_type,
                "setting_name": mapping.setting_name,
                "value": mapping.value,
                "confidence": mapping.confidence,
                "rule_id": mapping.rule_id,
            }
        )

    payload = {
        "policies": [
            {
                "intune_area": area,
                "settings": settings,
            }
            for area, settings in sorted(grouped.items())
        ]
    }

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
