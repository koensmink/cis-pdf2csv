\
from __future__ import annotations

import re
import hashlib
from dataclasses import dataclass
from typing import Iterable, Iterator, Optional, Tuple, Dict, List

import fitz  # PyMuPDF

SECTION_HEADINGS = [
    "Description",
    "Rationale Statement",
    "Impact Statement",
    "Audit Procedure",
    "Remediation Procedure",
    "Default Value",
    "References",
]

# Matches a CIS recommendation header line.
# Examples in PDFs:
# 1.1.1 (L1) Ensure 'Enforce password history' is set to '24 or more password(s)' (Automated)
# 2.2.3 (L1) Ensure 'Access this computer...' (MS only) (Automated)
RE_HEADER = re.compile(
    r"^(?P<id>\d+(?:\.\d+)+)\s*\((?P<profile>L1|L2|NG)\)\s+"
    r"(?P<title>.+?)"
    r"(?:\s+\((?P<assessment>Automated|Manual)\))?"
    r"(?:\s+\([^)]+\))*\s*$"
)

RE_BENCHMARK_META = re.compile(
    r"^CIS\s+Microsoft\s+Windows\s+Server\s+(?P<product>\d{4}(?:\s*R2)?)\s+Benchmark\s*$",
    re.IGNORECASE,
)
RE_VERSION_DATE = re.compile(
    r"^v(?P<version>[0-9.]+)\s*[–-]\s*(?P<date>\d{2}[-/]\d{2}[-/]\d{4}|\d{4}[-/]\d{2}[-/]\d{2})\s*$"
)

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8", errors="replace")).hexdigest()

def _normalize_text(text: str) -> str:
    # Remove soft hyphen and normalize whitespace/newlines.
    text = text.replace("\u00ad", "")
    # Fix common PDF hyphenation across line breaks: "authenti-\ncation" -> "authentication"
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse weird spaces
    text = re.sub(r"[ \t]+", " ", text)
    # Remove trailing spaces
    text = "\n".join([ln.rstrip() for ln in text.splitlines()])
    return text

def iter_pdf_lines(pdf_path: str) -> Iterator[Tuple[int, str]]:
    doc = fitz.open(pdf_path)
    for i in range(doc.page_count):
        page = doc.load_page(i)
        text = page.get_text("text")  # plain text
        text = _normalize_text(text)
        for ln in text.splitlines():
            if ln.strip():
                yield (i + 1, ln.strip())  # pages are 1-indexed

def extract_benchmark_meta(pdf_path: str) -> Tuple[str, str, str]:
    doc = fitz.open(pdf_path)
    first = _normalize_text(doc.load_page(0).get_text("text"))
    lines = [l.strip() for l in first.splitlines() if l.strip()]
    name = "CIS Microsoft Windows Server Benchmark"
    version = ""
    date = ""
    # Try parse from first page: product line + version/date line
    for idx, ln in enumerate(lines[:50]):
        m = RE_BENCHMARK_META.match(ln)
        if m:
            name = f"CIS Microsoft Windows Server {m.group('product').strip()} Benchmark"
            # Search nearby for version/date line
            for ln2 in lines[idx:idx+10]:
                m2 = RE_VERSION_DATE.match(ln2.replace("–", "-"))
                if m2:
                    version = f"v{m2.group('version')}"
                    date = m2.group("date")
                    break
            break
    # Fallback: look for any vX - date in first page
    if not version:
        for ln in lines:
            m2 = RE_VERSION_DATE.match(ln.replace("–", "-"))
            if m2:
                version = f"v{m2.group('version')}"
                date = m2.group("date")
                break
    if not date:
        date = ""
    return name, version, date

