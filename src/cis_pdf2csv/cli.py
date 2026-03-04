raise SystemExit(main())    args = p.parse_args(argv)    v = re.sub(r"[ \t]+", " ", v)

    return v.strip()


def _write_csv(records: List[ControlRecord], out_path: Path) -> None:
    fieldnames = list(ControlRecord.model_fields.keys())

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            quoting=csv.QUOTE_ALL,
        )

        writer.writeheader()

        for r in records:
            row = r.model_dump()
            row = {k: _clean_csv_value(v) for k, v in row.items()}
            writer.writerow(row)


def _write_jsonl(records: List[ControlRecord], out_path: Path) -> None:
    with out_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r.model_dump(), ensure_ascii=False) + "\n")


def main(argv: List[str] | None = None) -> int:

    p = argparse.ArgumentParser(
        prog="cis-pdf2csv",
        description="Parse CIS Benchmark PDF(s) into CSV/JSONL",
    )

    p.add_argument(
        "pdfs",
        nargs="+",
        help="Path(s) to CIS Benchmark PDF files (not stored in repo).",
    )

    p.add_argument(
        "-p",
        "--profile",
        default=None,
        help="Filter: L1, L2, or NG (default: all)",
    )

    p.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output file path (csv or jsonl)",
    )

    p.add_argument(
        "--format",
        choices=["csv", "jsonl"],
        default=None,
        help="Force output format (default: based on extension)",
    )

    args = p.parse_args(argv)

    out_path = Path(args.output)

    out_fmt = args.format or (out_path.suffix.lower().lstrip(".") if out_path.suffix else "csv")

    if out_fmt not in ("csv", "jsonl"):
        console.print(f"[red]Unsupported output format[/red]: {out_fmt}")
        return 2

    all_records: List[ControlRecord] = []

    for pdf in args.pdfs:
        controls = parse_controls(pdf, profile_filter=args.profile)

        for c in controls:
            all_records.append(ControlRecord(**c))

    # Deterministic ordering
    all_records.sort(key=lambda r: (r.benchmark_name, r.benchmark_version, r.control_id))

    if out_fmt == "csv":
        _write_csv(all_records, out_path)
    else:
        _write_jsonl(all_records, out_path)

    # Pretty summary
    t = Table(title="cis-pdf2csv summary")
    t.add_column("Benchmarks", justify="right")
    t.add_column("Controls", justify="right")
    t.add_column("Profile", justify="left")

    t.add_row(
        str(len(set((r.benchmark_name, r.benchmark_version) for r in all_records))),
        str(len(all_records)),
        str(args.profile or "ALL"),
    )

    console.print(t)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())    args = p.parse_args(argv)

    out_path = Path(args.output)
    out_fmt = args.format or (out_path.suffix.lower().lstrip(".") if out_path.suffix else "csv")
    if out_fmt not in ("csv", "jsonl"):
        console.print(f"[red]Unsupported output format[/red]: {out_fmt}")
        return 2

    all_records: List[ControlRecord] = []
    for pdf in args.pdfs:
        controls = parse_controls(pdf, profile_filter=args.profile)
        for c in controls:
            all_records.append(ControlRecord(**c))

    # Deterministic order: by benchmark then control_id
    all_records.sort(key=lambda r: (r.benchmark_name, r.benchmark_version, r.control_id))

    if out_fmt == "csv":
        _write_csv(all_records, out_path)
    else:
        _write_jsonl(all_records, out_path)

    # Pretty summary
    t = Table(title="cis-pdf2csv summary")
    t.add_column("Benchmarks", justify="right")
    t.add_column("Controls", justify="right")
    t.add_column("Profile", justify="left")
    t.add_row(str(len(set((r.benchmark_name, r.benchmark_version) for r in all_records))), str(len(all_records)), str(args.profile or "ALL"))
    console.print(t)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
