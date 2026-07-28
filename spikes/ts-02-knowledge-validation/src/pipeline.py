"""Pure validation pipeline for the throwaway TS-02 knowledge spike."""

from hashlib import sha256
from pathlib import Path
import re


STAGE_FIELDS = (
    "school_stage",
    "grade",
    "curriculum",
    "textbook_edition",
    "prerequisite_refs",
    "profile_version",
)

UNVERIFIED_NOTICE = (
    "这次讲解暂未匹配到已核验的教材或权威资料，"
    "内容由 AI 根据通用知识生成，可能存在错误，仅供探索参考。"
)

UNVERIFIED_REASON_CODES = {
    "CRITICAL_CLAIM_WITHOUT_EVIDENCE",
    "EVIDENCE_PAGE_MISSING",
    "EVIDENCE_QUOTE_NOT_FOUND",
    "EVIDENCE_SOURCE_NOT_DECLARED",
    "NO_RELIABLE_SOURCE",
    "PAGE_MISSING",
    "SOURCE_HASH_MISMATCH",
    "SOURCE_NOT_FOUND",
    "TEMPORARY_PACKAGE_SOURCE_THRESHOLD_NOT_MET",
}


def _step(name, reasons=(), evidence=()):
    reason_codes = sorted(set(reasons))
    return {
        "schema_version": "1.0",
        "step": name,
        "status": "fail" if reason_codes else "pass",
        "reason_codes": reason_codes,
        "evidence_refs": sorted(set(evidence)),
    }


def build_source_index(root, manifest):
    index = {}
    for record in manifest["sources"]:
        path = root / record["path"]
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        sections = re.split(r"\n\[page (\d+)\]\n", text)
        pages = {}
        for position in range(1, len(sections), 2):
            pages[int(sections[position])] = sections[position + 1].strip()
        index[record["source_id"]] = {
            **record,
            "actual_sha256": sha256(raw).hexdigest(),
            "actual_pages": pages,
        }
    return index


def parse_check(case, source_index):
    reasons = []
    evidence = []
    if case.get("untrusted_instructions"):
        reasons.append("PROMPT_INJECTION_DETECTED")
    for source_ref in case["source_refs"]:
        source_id = source_ref.get("source_id")
        source = source_index.get(source_id)
        if not source:
            reasons.append("SOURCE_NOT_FOUND")
            continue
        for page in source_ref.get("pages", []):
            if page not in source["actual_pages"]:
                reasons.append("PAGE_MISSING")
            else:
                evidence.append(f"{source_id}:page:{page}")
        if source_ref.get("ocr_confidence", 1.0) < 0.9:
            reasons.append("OCR_LOW_CONFIDENCE")
        if "ocr_text" in source_ref:
            reasons.append("OCR_OVERRIDE_UNTRUSTED")
    return _step("parse", reasons, evidence)


def source_verification(case, source_index):
    reasons = []
    evidence = []
    referenced_sources = {item.get("source_id") for item in case["source_refs"]}
    if not referenced_sources:
        reasons.append("NO_RELIABLE_SOURCE")
    for source_id in referenced_sources:
        source = source_index.get(source_id)
        if not source:
            reasons.append("SOURCE_NOT_FOUND")
        elif source["sha256"] != source["actual_sha256"]:
            reasons.append("SOURCE_HASH_MISMATCH")

    for claim in case["claims"]:
        refs = claim.get("evidence_refs", [])
        if claim.get("critical") and not refs:
            reasons.append("CRITICAL_CLAIM_WITHOUT_EVIDENCE")
        for ref in refs:
            source_id = ref.get("source_id")
            page = ref.get("page")
            source = source_index.get(source_id)
            if source_id not in referenced_sources:
                reasons.append("EVIDENCE_SOURCE_NOT_DECLARED")
            if not source or page not in source["actual_pages"]:
                reasons.append("EVIDENCE_PAGE_MISSING")
                continue
            if ref.get("quote", "") not in source["actual_pages"][page]:
                reasons.append("EVIDENCE_QUOTE_NOT_FOUND")
            else:
                evidence.append(f"{source_id}:page:{page}:claim:{claim['claim_id']}")

    if case["package_kind"] == "temporary_package":
        sources = [source_index[source_id] for source_id in referenced_sources if source_id in source_index]
        has_tier_one = any(item["source_tier"] == 1 for item in sources)
        independent_groups = {item["independence_group"] for item in sources if item["source_tier"] <= 3}
        if not has_tier_one and len(independent_groups) < 2:
            reasons.append("TEMPORARY_PACKAGE_SOURCE_THRESHOLD_NOT_MET")
    return _step("source_verification", reasons, evidence)


def boundary_check(case, source_index):
    reasons = []
    evidence = []
    profile = case["stage_profile"]
    stage = profile.get("school_stage")
    edition = profile.get("textbook_edition")
    stage_fit_request = case.get("stage_fit_request", {})
    declared_advanced = stage_fit_request.get("status") == "advanced"
    declared_sources = set(stage_fit_request.get("source_refs", []))
    for source_ref in case["source_refs"]:
        source = source_index.get(source_ref.get("source_id"))
        if not source:
            continue
        if stage and source["school_stage"] != stage:
            if not declared_advanced or source["source_id"] not in declared_sources:
                reasons.append("CROSS_STAGE_SOURCE_MIXING")
        if case["package_kind"] == "textbook_atom" and edition and source["edition"] != edition and not declared_advanced:
            reasons.append("TEXTBOOK_EDITION_MISMATCH")
        evidence.append(f"{source['source_id']}:stage:{source['school_stage']}")

    assertions = case.get("review_assertions", {})
    if assertions and len(set(assertions.values())) > 1:
        reasons.append("INDEPENDENT_CHECK_CONFLICT")
    if not case["boundaries"]:
        reasons.append("BOUNDARIES_MISSING")
    return _step("boundary_check", reasons, evidence)


