
# cis-pdf2csv

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Docker](https://img.shields.io/badge/docker-supported-blue.svg)
![Podman](https://img.shields.io/badge/podman-supported-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Convert **CIS Benchmark PDFs** into structured datasets and detect **changes between benchmark versions**.

`cis-pdf2csv` parses CIS Benchmark documents (primarily **Windows Server benchmarks**) and exports every control into machine‑readable formats such as **CSV** and **JSONL**.  
It also includes a **diff engine** that compares benchmark versions and generates detailed reports.

Designed for **security engineers, auditors, and governance teams** who need reproducible benchmark analysis.

---

# ✨ Features

- Parse **CIS Windows Server Benchmark PDFs**
- Extract full control metadata:
  - description
  - rationale
  - impact
  - audit procedure
  - remediation procedure
  - default value
  - references
- Filter controls by profile (`L1`, `L2`, `NG`)
- Export formats:
  - **CSV** (Excel friendly)
  - **JSONL** (automation friendly)
- **Diff benchmark versions**
- Generate reports:
  - `changes.csv`
  - `report.md`
  - `report_full.md`
- Evidence-grade extraction with:
  - page references
  - SHA256 integrity hashes
- Hardened Docker runtime

---

# 🧠 Pipeline

```
CIS Benchmark PDF
        │
        ▼
     parser.py
        │
        ▼
   CSV / JSONL export
        │
        ▼
      diff.py
        │
        ▼
changes.csv / report.md / report_full.md
```

---

# 📦 Project structure

```
cis-pdf2csv
├─ src/
│  └─ cis_pdf2csv/
│     ├─ __main__.py
│     ├─ cli.py
│     ├─ parser.py
│     ├─ diff.py
│     └─ schema.py
├─ Dockerfile
├─ requirements.txt
├─ pyproject.toml
├─ README.md
└─ SECURITY.md
```

---

# ⚙️ Installation

## Local (Python) 

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m cis_pdf2csv --help
```

## Docker

```bash
docker build --no-cache -t cis-pdf2csv .
```

## Podman

```bash
podman build --no-cache -t cis-pdf2csv .
```

---

# 🚀 Usage

## Parse CIS benchmark

```bash
docker run --rm -v "$PWD:/work" -w /work cis-pdf2csv ./CIS_Microsoft_Windows_Server_2025_Benchmark_v2.0.0.pdf -p L1 -o out_l1.csv
```

```bash
podman run --rm -v "$PWD:/work:Z" -w /work cis-pdf2csv >>CIS_Microsoft_Windows_Server_2025_Benchmark_v2.0.0.pdf -p L1 -o out_l1.csv
```

## Export JSONL

```bash
docker run --rm -v "$PWD:/work" -w /work cis-pdf2csv ./benchmark.pdf -p L1 -o out.jsonl --format jsonl
```

```bash
podman run --rm -v "$PWD:/work:Z" -w /work cis-pdf2csv ./benchmark.pdf -p L1 -o out.jsonl --format jsonl
```

---

# 🔍 Diff benchmark versions

Export baseline 1:

```bash
docker run --rm -v "$PWD:/work" -w /work cis-pdf2csv ./benchmark_v1.pdf -p L1 -o v1.jsonl --format jsonl
```

```bash
podman run --rm -v "$PWD:/work:Z" -w /work cis-pdf2csv ./benchmark_v1.pdf -p L1 -o v1.jsonl --format jsonl
```

Export baseline 2:

```bash
docker run --rm -v "$PWD:/work" -w /work cis-pdf2csv ./benchmark_v2.pdf -p L1 -o v2.jsonl --format jsonl
```

```bash
podman run --rm -v "$PWD:/work:Z" -w /work cis-pdf2csv ./benchmark_v2.pdf -p L1 -o v2.jsonl --format jsonl
```

Run diff:

```bash
docker run --rm -v "$PWD:/work" -w /work --entrypoint python cis-pdf2csv -m cis_pdf2csv.diff v1.jsonl v2.jsonl -o changes.csv --report report.md --full-report report_full.md
```

```bash
podman run --rm -v "$PWD:/work:Z" -w /work --entrypoint python cis-pdf2csv -m cis_pdf2csv.diff v1.jsonl v2.jsonl -o changes.csv --report report.md --full-report report_full.md
```

> Note: `:Z` on Podman volume mounts is recommended on SELinux-enabled hosts.

Example output:

```
changes: 365
added: 81
removed: 76
changed: 208
```

---

# 📊 Reports

## changes.csv

Machine readable overview of all changes.

## report.md

Summary including:

- total changes
- added controls
- removed controls
- changed controls
- most frequently changed fields

## report_full.md

Full audit report including:

- old vs new benchmark version
- changed fields per control
- complete value comparison

---

# 📄 Output schema

| Field | Description |
|------|-------------|
benchmark_name | CIS benchmark name |
benchmark_version | Benchmark version |
benchmark_date | Publication date |
control_id | CIS control ID |
profile | L1 / L2 / NG |
title | Control title |
assessment | Automated / Manual |
description | Description |
rationale | Rationale |
impact | Impact |
audit | Audit procedure |
remediation | Remediation |
default_value | Default value |
references | References |
page_start | Control start page |
page_end | Control end page |
source_pdf_sha256 | Source PDF hash |
block_text_sha256 | Control block hash |
parser_version | Parser version |
extracted_at_utc | Extraction timestamp |

---

# 🧩 Parser behaviour

The parser:

1. Detects where the **actual benchmark body starts**
2. Skips the **table of contents**
3. Identifies control headers
4. Splits sections based on CIS headings

Supported headings:

- Description
- Rationale / Rationale Statement
- Impact / Impact Statement
- Audit / Audit Procedure
- Remediation / Remediation Procedure
- Default Value
- References

---

# 📈 CSV vs JSONL

| Format | Use case |
|------|------|
JSONL | automation / diffing |
CSV | Excel / reporting |

CSV is written using **UTF‑8 BOM** to improve compatibility with **Excel on Windows**.

---

# 🔐 Security

The container is designed for processing **potentially untrusted PDFs**.

Security measures:

- non‑root container user
- read‑only filesystem support
- `no-new-privileges`
- `cap-drop ALL`
- block hashing for integrity verification

See **SECURITY.md** for the STRIDE threat model.

---

# ⚠️ Limitations

- Optimized for **Windows Server CIS benchmarks**
- Layout changes in CIS PDFs may require parser adjustments
- Control renumbering between versions may appear as added/removed

---

# 📜 License

MIT (code only).

CIS benchmark content is **not included** and remains subject to CIS Terms of Use.
