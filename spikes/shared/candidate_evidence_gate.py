from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


STAGES = {"preflight": 1, "candidate": 2, "release": 3}


def canonical_sha256(value: dict[str, Any]) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def file_sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def violation(code: str, path: str) -> dict[str, str]:
    return {"code": code, "path": path}


def repository_file(repo_root: Path, relative_path: str) -> Path | None:
    root = repo_root.resolve()
    resolved = (root / relative_path).resolve()
    if resolved != root and root not in resolved.parents:
        return None
    return resolved


def manifest_is_valid(manifest: dict[str, Any]) -> bool:
    candidate = manifest.get("candidate")
    budget = manifest.get("budget")
    data_boundary = manifest.get("data_boundary")
    inputs = manifest.get("inputs")
    input_ids = [item.get("id") for item in inputs] if isinstance(inputs, list) else []
    result_hash_keys = [item.get("result_hash_key") for item in inputs] if isinstance(inputs, list) else []
    budget_values = [budget.get(key) for key in ("external_requests", "tokens", "cost_cny")] if isinstance(budget, dict) else []
    historical_results = manifest.get("historical_results", [])
    return (
        manifest.get("schema_version") == "candidate-manifest/1.0"
        and all(manifest.get(key) for key in ("slice_id", "result_path"))
        and isinstance(candidate, dict)
        and all(candidate.get(key) is not None for key in ("subject", "supplier", "version", "invocation", "fixed_parameters"))
        and isinstance(budget, dict)
        and all(isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0 for value in budget_values)
        and isinstance(data_boundary, dict)
        and bool(data_boundary.get("classification"))
        and data_boundary.get("contains_child_data") is False
        and isinstance(inputs, list)
        and bool(inputs)
        and len(input_ids) == len(set(input_ids))
        and len(result_hash_keys) == len(set(result_hash_keys))
        and all(
            isinstance(item, dict)
            and all(item.get(key) for key in ("id", "path", "sha256", "result_hash_key"))
            and re.fullmatch(r"sha256:[0-9a-f]{64}", item["sha256"]) is not None
            for item in inputs
        )
        and isinstance(historical_results, list)
        and all(
            isinstance(item, dict)
            and bool(item.get("path"))
            and re.fullmatch(r"sha256:[0-9a-f]{64}", item.get("sha256", "")) is not None
            and bool(item.get("classification"))
            for item in historical_results
        )
    )


def authorization_is_valid(authorization: dict[str, Any]) -> bool:
    decision = authorization.get("decision")
    common_valid = (
        authorization.get("schema_version") == "candidate-authorization/1.0"
        and bool(authorization.get("slice_id"))
        and re.fullmatch(r"sha256:[0-9a-f]{64}", authorization.get("manifest_sha256", "")) is not None
        and decision in {"pending", "approved", "rejected"}
        and isinstance(authorization.get("evidence"), str)
    )
    if decision != "approved":
        return common_valid
    return common_valid and bool(authorization.get("authorized_by")) and bool(authorization.get("authorized_at"))


def run_record_is_valid(run: dict[str, Any]) -> bool:
    return (
        run.get("schema_version") == "candidate-run/1.0"
        and run.get("state") == "candidate_run_complete"
        and all(run.get(key) for key in ("slice_id", "started_at", "completed_at", "result_path"))
        and re.fullmatch(r"sha256:[0-9a-f]{64}", run.get("manifest_sha256", "")) is not None
        and re.fullmatch(r"sha256:[0-9a-f]{64}", run.get("result_sha256", "")) is not None
    )


def review_record_is_valid(review: dict[str, Any]) -> bool:
    return (
        review.get("schema_version") == "candidate-human-review/1.0"
        and review.get("decision") in {"conditional_pass", "pass", "fail"}
        and all(review.get(key) for key in ("slice_id", "reviewed_at", "reviewer", "evidence"))
        and re.fullmatch(r"sha256:[0-9a-f]{64}", review.get("manifest_sha256", "")) is not None
        and re.fullmatch(r"sha256:[0-9a-f]{64}", review.get("result_sha256", "")) is not None
    )


