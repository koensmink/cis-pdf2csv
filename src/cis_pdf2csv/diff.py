from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple


DIFF_FIELDS = [
    "title",
    "assessment",
    "applicability",
    "description",
    "rationale",
    "impact",
    "audit",
    "remediation",
    "default_value",
    "references",
]


def _load_jsonl(path: Path) -> List[dict]:
    rows: List[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _record_key(row: dict) -> Tuple[str, str, str]:
    return (
        row.get("benchmark_name", ""),
        row.get("profile", ""),
        row.get("control_id", ""),
    )


def _norm(v) -> str:
    if v is None:
        return ""
    if not isinstance(v, str):
        return str(v)
    return v.strip()


def _shorten(text: str, max_len: int = 240) -> str:
    text = _norm(text).replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def diff_records(old_rows: List[dict], new_rows: List[dict]) -> List[dict]:
    old_map: Dict[Tuple[str, str, str], dict] = {_record_key(r): r for r in old_rows}
    new_map: Dict[Tuple[str, str, str], dict] = {_record_key(r): r for r in new_rows}

    changes: List[dict] = []

    old_keys = set(old_map.keys())
    new_keys = set(new_map.keys())

    for key in sorted(new_keys - old_keys):
        r = new_map[key]
        changes.append({
            "change_type": "added",
            "benchmark_name": r.get("benchmark_name", ""),
            "old_benchmark_version": "",
            "new_benchmark_version": r.get("benchmark_version", ""),
            "profile": r.get("profile", ""),
            "control_id": r.get("control_id", ""),
            "fields_changed": "",
            "title_old": "",
            "title_new": r.get("title", ""),
            "old_block_text_sha256": "",
            "new_block_text_sha256": r.get("block_text_sha256", ""),
            "field_diffs": {},
        })

    for key in sorted(old_keys - new_keys):
        r = old_map[key]
        changes.append({
            "change_type": "removed",
            "benchmark_name": r.get("benchmark_name", ""),
            "old_benchmark_version": r.get("benchmark_version", ""),
            "new_benchmark_version": "",
            "profile": r.get("profile", ""),
            "control_id": r.get("control_id", ""),
            "fields_changed": "",
            "title_old": r.get("title", ""),
            "title_new": "",
            "old_block_text_sha256": r.get("block_text_sha256", ""),
            "new_block_text_sha256": "",
            "field_diffs": {},
        })

    for key in sorted(old_keys & new_keys):
        old = old_map[key]
        new = new_map[key]

        changed_fields = []
        field_diffs = {}

        for field in DIFF_FIELDS:
            old_val = _norm(old.get(field))
            new_val = _norm(new.get(field))

            if old_val != new_val:
                changed_fields.append(field)
                field_diffs[field] = {
                    "old": old_val,
                    "new": new_val,
                }

        if changed_fields:
            changes.append({
                "change_type": "changed",
                "benchmark_name": new.get("benchmark_name", ""),
                "old_benchmark_version": old.get("benchmark_version", ""),
                "new_benchmark_version": new.get("benchmark_version", ""),
                "profile": new.get("profile", ""),
                "control_id": new.get("control_id", ""),
                "fields_changed": ",".join(changed_fields),
                "title_old": old.get("title", ""),
                "title_new": new.get("title", ""),
                "old_block_text_sha256": old.get("block_text_sha256", ""),
                "new_block_text_sha256": new.get("block_text_sha256", ""),
                "field_diffs": field_diffs,
            })

    return changes


def write_csv(rows: List[dict], out_path: Path) -> None:
    fieldnames = [
        "change_type",
        "benchmark_name",
        "old_benchmark_version",
        "new_benchmark_version",
        "profile",
        "control_id",
        "fields_changed",
        "title_old",
        "title_new",
        "old_block_text_sha256",
        "new_block_text_sha256",
        "field_diff_summary",
    ]

    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            quoting=csv.QUOTE_ALL,
        )
        writer.writeheader()

        for row in rows:
            summary_parts = []
            for field, diff in row.get("field_diffs", {}).items():
                summary_parts.append(
                    f"{field}: OLD='{_shorten(diff.get('old', ''))}' NEW='{_shorten(diff.get('new', ''))}'"
                )

            writer.writerow({
                "change_type": row.get("change_type", ""),
                "benchmark_name": row.get("benchmark_name", ""),
                "old_benchmark_version": row.get("old_benchmark_version", ""),
                "new_benchmark_version": row.get("new_benchmark_version", ""),
                "profile": row.get("profile", ""),
                "control_id": row.get("control_id", ""),
                "fields_changed": row.get("fields_changed", ""),
                "title_old": row.get("title_old", ""),
                "title_new": row.get("title_new", ""),
                "old_block_text_sha256": row.get("old_block_text_sha256", ""),
                "new_block_text_sha256": row.get("new_block_text_sha256", ""),
                "field_diff_summary": " | ".join(summary_parts),
            })


