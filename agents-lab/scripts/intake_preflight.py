"""Validate approval metadata before weekly source CSVs are opened."""

import hashlib
import json
from datetime import date
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any, Dict, Optional


class PreflightError(ValueError):
    """A safe, non-sensitive reason that an intake cannot be processed."""


_MANIFEST_KEYS = {
    "schema_version",
    "approval_state",
    "simulation_only",
    "data_owner",
    "approver",
    "approved_at",
    "approval_record",
    "user_processing_authorized",
    "user_processing_authorized_at",
    "scope",
    "sources",
    "handling",
}
_SCOPE_KEYS = {"period", "contract_version", "contract_sha256", "input_dir"}
_APPROVAL_RECORD_KEYS = {"path", "sha256"}
_SOURCE_KEYS = {"file", "sha256"}
_HANDLING_KEYS = {
    "read_only",
    "codex_visibility",
    "evidence_policy",
    "external_sharing",
    "retention_days",
    "cleanup_owner",
}
_IDENTITY_KEYS = {"name", "title"}
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PERIOD_PATTERN = re.compile(r"^(\d{4})-W(\d{2})$")
_FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _decode_json(content):
    return json.loads(content.decode("utf-8"), object_pairs_hook=_unique_object)


def _sha256(content):
    return hashlib.sha256(content).hexdigest()


def _valid_sha256(value):
    return isinstance(value, str) and _SHA256_PATTERN.fullmatch(value) is not None


def _valid_iso_date(value):
    if not isinstance(value, str) or _DATE_PATTERN.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _validate_iso_week_dates(contract, period):
    match = _PERIOD_PATTERN.fullmatch(period) if isinstance(period, str) else None
    if match is None:
        raise PreflightError("contract period is not a valid ISO week")
    try:
        year, week = int(match.group(1)), int(match.group(2))
        expected_start = date.fromisocalendar(year, week, 1)
        expected_end = date.fromisocalendar(year, week, 7)
    except ValueError:
        raise PreflightError("contract period is not a valid ISO week")

    try:
        start_date = date.fromisoformat(contract.get("start_date"))
        end_date = date.fromisoformat(contract.get("end_date"))
    except (TypeError, ValueError):
        raise PreflightError("contract date range is invalid")
    if start_date != expected_start or end_date != expected_end:
        raise PreflightError("contract date range does not match its ISO week")


def _has_exact_keys(value, expected):
    return isinstance(value, dict) and set(value) == expected


def _nonempty_string(value):
    return isinstance(value, str) and bool(value.strip())


def _safe_filename(value):
    return (
        isinstance(value, str)
        and bool(value)
        and value not in (".", "..")
        and "/" not in value
        and "\\" not in value
        and "\x00" not in value
        and PurePosixPath(value).name == value
        and _FILENAME_PATTERN.fullmatch(value) is not None
    )


def _contract_sources(contract):
    sources = contract.get("sources")
    if not isinstance(sources, list) or not sources:
        raise PreflightError("contract source list is invalid")

    names = []
    for source in sources:
        if not isinstance(source, dict) or not _safe_filename(source.get("file")):
            raise PreflightError("contract source list is invalid")
        name = source["file"]
        if name in names:
            raise PreflightError("contract source list is invalid")
        names.append(name)
    return names


def _resolved_input_directory(input_dir):
    try:
        if input_dir.is_symlink():
            raise PreflightError("input directory must be a regular directory")
        resolved = input_dir.resolve(strict=True)
        if not resolved.is_dir():
            raise PreflightError("input directory must be a regular directory")
    except PreflightError:
        raise
    except (OSError, RuntimeError, ValueError):
        raise PreflightError("input directory is unavailable")
    return resolved


def _read_regular_file(path, description):
    try:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode):
            raise PreflightError(description + " must be a regular file")
        return path.read_bytes()
    except PreflightError:
        raise
    except OSError:
        raise PreflightError(description + " is unavailable")


def _load_manifest(manifest_path):
    try:
        metadata = manifest_path.lstat()
        if not stat.S_ISREG(metadata.st_mode):
            raise PreflightError("approval manifest must be a regular file")
        content = manifest_path.read_bytes()
        manifest = _decode_json(content)
    except PreflightError:
        raise
    except (OSError, UnicodeError, ValueError, TypeError):
        raise PreflightError("approval manifest is unavailable or invalid")

    if not isinstance(manifest, dict) or set(manifest) != _MANIFEST_KEYS:
        raise PreflightError("approval manifest fields are incomplete or unsupported")
    return manifest, _sha256(content)


