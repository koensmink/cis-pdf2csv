# cis-pdf2csv (CIS Benchmark PDF -> controls CSV)

**Doel**: CIS Benchmark PDF's (Windows Server) automatisch omzetten naar **evidence-grade** CSV met per control o.a. *Audit* en *Remediation*.

> ⚠️ CIS Terms of Use: host CIS Benchmarks (PDF) niet in publieke repos/third-party sites. Dit project bevat **geen** CIS content; het verwacht dat je de PDF's lokaal of in een private runner aanlevert.

## Output (CSV)
Kolommen (subset):
- benchmark_name, benchmark_version, benchmark_date
- control_id, profile (L1/L2/NG), title, assessment (Automated/Manual), applicability (MS only/DC only/…)
- description, rationale, impact, audit, remediation, default_value, references
- page_start, page_end
- source_pdf_sha256, extracted_at_utc, parser_version, block_text_sha256

## Install
### Local (Python)
```bash
python -m venv .venv
source .venv/bin/activate  # of .venv\Scripts\activate op Windows
pip install -r requirements.txt
python -m cis_pdf2csv --help
```

### Docker
Docker build (init): 

```bash
docker build -t cis-pdf2csv .
docker run --rm -v "$PWD:/work" -w /work cis-pdf2csv \
  python -m cis_pdf2csv ./CIS_Microsoft_Windows_Server_2025_Benchmark_v1.0.0.pdf -p L1 -o out.csv
```
  
Docker (re)build: 

```bash
docker build --no-cache -t cis-pdf2csv .
docker run --rm -v "$PWD:/work" -w /work cis-pdf2csv \
  ./CIS_Microsoft_Windows_Server_2025_Benchmark_v2.0.0.pdf -p L1 -o out_l1.cs
```

Docker run (hardened):
```docker-run
docker run --rm \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=256m \
  --tmpfs /home/appuser:rw,noexec,nosuid,size=256m \
  --security-opt no-new-privileges \
  --cap-drop ALL \
  -v "$PWD:/work:ro" \
  -v "$PWD/out:/out:rw" \
  -w /work \
  cis-pdf2csv \
  ./CIS_Microsoft_Windows_Server_2025_Benchmark_v2.0.0.pdf -p L1 -o /out/out_l1.csv
```

## Python usage
```bash
python -m cis_pdf2csv <pdf1> [pdf2 ...] -p L1 -o out.csv
python -m cis_pdf2csv <pdf> -p L1 -o out.jsonl --format jsonl
```

## Diff
Export 1:
```bash
docker run --rm -v "$PWD:/work" -w /work cis-pdf2csv \
./CIS_Microsoft_Windows_Server_2025_Benchmark_v1.0.0.pdf -p L1 -o ws2025_v1_l1.jsonl --format jsonl
```
Export 2: 
```bash
docker run --rm -v "$PWD:/work" -w /work cis-pdf2csv \
./CIS_Microsoft_Windows_Server_2025_Benchmark_v2.0.0.pdf -p L1 -o ws2025_v2_l1.jsonl --format jsonl
``
Diff check:
```bash
docker run --rm -v "$PWD:/work" -w /work --entrypoint python cis-pdf2csv \
-m cis_pdf2csv.diff ws2025_v1_l1.jsonl ws2025_v2_l1.jsonl -o changes.csv
```

## GitHub Actions
Zie `.github/workflows/parse-cis.yml`. Gebruik bij voorkeur een **self-hosted runner** met toegang tot de PDF's (bijv. via interne storage).

## Evidence-grade aanpak (samengevat)
- Extractie per pagina incl. `page_start/page_end`
- Hashes van PDF en per-control block (`sha256`) voor integriteitscontrole
- Strikte herkenning van control headers (bijv. `1.1.1 (L1) Ensure ... (Automated)`)
- Sectie-splitting op vaste headings: Description, Rationale Statement, Impact Statement, Audit Procedure, Remediation Procedure, Default Value, References

## Licentie
MIT (code). Geen CIS content inbegrepen.