def write_jsonl(rows: List[dict], out_path: Path) -> None:
    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_report(rows: List[dict], out_path: Path) -> None:
    added = [r for r in rows if r["change_type"] == "added"]
    removed = [r for r in rows if r["change_type"] == "removed"]
    changed = [r for r in rows if r["change_type"] == "changed"]

    field_counter = Counter()
    for row in changed:
        for field in row.get("field_diffs", {}).keys():
            field_counter[field] += 1

    lines: List[str] = []
    lines.append("# CIS Diff Report")
    lines.append("")
    lines.append(f"- Totaal wijzigingen: **{len(rows)}**")
    lines.append(f"- Added: **{len(added)}**")
    lines.append(f"- Removed: **{len(removed)}**")
    lines.append(f"- Changed: **{len(changed)}**")
    lines.append("")

    if changed:
        lines.append("## Meest gewijzigde velden")
        lines.append("")
        for field, count in field_counter.most_common():
            lines.append(f"- `{field}`: {count}")
        lines.append("")

        lines.append("## Overzicht van alle gewijzigde controls")
        lines.append("")
        for row in changed:
            lines.append(
                f"- `{row['control_id']}` ({row['profile']}): "
                f"{row.get('fields_changed', '')}"
            )
        lines.append("")

    if added:
        lines.append("## Overzicht van alle toegevoegde controls")
        lines.append("")
        for row in added:
            lines.append(
                f"- `{row['control_id']}` ({row['profile']}): {row.get('title_new', '')}"
            )
        lines.append("")

    if removed:
        lines.append("## Overzicht van alle verwijderde controls")
        lines.append("")
        for row in removed:
            lines.append(
                f"- `{row['control_id']}` ({row['profile']}): {row.get('title_old', '')}"
            )
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_full_report(rows: List[dict], out_path: Path) -> None:
    added = [r for r in rows if r["change_type"] == "added"]
    removed = [r for r in rows if r["change_type"] == "removed"]
    changed = [r for r in rows if r["change_type"] == "changed"]

    field_counter = Counter()
    for row in changed:
        for field in row.get("field_diffs", {}).keys():
            field_counter[field] += 1

    lines: List[str] = []
    lines.append("# CIS Diff Full Report")
    lines.append("")
    lines.append(f"- Totaal wijzigingen: **{len(rows)}**")
    lines.append(f"- Added: **{len(added)}**")
    lines.append(f"- Removed: **{len(removed)}**")
    lines.append(f"- Changed: **{len(changed)}**")
    lines.append("")

    if changed:
        lines.append("## Meest gewijzigde velden")
        lines.append("")
        for field, count in field_counter.most_common():
            lines.append(f"- `{field}`: {count}")
        lines.append("")

        lines.append("## Alle gewijzigde controls")
        lines.append("")
        for row in changed:
            lines.append(f"### `{row['control_id']}` ({row['profile']})")
            lines.append("")
            lines.append(f"- Oude versie: `{row.get('old_benchmark_version', '')}`")
            lines.append(f"- Nieuwe versie: `{row.get('new_benchmark_version', '')}`")
            lines.append(f"- Gewijzigde velden: `{row.get('fields_changed', '')}`")
            lines.append(f"- Oude titel: {row.get('title_old', '')}")
            lines.append(f"- Nieuwe titel: {row.get('title_new', '')}")
            lines.append("")

            field_diffs = row.get("field_diffs", {})
            for field, diff in field_diffs.items():
                lines.append(f"#### Veld: `{field}`")
                lines.append("")
                lines.append("**Oud:**")
                lines.append("")
                lines.append("```")
                lines.append(diff.get("old", ""))
                lines.append("```")
                lines.append("")
                lines.append("**Nieuw:**")
                lines.append("")
                lines.append("```")
                lines.append(diff.get("new", ""))
                lines.append("```")
                lines.append("")

    if added:
        lines.append("## Alle toegevoegde controls")
        lines.append("")
        for row in added:
            lines.append(
                f"- `{row['control_id']}` ({row['profile']}): {row.get('title_new', '')}"
            )
        lines.append("")

    if removed:
        lines.append("## Alle verwijderde controls")
        lines.append("")
        for row in removed:
            lines.append(
                f"- `{row['control_id']}` ({row['profile']}): {row.get('title_old', '')}"
            )
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Diff two cis-pdf2csv JSONL exports")
    p.add_argument("old_file", help="Old baseline JSONL")
    p.add_argument("new_file", help="New baseline JSONL")
    p.add_argument("-o", "--output", required=True, help="Output file path (csv or jsonl)")
    p.add_argument("--format", choices=["csv", "jsonl"], default=None)
    p.add_argument("--report", help="Optional markdown summary report output path")
    p.add_argument("--full-report", help="Optional markdown full report output path")

    args = p.parse_args(argv)

    old_path = Path(args.old_file)
    new_path = Path(args.new_file)
    out_path = Path(args.output)

    out_fmt = args.format or out_path.suffix.lower().lstrip(".")

    if out_fmt not in ("csv", "jsonl"):
        raise SystemExit(f"Unsupported output format: {out_fmt}")

    old_rows = _load_jsonl(old_path)
    new_rows = _load_jsonl(new_path)

    changes = diff_records(old_rows, new_rows)

    if out_fmt == "csv":
        write_csv(changes, out_path)
    else:
        write_jsonl(changes, out_path)

    if args.report:
        write_report(changes, Path(args.report))

    if args.full_report:
        write_full_report(changes, Path(args.full_report))

    print(f"changes: {len(changes)}")
    print(f"added: {sum(1 for r in changes if r['change_type'] == 'added')}")
    print(f"removed: {sum(1 for r in changes if r['change_type'] == 'removed')}")
    print(f"changed: {sum(1 for r in changes if r['change_type'] == 'changed')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