def _validate_identity(identity):
    return (
        _has_exact_keys(identity, _IDENTITY_KEYS)
        and _nonempty_string(identity.get("name"))
        and _nonempty_string(identity.get("title"))
    )


def _validate_handling(handling):
    if not _has_exact_keys(handling, _HANDLING_KEYS):
        raise PreflightError("handling declaration is incomplete or unsupported")
    if (
        handling.get("read_only") is not True
        or handling.get("codex_visibility") != "aggregates_only"
        or handling.get("evidence_policy") != "safe_metadata_and_aggregates"
        or handling.get("external_sharing") is not False
        or type(handling.get("retention_days")) is not int
        or handling["retention_days"] <= 0
        or not _nonempty_string(handling.get("cleanup_owner"))
    ):
        raise PreflightError("handling declaration is unsupported")


def _approval_record_bytes(manifest_path, record):
    relative_path = record.get("path")
    if (
        not isinstance(relative_path, str)
        or not relative_path
        or "\\" in relative_path
        or "\x00" in relative_path
    ):
        raise PreflightError("approval record path is invalid")
    path_parts = relative_path.split("/")
    if any(part in ("", ".", "..") or ":" in part for part in path_parts):
        raise PreflightError("approval record path is invalid")
    parsed = PurePosixPath(relative_path)
    if parsed.is_absolute():
        raise PreflightError("approval record path is invalid")

    try:
        manifest_directory = manifest_path.resolve(strict=True).parent
        approval_path = manifest_directory.joinpath(*path_parts)
        current = manifest_directory
        for part in path_parts:
            current = current / part
            if current.is_symlink():
                raise PreflightError("approval record path must not use symlinks")
        resolved_approval = approval_path.resolve(strict=True)
        if not resolved_approval.is_relative_to(manifest_directory):
            raise PreflightError("approval record path is invalid")
    except PreflightError:
        raise
    except (OSError, RuntimeError, ValueError):
        raise PreflightError("approval record is unavailable")

    return _read_regular_file(resolved_approval, "approval record")


def _source_inventory(input_directory, expected_names, exact_inventory):
    try:
        entries = list(input_directory.iterdir())
    except OSError:
        raise PreflightError("input directory contents are unavailable")

    names = [entry.name for entry in entries]
    if len(names) != len(set(names)):
        raise PreflightError("input directory contents do not match the approved inventory")
    missing = sorted(set(expected_names) - set(names))
    if missing:
        raise PreflightError("missing source: " + missing[0])
    if exact_inventory and set(names) != set(expected_names):
        raise PreflightError("input directory contents do not match the approved inventory")

    files = {}
    for entry in entries:
        try:
            metadata = entry.lstat()
        except OSError:
            raise PreflightError("input directory contents are unavailable")
        if not stat.S_ISREG(metadata.st_mode):
            raise PreflightError("input directory contains a non-regular source entry")
        files[entry.name] = entry
    return files


def _read_approved_sources(input_directory, expected_names, declared_hashes=None, exact_inventory=True):
    files = _source_inventory(input_directory, expected_names, exact_inventory)
    contents = {}
    hashes = {}
    for name in expected_names:
        content = _read_regular_file(files[name], "source file")
        digest = _sha256(content)
        if declared_hashes is not None and digest != declared_hashes[name]:
            raise PreflightError("approved source fingerprint mismatch: " + name)
        contents[name] = content
        hashes[name] = digest
    return hashes, contents


def _simulation_path_allowed(input_directory, project_root):
    try:
        root = project_root.resolve(strict=True)
        fixtures = (root / "fixtures").resolve(strict=True)
        in_fixtures = input_directory.is_relative_to(fixtures)
    except (OSError, RuntimeError, ValueError):
        in_fixtures = False
    return in_fixtures or "simulation-only" in input_directory.parts


def _simulation_result(contract, input_dir, project_root, manifest_path):
    if manifest_path is not None:
        raise PreflightError("simulation runs must not use an approval manifest")
    input_directory = _resolved_input_directory(input_dir)
    if not _simulation_path_allowed(input_directory, project_root):
        raise PreflightError("simulation input directory is outside the allowed simulation paths")
    names = _contract_sources(contract)
    hashes, contents = _read_approved_sources(input_directory, names, exact_inventory=False)
    return {
        "run_mode": "simulation",
        "approval_manifest_sha256": None,
        "source_hashes": hashes,
        "source_contents": contents,
    }


