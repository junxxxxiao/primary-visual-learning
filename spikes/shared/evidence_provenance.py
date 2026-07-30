from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


def canonical_sha256(value: dict[str, Any]) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def seal_knowledge_package(value: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(value)
    sealed["package_sha256"] = canonical_sha256(value)
    return sealed


def validate_knowledge_provenance(
    knowledge: dict[str, Any],
    producer_root: Path,
) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    export_path = producer_root / "results" / "knowledge-packages.json"
    if not export_path.is_file():
        return [{"code": "KNOWLEDGE_EXPORT_MISSING", "path": str(export_path)}]

    export = json.loads(export_path.read_text(encoding="utf-8"))
    manifest_path = producer_root / "fixtures" / "source-manifest.json"
    if not manifest_path.is_file():
        return [{"code": "SOURCE_MANIFEST_MISSING", "path": str(manifest_path)}]
    manifest_bytes = manifest_path.read_bytes()
    manifest_hash = f"sha256:{hashlib.sha256(manifest_bytes).hexdigest()}"
    if export.get("source_manifest_sha256") != manifest_hash:
        violations.append({"code": "SOURCE_MANIFEST_HASH_MISMATCH", "path": str(manifest_path)})

    case_id = knowledge.get("package_case_id")
    if not case_id:
        return [{"code": "KNOWLEDGE_PROVENANCE_MISSING", "path": "knowledge.package_case_id"}]
    expected = export.get("packages", {}).get(case_id)
    if expected is None:
        return [{"code": "KNOWLEDGE_PACKAGE_NOT_EXPORTED", "path": "knowledge.package_case_id"}]
    if expected.get("source_scope") == "synthetic_fixture":
        if expected.get("evidence_status") != "exploratory_only":
            violations.append({"code": "SYNTHETIC_SCOPE_NOT_EXPLORATORY", "path": "knowledge.evidence_status"})
    else:
        semantic_review = expected.get("semantic_review", {})
        if semantic_review.get("decision") != "pass" or semantic_review.get("independent") is not True:
            violations.append({"code": "INDEPENDENT_SEMANTIC_REVIEW_MISSING", "path": "knowledge.semantic_review"})

    manifest = json.loads(manifest_bytes.decode("utf-8"))
    source_manifest = {item["source_id"]: item for item in manifest["sources"]}
    source_pages: dict[str, dict[int, str]] = {}
    declared_source_ids: set[str] = set()
    for source_ref in expected.get("source_refs", []):
        source_id = source_ref["source_id"]
        declared_source_ids.add(source_id)
        record = source_manifest.get(source_id)
        if record is None:
            violations.append({"code": "SOURCE_NOT_IN_MANIFEST", "path": f"knowledge.source_refs.{source_id}"})
            continue
        source_path = (producer_root / record["path"]).resolve()
        if producer_root.resolve() not in source_path.parents or not source_path.is_file():
            violations.append({"code": "SOURCE_FILE_MISSING", "path": str(source_path)})
            continue
        raw = source_path.read_bytes()
        actual_hash = f"sha256:{hashlib.sha256(raw).hexdigest()}"
        manifest_document_hash = f"sha256:{record['sha256']}"
        if actual_hash != manifest_document_hash or actual_hash != source_ref.get("document_hash"):
            violations.append({"code": "SOURCE_DOCUMENT_HASH_MISMATCH", "path": str(source_path)})
        sections = re.split(r"\n\[page (\d+)\]\n", raw.decode("utf-8"))
        source_pages[source_id] = {
            int(sections[position]): sections[position + 1].strip()
            for position in range(1, len(sections), 2)
        }

    for claim_index, claim in enumerate(expected.get("claims", [])):
        for evidence_index, evidence_ref in enumerate(claim.get("evidence_refs", [])):
            source_id = evidence_ref.get("source_id")
            page = evidence_ref.get("page")
            path = f"knowledge.claims[{claim_index}].evidence_refs[{evidence_index}]"
            if source_id not in declared_source_ids:
                violations.append({"code": "EVIDENCE_SOURCE_NOT_DECLARED", "path": path})
                continue
            page_text = source_pages.get(source_id, {}).get(page)
            if page_text is None:
                violations.append({"code": "EVIDENCE_PAGE_MISSING", "path": path})
            elif evidence_ref.get("quote", "") not in page_text:
                violations.append({"code": "EVIDENCE_QUOTE_NOT_FOUND", "path": path})

    supplied_hash = knowledge.get("package_sha256")
    unsealed = {key: value for key, value in knowledge.items() if key != "package_sha256"}
    if supplied_hash != canonical_sha256(unsealed):
        violations.append({"code": "KNOWLEDGE_PACKAGE_HASH_MISMATCH", "path": "knowledge.package_sha256"})
    if knowledge != expected:
        violations.append({"code": "KNOWLEDGE_PACKAGE_CONTENT_MISMATCH", "path": "knowledge"})
    return violations
