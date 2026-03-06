
# cis-pdf2csv

Convert **CIS Benchmark PDF files** (primarily Windows Server benchmarks) into structured datasets and detect differences between benchmark versions.

The tool extracts CIS controls from PDF and exports them to **CSV or JSONL**, enabling automation, auditing and version comparison of CIS hardening baselines.

---

# Project purpose

CIS benchmarks are distributed as PDF documents.  
While readable for humans, they are difficult to:

- compare across benchmark versions
- process automatically
- integrate into governance tooling
- analyze in Excel / Power BI
- track changes between benchmark revisions

`cis-pdf2csv` creates a reproducible pipeline:

CIS PDF → parser → CSV / JSONL → diff → reports

---

# Features

- Parse **CIS Windows Server benchmark PDFs**
- Extract full control metadata including:
  - description
  - rationale
  - impact
  - audit
  - remediation
  - default value
  - references
- Filter controls by profile (`L1`, `L2`, `NG`)
- Export to:
  - CSV (Excel friendly)
  - JSONL (automation friendly)
- Generate **diffs between benchmark versions**
- Produce reports:
  - `changes.csv`
  - `report.md`
  - `report_full.md`
- Evidence-grade extraction with hashes and page references
- Hardened container runtime

---

# Example pipeline

```
CIS Benchmark PDF
        ↓
     parser.py
        ↓
   CSV / JSONL export
        ↓
      diff.py
        ↓
changes.csv / report.md / report_full.md
```

---

# Output fields

Example CSV/JSONL fields:

| Field | Description |
|------|-------------|
benchmark_name | Name of the CIS benchmark |
benchmark_version | Version extracted from PDF |
benchmark_date | Benchmark publication date |
control_id | CIS control ID |
profile | L1 / L2 / NG |
title | Control title |
assessment | Automated / Manual |
applicability | MS only / DC only etc |
description | Description |
rationale | Rationale |
impact | Impact |
audit | Audit procedure |
remediation | Remediation procedure |
default_value | Default value |
references | References |
page_start | Control start page |
page_end | Control end page |
source_pdf_sha256 | SHA256 of source PDF |
block_text_sha256 | SHA256 of control block |
parser_version | Parser version |
extracted_at_utc | Extraction timestamp |

---

# Installation

## Local (Python)

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m cis_pdf2csv --help
```

## Docker

Build container:

```
docker build --no-cache -t cis-pdf2csv .
```

---

# Usage

## Parse CIS benchmark

```
docker run --rm -v "$PWD:/work" -w /work cis-pdf2csv ./CIS_Microsoft_Windows_Server_2025_Benchmark_v2.0.0.pdf -p L1 -o out_l1.csv
```

Export JSONL:

```
docker run --rm -v "$PWD:/work" -w /work cis-pdf2csv ./benchmark.pdf -p L1 -o out.jsonl --format jsonl
```

---

# Diff between benchmark versions

Export baseline 1:

```
docker run --rm -v "$PWD:/work" -w /work cis-pdf2csv ./benchmark_v1.pdf -p L1 -o v1.jsonl --format jsonl
```

Export baseline 2:

```
docker run --rm -v "$PWD:/work" -w /work cis-pdf2csv ./benchmark_v2.pdf -p L1 -o v2.jsonl --format jsonl
```

Run diff:

```
docker run --rm -v "$PWD:/work" -w /work --entrypoint python cis-pdf2csv -m cis_pdf2csv.diff v1.jsonl v2.jsonl -o changes.csv --report report.md --full-report report_full.md
```

Example output:

```
changes: 365
added: 81
removed: 76
changed: 208
```

---

# Reports

## changes.csv

Machine readable overview of all changes.

## report.md

Summary report including:

- total changes
- added controls
- removed controls
- changed controls
- most frequently changed fields

## report_full.md

Detailed report including:

- old vs new benchmark version
- changed fields per control
- full field comparison (old vs new values)

Useful for **audit and review purposes**.

---

# Parser behaviour

The parser:

1. Detects where the **real benchmark body starts**
2. Skips the **table of contents**
3. Detects control headers
4. Splits control blocks by known CIS section headings

Supported headings:

- Description
- Rationale / Rationale Statement
- Impact / Impact Statement
- Audit / Audit Procedure
- Remediation / Remediation Procedure
- Default Value
- References

---

# CSV and Excel compatibility

CSV exports use **UTF-8 with BOM (`utf-8-sig`)** to improve compatibility with Excel on Windows.

Multiline fields such as audit or remediation are normalized so they remain inside a single CSV cell.

Recommended usage:

| Format | Use case |
|------|------|
JSONL | automation, diffing |
CSV | Excel analysis and reporting |

---

# Security

The container runtime is designed for safe processing of untrusted PDFs.

Security measures include:

- non-root container user
- read-only filesystem support
- no-new-privileges
- dropped Linux capabilities
- block-level hashing for integrity verification

See `SECURITY.md` for the STRIDE threat model.

---

# Limitations

- Currently optimized for **Windows Server CIS benchmarks**
- Layout changes in CIS PDFs may require parser adjustments
- Control renumbering between versions may appear as added/removed instead of renamed

---

# License

MIT (code only).

CIS benchmark content is **not included** and remains subject to CIS Terms of Use.