def _real_result(manifest_path, contract, contract_sha256, period, input_dir):
    if manifest_path is None:
        raise PreflightError("approval manifest is required")

    manifest, manifest_sha256 = _load_manifest(manifest_path)
    if (
        type(manifest.get("schema_version")) is not int
        or manifest["schema_version"] != 1
        or manifest.get("approval_state") != "approved"
        or manifest.get("simulation_only") is not False
    ):
        raise PreflightError("approval manifest is not approved for a real run")

    if not _validate_identity(manifest.get("data_owner")) or not _validate_identity(manifest.get("approver")):
        raise PreflightError("owner or approver declaration is incomplete")
    if not _valid_iso_date(manifest.get("approved_at")):
        raise PreflightError("approval date is invalid")
    if (
        manifest.get("user_processing_authorized") is not True
        or not _valid_iso_date(manifest.get("user_processing_authorized_at"))
    ):
        raise PreflightError("user processing authorization is missing or invalid")

    approval_record = manifest.get("approval_record")
    if not _has_exact_keys(approval_record, _APPROVAL_RECORD_KEYS) or not _valid_sha256(approval_record.get("sha256")):
        raise PreflightError("approval record declaration is invalid")

    scope = manifest.get("scope")
    if not _has_exact_keys(scope, _SCOPE_KEYS):
        raise PreflightError("approval scope is incomplete or unsupported")
    if (
        not isinstance(period, str)
        or _PERIOD_PATTERN.fullmatch(period) is None
        or not isinstance(contract.get("period"), str)
        or contract.get("period") != period
        or scope.get("period") != period
        or not isinstance(contract.get("contract_version"), str)
        or scope.get("contract_version") != contract.get("contract_version")
        or not _valid_sha256(contract_sha256)
        or not _valid_sha256(scope.get("contract_sha256"))
        or scope.get("contract_sha256") != contract_sha256
    ):
        raise PreflightError("approval scope does not match the requested period or contract")

    input_directory = _resolved_input_directory(input_dir)
    if not isinstance(scope.get("input_dir"), str) or scope["input_dir"] != str(input_directory):
        raise PreflightError("approved input directory does not match the requested directory")

    _validate_handling(manifest.get("handling"))
    approval_bytes = _approval_record_bytes(manifest_path, approval_record)
    if _sha256(approval_bytes) != approval_record["sha256"]:
        raise PreflightError("approval record fingerprint mismatch")

    expected_names = _contract_sources(contract)
    source_entries = manifest.get("sources")
    if not isinstance(source_entries, list):
        raise PreflightError("approved source inventory is invalid")
    declared_hashes = {}
    for item in source_entries:
        if not _has_exact_keys(item, _SOURCE_KEYS):
            raise PreflightError("approved source inventory is invalid")
        name = item.get("file")
        digest = item.get("sha256")
        if not _safe_filename(name) or name in declared_hashes or not _valid_sha256(digest):
            raise PreflightError("approved source inventory is invalid")
        declared_hashes[name] = digest
    if set(declared_hashes) != set(expected_names):
        raise PreflightError("approved source inventory does not match the contract")

    hashes, contents = _read_approved_sources(input_directory, expected_names, declared_hashes)
    return {
        "run_mode": "real",
        "approval_manifest_sha256": manifest_sha256,
        "source_hashes": hashes,
        "source_contents": contents,
    }


def validate_preflight(
    manifest_path: Optional[Path],
    contract: dict,
    contract_sha256: str,
    period: str,
    input_dir: Path,
    project_root: Path,
) -> Dict[str, Any]:
    """Validate one real or explicitly allowed simulation input boundary.

    Real-mode source bytes are read only after manifest metadata, scope,
    approval-copy fingerprint, handling, and exact directory inventory pass.
    The returned byte snapshots are the bytes callers must parse.
    """
    if not isinstance(contract, dict):
        raise PreflightError("contract is invalid")
    if not isinstance(period, str) or contract.get("period") != period:
        raise PreflightError("approval scope does not match the requested period")
    _validate_iso_week_dates(contract, period)
    if contract.get("simulation_only") is True:
        return _simulation_result(contract, input_dir, project_root, manifest_path)
    return _real_result(manifest_path, contract, contract_sha256, period, input_dir)
