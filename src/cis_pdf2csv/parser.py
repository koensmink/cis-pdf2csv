from __future__ import annotations

import re
import hashlib
from typing import Iterator, Optional, Tuple, Dict, List

import fitz


SECTION_HEADINGS = [
    "Profile Applicability",
    "Description",
    "Rationale",
    "Rationale Statement",
    "Impact",
    "Impact Statement",
    "Audit",
    "Audit Procedure",
    "Remediation",
    "Remediation Procedure",
    "Default Value",
    "References",
]


SECTION_CANONICAL_MAP = {
    "profile applicability": "applicability",
    "description": "description",
    "rationale": "rationale",
    "rationale statement": "rationale",
    "impact": "impact",
    "impact statement": "impact",
    "audit": "audit",
    "audit procedure": "audit",
    "remediation": "remediation",
    "remediation procedure": "remediation",
    "default value": "default_value",
    "references": "references",
}


RE_HEADER = re.compile(
    r"^(?P<id>\d+(?:\.\d+)+)\s+"
    r"(?:\((?P<profile>L1|L2|NG)\)\s+)?"
    r"(?P<title>.+?)"
    r"(?:\s+\((?P<assessment>Automated|Manual)\))?"
    r"(?:\s+\([^)]+\))*\s*$"
)


RE_BENCHMARK_META = re.compile(
    r"^CIS\s+Microsoft\s+Windows\s+Server\s+(?P<product>\d{4}(?:\s*R2)?)\s+Benchmark",
    re.IGNORECASE,
)


RE_VERSION_DATE = re.compile(
    r"^v(?P<version>[0-9.]+)\s*[–-]\s*(?P<date>.+)$"
)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8", errors="replace")).hexdigest()


def _normalize_text(text: str) -> str:
    text = text.replace("\u00ad", "")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = "\n".join([ln.rstrip() for ln in text.splitlines()])
    return text


def _normalize_heading(line: str) -> str:
    """
    Normalize heading text so variants like:
    - 'Rationale'
    - 'Rationale:'
    - 'Rationale Statement'
    all become comparable.
    """
    return line.strip().rstrip(":").strip().lower()


def find_body_start_page(pdf_path: str) -> int:
    """
    Detect where the actual control body begins.
    We skip the TOC by searching for known section headings.
    """
    doc = fitz.open(pdf_path)

    needles = [
        "Profile Applicability",
        "Description",
        "Rationale",
        "Rationale Statement",
        "Impact",
        "Impact Statement",
        "Audit",
        "Audit Procedure",
        "Remediation",
        "Remediation Procedure",
        "Default Value",
        "References",
    ]

    for i in range(doc.page_count):
        text = _normalize_text(doc.load_page(i).get_text("text"))

        if any(n in text for n in needles):
            return i + 1

    return 1


def iter_pdf_lines(pdf_path: str, start_page: int) -> Iterator[Tuple[int, str]]:
    doc = fitz.open(pdf_path)

    for i in range(start_page - 1, doc.page_count):
        page = doc.load_page(i)
        text = _normalize_text(page.get_text("text"))

        for ln in text.splitlines():
            ln = ln.strip()
            if ln:
                yield (i + 1, ln)


def extract_benchmark_meta(pdf_path: str) -> Tuple[str, str, str]:
    doc = fitz.open(pdf_path)

    text = _normalize_text(doc.load_page(0).get_text("text"))
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    name = "CIS Microsoft Windows Server Benchmark"
    version = ""
    date = ""

    for idx, ln in enumerate(lines[:50]):
        m = RE_BENCHMARK_META.match(ln)
        if m:
            name = f"CIS Microsoft Windows Server {m.group('product')} Benchmark"

        m2 = RE_VERSION_DATE.match(ln.replace("–", "-"))
        if m2:
            version = f"v{m2.group('version')}"
            date = m2.group("date")

    return name, version, date


def _split_title_applicability(raw_title: str):
    applicability = []
    title = raw_title

    while True:
        m = re.search(r"\(([^)]+only)\)", title, re.IGNORECASE)

        if not m:
            break

        applicability.append(m.group(1))
        title = title.replace(m.group(0), "").strip()

    return title.strip(), "; ".join(applicability) if applicability else None


