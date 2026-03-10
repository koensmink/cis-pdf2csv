from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from rich.console import Console
from rich.table import Table

from .exporters import (
    write_baseline_csv,
    write_conflicts_csv,
    write_intune_policies_json,
    write_manual_review_csv,
)
from .models import MappingInputControl
from .resolver import resolve_controls

console = Console()


def _load_controls_jsonl(path: Path) -> List[MappingInputControl]:
    controls: List[MappingInputControl] = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            controls.append(MappingInputControl(**json.loads(line)))

    return controls


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cis-intune-map",
        description="Map parsed CIS controls to Intune baseline artifacts",
    )
    parser.add_argument("input", help="Input controls JSONL exported by cis-pdf2csv")
    parser.add_argument("-o", "--output-dir", required=True, help="Output directory")
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    controls = _load_controls_jsonl(input_path)
    result = resolve_controls(controls)

    mappings = result.mappings
    conflicts = result.conflicts

    write_baseline_csv(mappings, output_dir / "baseline.csv")
    write_intune_policies_json(mappings, output_dir / "intune_policies.json")
    write_manual_review_csv(mappings, output_dir / "manual_review.csv")
    write_conflicts_csv(conflicts, output_dir / "conflicts.csv")

    manual_count = len([m for m in mappings if m.implementation_type == "manual_review"])

    table = Table(title="cis-intune-map summary")
    table.add_column("Controls", justify="right")
    table.add_column("Mapped", justify="right")
    table.add_column("Manual review", justify="right")
    table.add_column("Conflicts", justify="right")
    table.add_row(
        str(len(controls)),
        str(len(mappings) - manual_count),
        str(manual_count),
        str(len(conflicts)),
    )
    console.print(table)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