def validate_candidate_evidence(
    *,
    repo_root: Path,
    manifest_path: Path,
    authorization_path: Path,
    run_path: Path | None = None,
    review_path: Path | None = None,
    required_stage: str = "release",
) -> list[dict[str, str]]:
    if required_stage not in STAGES:
        raise ValueError(f"Unsupported candidate evidence stage: {required_stage}")
    violations: list[dict[str, str]] = []
    for path, code in (
        (manifest_path, "CANDIDATE_MANIFEST_MISSING"),
        (authorization_path, "CANDIDATE_AUTHORIZATION_MISSING"),
    ):
        if not path.is_file():
            violations.append(violation(code, str(path)))
    if violations:
        return violations

    manifest = load_json(manifest_path)
    authorization = load_json(authorization_path)
    if not manifest_is_valid(manifest):
        violations.append(violation("CANDIDATE_MANIFEST_INVALID", str(manifest_path)))
    if not authorization_is_valid(authorization):
        violations.append(violation("CANDIDATE_AUTHORIZATION_INVALID", str(authorization_path)))
    manifest_hash = canonical_sha256(manifest)
    if authorization.get("decision") != "approved":
        violations.append(violation("AUTHORIZATION_NOT_APPROVED", str(authorization_path)))
    if authorization.get("manifest_sha256") != manifest_hash:
        violations.append(violation("AUTHORIZATION_MANIFEST_HASH_MISMATCH", str(authorization_path)))
    if authorization.get("slice_id") != manifest.get("slice_id"):
        violations.append(violation("AUTHORIZATION_SLICE_MISMATCH", str(authorization_path)))

    for index, item in enumerate(manifest.get("inputs", [])):
        relative_path = item.get("path", "")
        input_path = repository_file(repo_root, relative_path)
        item_path = f"inputs[{index}]"
        if input_path is None:
            violations.append(violation("CANDIDATE_INPUT_OUTSIDE_REPOSITORY", item_path))
        elif not input_path.is_file():
            violations.append(violation("CANDIDATE_INPUT_MISSING", relative_path))
        elif item.get("sha256") != file_sha256(input_path):
            violations.append(violation("CANDIDATE_INPUT_HASH_MISMATCH", relative_path))
    for index, item in enumerate(manifest.get("historical_results", [])):
        historical_path = repository_file(repo_root, item.get("path", ""))
        if historical_path is None or not historical_path.is_file():
            violations.append(violation("HISTORICAL_CANDIDATE_RESULT_MISSING", f"historical_results[{index}]"))
        elif item.get("sha256") != file_sha256(historical_path):
            violations.append(violation("HISTORICAL_CANDIDATE_RESULT_HASH_MISMATCH", item["path"]))

    if STAGES[required_stage] < STAGES["candidate"]:
        return violations
    if run_path is None or not run_path.is_file():
        violations.append(violation("CANDIDATE_RUN_RECORD_MISSING", str(run_path)))
        return violations

    run = load_json(run_path)
    if not run_record_is_valid(run):
        violations.append(violation("CANDIDATE_RUN_RECORD_INVALID", str(run_path)))
    if run.get("manifest_sha256") != manifest_hash:
        violations.append(violation("CANDIDATE_RUN_MANIFEST_HASH_MISMATCH", str(run_path)))
    if run.get("state") != "candidate_run_complete":
        violations.append(violation("CANDIDATE_RUN_STATE_INVALID", str(run_path)))
    if run.get("slice_id") != manifest.get("slice_id"):
        violations.append(violation("CANDIDATE_RUN_SLICE_MISMATCH", str(run_path)))
    try:
        if parse_timestamp(run["started_at"]) < parse_timestamp(authorization["authorized_at"]):
            violations.append(violation("CANDIDATE_RUN_PRECEDES_AUTHORIZATION", str(run_path)))
        if parse_timestamp(run["completed_at"]) < parse_timestamp(run["started_at"]):
            violations.append(violation("CANDIDATE_RUN_TIME_INVALID", str(run_path)))
    except (KeyError, TypeError, ValueError):
        violations.append(violation("CANDIDATE_TIMESTAMP_INVALID", str(run_path)))

    result_relative = manifest.get("result_path", "")
    result_path = repository_file(repo_root, result_relative)
    if run.get("result_path") != result_relative:
        violations.append(violation("CANDIDATE_RESULT_PATH_MISMATCH", str(run_path)))
    if result_path is None or not result_path.is_file():
        violations.append(violation("CANDIDATE_RESULT_MISSING", result_relative))
        return violations
    actual_result_hash = file_sha256(result_path)
    if run.get("result_sha256") != actual_result_hash:
        violations.append(violation("CANDIDATE_RESULT_HASH_MISMATCH", result_relative))
    result = load_json(result_path)
    if result.get("evidence_kind") != "candidate_output":
        violations.append(violation("CANDIDATE_RESULT_KIND_INVALID", result_relative))
    if result.get("started_at") != run.get("started_at") or result.get("completed_at") != run.get("completed_at"):
        violations.append(violation("CANDIDATE_RESULT_TIME_MISMATCH", result_relative))
    result_hashes = result.get("hashes", {})
    for index, item in enumerate(manifest.get("inputs", [])):
        expected = item.get("sha256", "").removeprefix("sha256:")
        if result_hashes.get(item.get("result_hash_key")) != expected:
            violations.append(violation("CANDIDATE_RESULT_INPUT_HASH_MISMATCH", f"inputs[{index}]"))

    if STAGES[required_stage] < STAGES["release"]:
        return violations
    if review_path is None or not review_path.is_file():
        violations.append(violation("HUMAN_REVIEW_RECORD_MISSING", str(review_path)))
        return violations
    review = load_json(review_path)
    if not review_record_is_valid(review):
        violations.append(violation("HUMAN_REVIEW_RECORD_INVALID", str(review_path)))
    if review.get("manifest_sha256") != manifest_hash:
        violations.append(violation("HUMAN_REVIEW_MANIFEST_HASH_MISMATCH", str(review_path)))
    if review.get("result_sha256") != actual_result_hash:
        violations.append(violation("HUMAN_REVIEW_RESULT_HASH_MISMATCH", str(review_path)))
    if review.get("slice_id") != manifest.get("slice_id"):
        violations.append(violation("HUMAN_REVIEW_SLICE_MISMATCH", str(review_path)))
    if review.get("decision") not in {"conditional_pass", "pass", "fail"}:
        violations.append(violation("HUMAN_REVIEW_DECISION_INVALID", str(review_path)))
    try:
        if parse_timestamp(review["reviewed_at"]) < parse_timestamp(run["completed_at"]):
            violations.append(violation("HUMAN_REVIEW_PRECEDES_CANDIDATE", str(review_path)))
    except (KeyError, TypeError, ValueError):
        violations.append(violation("HUMAN_REVIEW_TIMESTAMP_INVALID", str(review_path)))
    return violations