def _profile_from_applicability(text: Optional[str]):
    if not text:
        return "Unknown"

    t = text.lower()

    if "level 2" in t:
        return "L2"

    if "level 1" in t:
        return "L1"

    return "Unknown"


def _is_real_control(sections: Dict[str, Optional[str]]) -> bool:
    """
    Reject TOC blocks.
    Only accept if real CIS body sections exist.
    """
    if sections.get("audit") or sections.get("remediation"):
        return True

    if sections.get("applicability"):
        return True

    return False


def parse_controls(pdf_path: str, profile_filter: Optional[str] = None) -> List[Dict]:
    with open(pdf_path, "rb") as f:
        pdf_hash = sha256_bytes(f.read())

    bench_name, bench_version, bench_date = extract_benchmark_meta(pdf_path)

    start_page = find_body_start_page(pdf_path)

    controls: List[Dict] = []

    current: Optional[Dict] = None
    current_lines: List[str] = []
    current_end_page: Optional[int] = None

    for page, line in iter_pdf_lines(pdf_path, start_page):
        m = RE_HEADER.match(line)

        if m:
            if current:
                block_text = "\n".join(current_lines).strip()

                current["page_end"] = current_end_page or current["page_start"]
                current["block_text_sha256"] = sha256_text(block_text)

                sections = _extract_sections(block_text)

                if _is_real_control(sections):
                    current.update(sections)

                    current["profile"] = _profile_from_applicability(
                        current.get("applicability")
                    )

                    controls.append(current)

            control_id = m.group("id")
            assessment = m.group("assessment") or "Unknown"
            raw_title = m.group("title")

            title, applicability_tag = _split_title_applicability(raw_title)

            current = dict(
                benchmark_name=bench_name,
                benchmark_version=bench_version,
                benchmark_date=bench_date,
                control_id=control_id,
                profile="Unknown",
                title=title,
                assessment=assessment,
                applicability=applicability_tag,
                page_start=page,
                page_end=page,
                source_pdf_sha256=pdf_hash,
                extracted_at_utc=_utc_now(),
                parser_version="0.3.0",
                block_text_sha256="",
            )

            current_lines = []
            current_end_page = page

        else:
            if current:
                current_lines.append(line)
                current_end_page = page

    if current:
        block_text = "\n".join(current_lines).strip()

        current["page_end"] = current_end_page or current["page_start"]
        current["block_text_sha256"] = sha256_text(block_text)

        sections = _extract_sections(block_text)

        if _is_real_control(sections):
            current.update(sections)

            current["profile"] = _profile_from_applicability(
                current.get("applicability")
            )

            controls.append(current)

    if profile_filter:
        pf = profile_filter.upper()

        controls = [
            c for c in controls if (c.get("profile") or "").upper() == pf
        ]

    return controls


def _utc_now():
    import datetime

    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _extract_sections(block_text: str) -> Dict[str, Optional[str]]:
    """
    Extract CIS control sections from a control text block.

    Supports both older section names:
    - Rationale Statement
    - Impact Statement
    - Audit Procedure
    - Remediation Procedure

    and newer section names:
    - Rationale
    - Impact
    - Audit
    - Remediation
    """
    lines = [ln.strip() for ln in block_text.splitlines() if ln.strip()]

    sections_accumulator: Dict[str, List[str]] = {
        "applicability": [],
        "description": [],
        "rationale": [],
        "impact": [],
        "audit": [],
        "remediation": [],
        "default_value": [],
        "references": [],
    }

    current_key = "description"

    for ln in lines:
        normalized = _normalize_heading(ln)

        if normalized in SECTION_CANONICAL_MAP:
            current_key = SECTION_CANONICAL_MAP[normalized]
            continue

        sections_accumulator[current_key].append(ln)

    return {
        "applicability": "\n".join(sections_accumulator["applicability"]).strip() or None,
        "description": "\n".join(sections_accumulator["description"]).strip() or None,
        "rationale": "\n".join(sections_accumulator["rationale"]).strip() or None,
        "impact": "\n".join(sections_accumulator["impact"]).strip() or None,
        "audit": "\n".join(sections_accumulator["audit"]).strip() or None,
        "remediation": "\n".join(sections_accumulator["remediation"]).strip() or None,
        "default_value": "\n".join(sections_accumulator["default_value"]).strip() or None,
        "references": "\n".join(sections_accumulator["references"]).strip() or None,
    }