def pedagogy_check(case, _source_index):
    reasons = []
    if not case["learning_objective"].strip():
        reasons.append("LEARNING_OBJECTIVE_MISSING")
    if not case["age_appropriate_expression"].strip():
        reasons.append("AGE_APPROPRIATE_EXPRESSION_MISSING")
    declared = set(case["stage_profile"].get("prerequisite_refs", []))
    bridged = set(case.get("stage_fit_request", {}).get("bridge_prerequisite_refs", []))
    undeclared = set(case["prerequisites_used"]) - declared - bridged
    if undeclared:
        reasons.append("UNDECLARED_PREREQUISITE")
    return _step("pedagogy_check", reasons, sorted(declared))


def transfer_check(case, _source_index):
    reasons = []
    task = case["transfer_task"]
    if not task.get("different_context"):
        reasons.append("TRANSFER_REPEATS_ORIGINAL_CONTEXT")
    if not task.get("asks_conclusion"):
        reasons.append("TRANSFER_CONCLUSION_MISSING")
    if not task.get("asks_reason"):
        reasons.append("TRANSFER_REASON_MISSING")
    return _step("transfer_check", reasons, [task.get("prompt", "")])


CHECKS = (
    parse_check,
    source_verification,
    boundary_check,
    pedagogy_check,
    transfer_check,
)


def _stage_context_status(profile):
    present = sum(profile.get(field) not in (None, "", []) for field in STAGE_FIELDS)
    if present == len(STAGE_FIELDS):
        return "provided"
    if present:
        return "partial"
    return "unknown"


def _stage_fit(case, source_index):
    requested = case.get("stage_fit_request")
    if requested:
        return {
            "status": requested["status"],
            "basis": requested.get("basis", "textbook_source"),
            "source_refs": requested.get("source_refs", []),
            "missing_prerequisite_refs": requested.get("bridge_prerequisite_refs", []),
            "fit_version": "1.0",
        }
    profile = case["stage_profile"]
    if _stage_context_status(profile) != "provided":
        return {
            "status": "unknown",
            "basis": "none",
            "source_refs": [],
            "missing_prerequisite_refs": [],
            "fit_version": "1.0",
        }
    source_refs = [item["source_id"] for item in case["source_refs"] if item.get("source_id") in source_index]
    return {
        "status": "within_stage",
        "basis": "textbook_source",
        "source_refs": source_refs,
        "missing_prerequisite_refs": [],
        "fit_version": "1.0",
    }


def release_decision(case, steps, source_index):
    failed_reasons = sorted(
        {reason for step in steps if step["status"] == "fail" for reason in step["reason_codes"]}
    )
    unverified_only = bool(failed_reasons) and set(failed_reasons).issubset(UNVERIFIED_REASON_CODES)
    blocked = bool(failed_reasons) and not unverified_only
    verified = not failed_reasons
    source_refs = []
    for item in case["source_refs"]:
        source = source_index.get(item.get("source_id"))
        if source:
            source_refs.append(
                {
                    "source_id": source["source_id"],
                    "document_hash": f"sha256:{source['actual_sha256']}",
                    "edition": source["edition"],
                    "pages": item.get("pages", []),
                }
            )
    return {
        "schema_version": "1.1",
        "case_id": case["case_id"],
        "package_kind": case["package_kind"],
        "stage_profile": case["stage_profile"],
        "stage_context_status": _stage_context_status(case["stage_profile"]),
        "stage_fit": _stage_fit(case, source_index),
        "source_refs": source_refs,
        "claims": case["claims"],
        "review_method": "ai_only",
        "review_steps": steps,
        "status": (
            "temporary"
            if verified and case["package_kind"] == "temporary_package"
            else "candidate"
            if verified
            else "unverified_generated"
            if unverified_only
            else "blocked"
        ),
        "verification_status": (
            "temporary_verified"
            if verified and case["package_kind"] == "temporary_package"
            else "verified_atom"
            if verified
            else "unverified_generated"
            if unverified_only
            else "blocked"
        ),
        "user_notice": UNVERIFIED_NOTICE if unverified_only else "",
        "formal_learning_result_allowed": verified,
        "content_version": "2026-07-28.1",
        "evidence_status": "exploratory_only" if verified else "unverified_reference_only" if unverified_only else "rejected",
        "routing_reasons": failed_reasons,
    }


def validate_case(case, source_index):
    steps = [check(case, source_index) for check in CHECKS]
    package = release_decision(case, steps, source_index)
    actual_decision = (
        "publish"
        if package["status"] in ("candidate", "temporary")
        else "unverified_generate"
        if package["status"] == "unverified_generated"
        else "block"
    )
    return {
        "case_id": case["case_id"],
        "expected_decision": case["expected_decision"],
        "actual_decision": actual_decision,
        "oracle_match": actual_decision == case["expected_decision"],
        "steps": steps,
        "package": package,
    }