def discover_manifests(repo_root: Path) -> list[Path]:
    return sorted((repo_root / "spikes").glob("ts-*/candidate-manifest.json"))


def validate_repository_candidate_evidence(
    *, repo_root: Path, required_stage: str = "release"
) -> list[dict[str, str]]:
    slice_roots = {path.parent for path in discover_manifests(repo_root)}
    violations: list[dict[str, str]] = []
    for result_path in sorted((repo_root / "spikes").glob("ts-*/results/*.json")):
        try:
            result = load_json(result_path)
        except (OSError, json.JSONDecodeError):
            violations.append(violation("CANDIDATE_RESULT_JSON_INVALID", str(result_path)))
            continue
        if result.get("evidence_kind") != "candidate_output":
            continue
        slice_root = result_path.parent.parent
        slice_roots.add(slice_root)
        manifest_path = slice_root / "candidate-manifest.json"
        if not manifest_path.is_file():
            violations.append(violation("CANDIDATE_MANIFEST_MISSING", str(slice_root)))
            continue
        manifest = load_json(manifest_path)
        registered_paths = {manifest.get("result_path")}
        registered_paths.update(item.get("path") for item in manifest.get("historical_results", []))
        result_relative = result_path.resolve().relative_to(repo_root.resolve()).as_posix()
        if result_relative not in registered_paths:
            violations.append(violation("UNREGISTERED_CANDIDATE_OUTPUT", result_relative))

    for slice_root in sorted(slice_roots):
        manifest_path = slice_root / "candidate-manifest.json"
        if not manifest_path.is_file():
            continue
        violations.extend(validate_candidate_evidence(
            repo_root=repo_root,
            manifest_path=manifest_path,
            authorization_path=slice_root / "candidate-authorization.json",
            run_path=slice_root / "candidate-run.json",
            review_path=slice_root / "candidate-human-review.json",
            required_stage=required_stage,
        ))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate candidate authorization and evidence ordering")
    parser.add_argument("command", choices=("validate", "discover"))
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--stage", choices=tuple(STAGES), default="release")
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    if args.command == "discover":
        violations = validate_repository_candidate_evidence(repo_root=args.repo_root, required_stage=args.stage)
    else:
        if args.manifest is None:
            parser.error("--manifest is required for validate")
        slice_root = args.manifest.parent
        violations = validate_candidate_evidence(
            repo_root=args.repo_root,
            manifest_path=args.manifest,
            authorization_path=slice_root / "candidate-authorization.json",
            run_path=slice_root / "candidate-run.json",
            review_path=slice_root / "candidate-human-review.json",
            required_stage=args.stage,
        )
    print(json.dumps({"stage": args.stage, "pass": not violations, "violations": violations}, indent=2))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
