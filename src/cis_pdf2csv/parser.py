from __future__ import annotations

import re
import hashlib
from typing import Iterator, Optional, Tuple, Dict, List

import fitz  # PyMuPDF


# --- Section headings (body) ---
SECTION_HEADINGS = [
    "Profile Applicability",
    "Description",
    "Rationale Statement",
    "Impact Statement",
    "Audit Procedure",
    "Remediation Procedure",
    "Default Value",
    "References",
]

# "Real content" indicator headings. TOC pages won't have these.
EVIDENCE_HEADINGS = {
    "Profile Applicability",
    "Audit Procedure",
    "Remediation Procedure",
    "Description",
}

# --- Header detection (TOC-style lines and body headers) ---
# Matches: 1.1.1 Ensure '...' ... (Automated)
# Allows optional trailing dot leaders + page number from TOC.
RE_HEADER = re.compile(
    r"^(?P<id>\d+(?:\.\d+)+)\s+"
    r"(?P<title>.+?)\s+"
    r"\((?P<assessment>Automated|Manual)\)"
    r"(?:\s+\.*\s*\d+)?\s*$"
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
        text = page.get_text("text")
        text = _normalize_text(text)
        for ln in text.splitlines():
            ln = ln.strip()
            if ln:
                yield (i + 1, ln)  # pages are 1-indexed


def extract_benchmark_meta(pdf_path: str) -> Tuple[str, str, str]:
    doc = fitz.open(pdf_path)
    first = _normalize_text(doc.load_page(0).get_text("text"))
    lines = [l.strip() for l in first.splitlines() if l.strip()]
    name = "CIS Microsoft Windows Server Benchmark"
    version = ""
    date = ""

    # Try parse from first page: product line + version/date line
    for idx, ln in enumerate(lines[:80]):
        m = RE_BENCHMARK_META.match(ln)
        if m:
            name = f"CIS Microsoft Windows Server {m.group('product').strip()} Benchmark"
            # Search nearby for version/date line
            for ln2 in lines[idx : idx + 15]:
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

    return name, version, date or ""


def _split_title_applicability(raw_title: str) -> Tuple[str, Optional[str]]:
    # Pull trailing "(MS only)" "(DC only)" etc that may appear before (Automated/Manual).
    applicability = []
    title = raw_title

    while True:
        m = re.search(r"\s+\(([^)]+only)\)\s*$", title, re.IGNORECASE)
        if not m:
            break
        applicability.insert(0, m.group(1))
        title = title[: m.start()].rstrip()

    return title, "; ".join(applicability) if applicability else None


def _join_multiline_header(line: str, next_line: Optional[str]) -> str:
    """
    Some PDFs wrap long titles: the '(Automated)' token may appear on the next line.
    If current line looks like it starts a control id but lacks (Automated|Manual),
    join with next line and try matching again.
    """
    if not next_line:
        return line
    # Starts with control id, but no assessment marker yet -> likely wrapped
    if re.match(r"^\d+(?:\.\d+)+\b", line) and ("(Automated)" not in line and "(Manual)" not in line):
        return f"{line} {next_line}".strip()
    return line


def _profile_from_applicability(applicability: Optional[str]) -> str:
    """
    Determine L1/L2/Unknown based on Profile Applicability section text.
    CIS typically includes 'Level 1' / 'Level 2' strings here.
    """
    if not applicability:
        return "Unknown"
    a = applicability.lower()
    # Prefer explicit Level 2 if present
    if "level 2" in a:
        return "L2"
    if "level 1" in a:
        return "L1"
    return "Unknown"


def parse_controls(pdf_path: str, profile_filter: Optional[str] = None) -> List[Dict]:
    # Hash PDF bytes for evidence/integrity
    with open(pdf_path, "rb") as f:
        pdf_hash = sha256_bytes(f.read())

    bench_name, bench_version, bench_date = extract_benchmark_meta(pdf_path)

    controls: List[Dict] = []
    current: Optional[Dict] = None
    current_lines: List[str] = []
    current_end_page: Optional[int] = None

    # We need a one-line lookahead to support multiline headers
    it = iter_pdf_lines(pdf_path)
    buffered: Optional[Tuple[int, str]] = None

    def next_item() -> Optional[Tuple[int, str]]:
        nonlocal buffered
        if buffered is not None:
            x = buffered
            buffered = None
            return x
        try:
            return next(it)
        except StopIteration:
            return None

    while True:
        item = next_item()
        if item is None:
            break
        page, line = item

        # Lookahead for multiline header join
        look = next_item()
        if look is not None:
            buffered = look
        candidate = _join_multiline_header(line, look[1] if look else None)

        m = RE_HEADER.match(candidate)
        if m:
            # If we consumed lookahead as part of candidate join, drop buffered
            if candidate != line:
                buffered = None  # we used the next line already

            # finalize previous
            if current:
                block_text = "\n".join(current_lines).strip()
                current["page_end"] = current_end_page or current["page_start"]
                current["block_text_sha256"] = sha256_text(block_text)

                sections = _extract_sections(block_text)

                # Skip TOC-like segments: no evidence headings found
                if _is_real_control(sections):
                    current.update(sections)

                    # Profile derived from applicability
                    current["profile"] = _profile_from_applicability(current.get("applicability"))

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
                profile="Unknown",  # will be derived from applicability
                title=title,
                assessment=assessment,
                applicability=applicability_tag,  # short tag e.g. MS only/DC only from header
                page_start=page,
                page_end=page,
                source_pdf_sha256=pdf_hash,
                extracted_at_utc=_utc_now(),
                parser_version="0.1.0",
                block_text_sha256="",
            )
            current_lines = []
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

        sections = _extract_sections(block_text)
        if _is_real_control(sections):
            current.update(sections)
            current["profile"] = _profile_from_applicability(current.get("applicability"))
            controls.append(current)

    # Apply profile filter (derived from Profile Applicability)
    if profile_filter:
        pf = profile_filter.upper()
        controls = [c for c in controls if (c.get("profile") or "").upper() == pf]

    return controls


def _utc_now() -> str:
    import datetime

    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _is_real_control(sections: Dict[str, Optional[str]]) -> bool:
    """
    TOC entries won't have these section bodies. Real controls do.
    Evidence-grade rule: require at least one of the evidence headings to have content.
    """
    # Note: _extract_sections maps "Profile Applicability" -> "applicability"
    if sections.get("audit") or sections.get("remediation"):
        return True
    if sections.get("description"):
        return True
    if sections.get("applicability"):
        return True
    return False


def _extract_sections(block_text: str) -> Dict[str, Optional[str]]:
    """
    Split into sections by known headings.
    Headings in CIS PDFs may appear with or without trailing colon.
    """
    lines = [ln.strip() for ln in block_text.splitlines() if ln.strip()]
    idxs: List[Tuple[int, str]] = []

    for i, ln in enumerate(lines):
        for h in SECTION_HEADINGS:
            if ln == h or ln.startswith(h + ":"):
                idxs.append((i, h))
                break

    if not idxs:
        return {
            "applicability": None,
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
        sections[h] = "\n".join(content_lines).strip()

    return {
        "applicability": sections.get("Profile Applicability") or None,
        "description": sections.get("Description") or None,
        "rationale": sections.get("Rationale Statement") or None,
        "impact": sections.get("Impact Statement") or None,
        "audit": sections.get("Audit Procedure") or None,
        "remediation": sections.get("Remediation Procedure") or None,
        "default_value": sections.get("Default Value") or None,
        "references": sections.get("References") or None,
    }
