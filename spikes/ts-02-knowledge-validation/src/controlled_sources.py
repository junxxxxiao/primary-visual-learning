"""Controlled PDF checks. Extracted textbook text never leaves memory."""

from hashlib import sha256
from pathlib import Path


def _file_hash(path):
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _chapter_pages(pdf, first_page, last_page):
    pages = {}
    for page_number in range(first_page, last_page + 1):
        text = (pdf.pages[page_number - 1].extract_text() or "").replace(" ", "")
        pages[page_number] = {
            "text": text,
            "text_sha256": sha256(text.encode("utf-8")).hexdigest(),
            "character_count": len(text),
        }
    return pages


def validate_controlled_sources(manifest, paths):
    try:
        import pdfplumber
    except ImportError as error:
        raise RuntimeError("Controlled PDF mode requires the bundled workspace Python with pdfplumber") from error

    source_results = {}
    private_pages = {}
    for source in manifest["sources"]:
        path = Path(paths[source["source_id"]])
        actual_hash = _file_hash(path)
        first_page, last_page = source["pdf_pages"]
        with pdfplumber.open(path) as pdf:
            page_count_ok = len(pdf.pages) >= last_page
            pages = _chapter_pages(pdf, first_page, last_page) if page_count_ok else {}
        private_pages[source["source_id"]] = pages
        source_results[source["source_id"]] = {
            "title": source["title"],
            "chapter": source["chapter"],
            "school_stage": source["school_stage"],
            "grade": source["grade"],
            "pdf_pages": source["pdf_pages"],
            "book_pages": source["book_pages"],
            "expected_document_hash": f"sha256:{source['sha256']}",
            "actual_document_hash": f"sha256:{actual_hash}",
            "document_hash_match": actual_hash == source["sha256"],
            "chapter_page_count": len(pages),
            "chapter_pages_nonempty": bool(pages) and all(item["character_count"] > 0 for item in pages.values()),
            "page_fingerprints": [
                {
                    "pdf_page": page_number,
                    "text_sha256": item["text_sha256"],
                    "character_count": item["character_count"],
                }
                for page_number, item in pages.items()
            ],
        }

    evidence_results = []
    for rule in manifest["evidence_rules"]:
        pages = private_pages[rule["source_id"]]
        first_page, last_page = rule["pdf_pages"][0], rule["pdf_pages"][-1]
        selected = "".join(pages[number]["text"] for number in range(first_page, last_page + 1) if number in pages)
        marker_presence = {marker: marker in selected for marker in rule["required_markers"]}
        found = any(marker_presence.values()) if rule["expected"] == "unsupported" else all(marker_presence.values())
        observed = "supported" if found else "unsupported"
        evidence_results.append(
            {
                "claim_id": rule["claim_id"],
                "source_id": rule["source_id"],
                "pdf_pages": rule["pdf_pages"],
                "expected": rule["expected"],
                "observed": observed,
                "oracle_match": observed == rule["expected"],
                "marker_presence": marker_presence,
            }
        )

    source_checks_pass = all(
        result["document_hash_match"] and result["chapter_pages_nonempty"]
        for result in source_results.values()
    )
    evidence_checks_pass = all(result["oracle_match"] for result in evidence_results)
    unsupported = [result["claim_id"] for result in evidence_results if result["observed"] == "unsupported"]
    return {
        "protocol_version": "1.0",
        "source_results": source_results,
        "evidence_results": evidence_results,
        "source_checks_pass": source_checks_pass,
        "evidence_checks_pass": evidence_checks_pass,
        "package_decisions": {
            "primary_sound_atom": "candidate",
            "middle_perfect_square_identity_atom": "candidate",
            "current_full_math_demo_package": "unverified_generated" if unsupported else "candidate",
        },
        "unverified_user_notice_required": bool(unsupported),
        "formal_learning_result_allowed": not unsupported,
        "unsupported_claims": unsupported,
        "review_method": "ai_only",
        "review_execution": "interactive_codex_single_model_plus_deterministic_evidence_gate",
        "independence_limit": "Verification steps are structurally separated but were not run by independent model providers.",
        "verdict": "conditional_pass_with_source_gap" if source_checks_pass and evidence_checks_pass else "fail",
    }