def _split_title_applicability(raw_title: str) -> Tuple[str, Optional[str]]:
    # Pull trailing "(MS only)" "(DC only)" "(MS Only)" etc that may appear before (Automated)
    # We already stripped (Automated/Manual) at end via header regex.
    # Keep them as applicability tag(s).
    applicability = []
    title = raw_title
    # Find parenthetical markers at end like "(MS only)" or "(DC only)"
    while True:
        m = re.search(r"\s+\(([^)]+only)\)\s*$", title, re.IGNORECASE)
        if not m:
            break
        applicability.insert(0, m.group(1))
        title = title[:m.start()].rstrip()
    return title, "; ".join(applicability) if applicability else None

def parse_controls(pdf_path: str, profile_filter: Optional[str] = None) -> List[Dict]:
    # Hash PDF bytes for evidence/integrity
    with open(pdf_path, "rb") as f:
        pdf_hash = sha256_bytes(f.read())

    bench_name, bench_version, bench_date = extract_benchmark_meta(pdf_path)

    controls: List[Dict] = []
    current: Optional[Dict] = None
    current_lines: List[str] = []
    current_start_page: Optional[int] = None
    current_end_page: Optional[int] = None

    for page, line in iter_pdf_lines(pdf_path):
        m = RE_HEADER.match(line)
        if m:
            # finalize previous
            if current:
                current_end_page = current_end_page or page
                block_text = "\n".join(current_lines).strip()
                current["page_end"] = current_end_page or current["page_start"]
                current["block_text_sha256"] = sha256_text(block_text)
                current.update(_extract_sections(block_text))
                controls.append(current)

            control_id = m.group("id")
            profile = m.group("profile")
            assessment = m.group("assessment")
            raw_title = m.group("title")

            title, applicability = _split_title_applicability(raw_title)

            current = dict(
                benchmark_name=bench_name,
                benchmark_version=bench_version,
                benchmark_date=bench_date,
                control_id=control_id,
                profile=profile,
                title=title,
                assessment=assessment,
                applicability=applicability,
                page_start=page,
                page_end=page,
                source_pdf_sha256=pdf_hash,
                extracted_at_utc=_utc_now(),
                parser_version="0.1.0",
                block_text_sha256="",
            )
            current_lines = []
            current_start_page = page
            current_end_page = page
        else:
            if current:
                current_lines.append(line)
                current_end_page = page

    # finalize last
    if current:
        block_text = "\n".join(current_lines).strip()
        current["page_end"] = current_end_page or current["page_start"]
        current["block_text_sha256"] = sha256_text(block_text)
        current.update(_extract_sections(block_text))
        controls.append(current)

    if profile_filter:
        controls = [c for c in controls if c.get("profile") == profile_filter]

    return controls

def _utc_now() -> str:
    import datetime
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def _extract_sections(block_text: str) -> Dict[str, Optional[str]]:
    # Split into sections by known headings. Some PDFs put headings without colon.
    # We'll detect headings at line starts.
    lines = [ln.strip() for ln in block_text.splitlines() if ln.strip()]
    # Find indexes where a heading starts
    idxs: List[Tuple[int, str]] = []
    for i, ln in enumerate(lines):
        for h in SECTION_HEADINGS:
            if ln == h or ln.startswith(h + ":"):
                idxs.append((i, h))
                break
    if not idxs:
        return {
            "description": block_text.strip() or None,
            "rationale": None,
            "impact": None,
            "audit": None,
            "remediation": None,
            "default_value": None,
            "references": None,
        }

    idxs.sort(key=lambda x: x[0])
    sections: Dict[str, str] = {}
    for n, (i, h) in enumerate(idxs):
        start = i + 1
        end = idxs[n + 1][0] if n + 1 < len(idxs) else len(lines)
        content_lines = lines[start:end]
        # Strip if first line is "Description:" style (handled above)
        sections[h] = "\n".join(content_lines).strip()

    return {
        "description": sections.get("Description") or None,
        "rationale": sections.get("Rationale Statement") or None,
        "impact": sections.get("Impact Statement") or None,
        "audit": sections.get("Audit Procedure") or None,
        "remediation": sections.get("Remediation Procedure") or None,
        "default_value": sections.get("Default Value") or None,
        "references": sections.get("References") or None,
    }
