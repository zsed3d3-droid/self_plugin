#!/usr/bin/env python3
"""Export a complete reviewed catalog from a read-only SQLite transaction.

CLI: sync-decisions.py --db review.sqlite --catalog catalog.json --output profile.json [--check]
Format da-development-decisions/v1 is deterministic: no local paths, request IDs,
credential fields, or inferred policy. Rejected rules stay rejected; their user's
verbatim reason must be interpreted by the consuming policy, never inverted here.
The output watermark and prior event references support later re-review and audit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

FORMAT = "da-development-decisions/v1"
CREDENTIAL_NAMES = {
    "auth.json", "credentials.json", "credential.json", "secrets.json",
    "secret.json", "tokens.json", "token.json", "keys.json", "key.json",
    "config.json", "service-account.json",
}
SENSITIVE_DIRS = {".ssh", ".aws", ".gnupg", ".git", ".docker", ".kube", ".azure"}


class SyncError(ValueError):
    """Incomplete, stale or unsafe input; no output should be changed."""


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: object) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise SyncError(f"Cannot read valid JSON: {path.name}") from error


def catalog_snapshots(catalog: object) -> tuple[str, dict[str, dict]]:
    if not isinstance(catalog, dict) or not isinstance(catalog.get("version"), str):
        raise SyncError("Catalog must have a string version")
    if not isinstance(catalog.get("experts"), list):
        raise SyncError("Catalog must contain experts")
    snapshots = {}
    for expert in catalog["experts"]:
        if not isinstance(expert, dict) or not isinstance(expert.get("name"), str):
            raise SyncError("Catalog expert must have a name")
        if not isinstance(expert.get("field"), str) or not isinstance(expert.get("sources"), list):
            raise SyncError("Catalog expert must have field and sources")
        if not isinstance(expert.get("rules"), list):
            raise SyncError("Catalog expert must have rules")
        for rule in expert["rules"]:
            if not isinstance(rule, dict) or not isinstance(rule.get("id"), str) or not rule["id"]:
                raise SyncError("Catalog rule must have a nonempty id")
            if rule["id"] in snapshots:
                raise SyncError(f"Duplicate catalog rule: {rule['id']}")
            for field in ("title", "rule", "when", "test", "recommendation"):
                if not isinstance(rule.get(field), str):
                    raise SyncError(f"Catalog rule {rule['id']} is missing {field}")
            snapshots[rule["id"]] = {
                "expert": expert["name"], "field": expert["field"],
                "sources": expert["sources"], **rule,
            }
    if not snapshots:
        raise SyncError("Catalog has no rules")
    return catalog["version"], snapshots


def read_events(db_path: Path) -> list[dict]:
    if not db_path.is_file():
        raise SyncError("Review database does not exist")
    try:
        connection = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA query_only=ON")
            connection.execute("BEGIN")
            # Read the entire evidence journal once, inside one SQLite snapshot.
            rows = connection.execute(
                "SELECT event_id,rule_id,report_version,decision,reason,revision,"
                "created_at,rule_snapshot FROM decision_events ORDER BY event_id"
            ).fetchall()
            events = [dict(row) for row in rows]
            connection.commit()
        finally:
            connection.close()
    except sqlite3.Error as error:
        raise SyncError(f"Cannot read review journal: {error}") from error
    return events


def build_profile(db_path: Path, catalog_path: Path) -> dict:
    version, expected = catalog_snapshots(read_json(catalog_path))
    events = read_events(db_path)
    grouped: dict[str, list[dict]] = {}
    for event in events:
        rule_id = event["rule_id"]
        if rule_id not in expected:
            raise SyncError(f"Journal contains a rule absent from catalog: {rule_id}")
        if not isinstance(event["revision"], int) or event["revision"] < 1:
            raise SyncError(f"Invalid revision for {rule_id}")
        if not isinstance(event["event_id"], int) or event["event_id"] < 1:
            raise SyncError(f"Invalid event id for {rule_id}")
        try:
            snapshot = json.loads(event.pop("rule_snapshot"))
        except (ValueError, TypeError) as error:
            raise SyncError(f"Invalid saved rule snapshot for {rule_id}") from error
        if not isinstance(snapshot, dict) or snapshot.get("id") != rule_id:
            raise SyncError(f"Missing or inconsistent saved rule snapshot for {rule_id}")
        event["rule_snapshot"] = snapshot
        grouped.setdefault(rule_id, []).append(event)

    missing = sorted(expected.keys() - grouped.keys())
    if missing:
        raise SyncError("Review incomplete; missing decisions: " + ", ".join(missing))

    decisions = []
    counts = {"adopt": 0, "reject": 0}
    for rule_id in sorted(expected):
        history = sorted(grouped[rule_id], key=lambda event: event["revision"])
        revisions = [event["revision"] for event in history]
        if len(revisions) != len(set(revisions)):
            raise SyncError(f"Duplicate revision for {rule_id}")
        current = history[-1]
        if current["decision"] not in counts:
            raise SyncError(f"Review incomplete; {rule_id} is not adopted or rejected")
        if not isinstance(current["reason"], str) or not current["reason"].strip():
            raise SyncError(f"Review incomplete; {rule_id} has no reason")
        if current["report_version"] != version or current["rule_snapshot"] != expected[rule_id]:
            raise SyncError(f"Stale review for {rule_id}: catalog/version differs from saved snapshot")
        counts[current["decision"]] += 1
        decisions.append({
            "rule_id": rule_id,
            "event_id": current["event_id"],
            "revision": current["revision"],
            "report_version": current["report_version"],
            "decision": current["decision"],
            "reason": current["reason"],
            "created_at": current["created_at"],
            "snapshot_sha256": fingerprint(current["rule_snapshot"]),
            "rule_snapshot": current["rule_snapshot"],
            "prior_events": [
                {
                    "event_id": old["event_id"], "revision": old["revision"],
                    "report_version": old["report_version"], "decision": old["decision"],
                    "created_at": old["created_at"],
                    "snapshot_sha256": fingerprint(old["rule_snapshot"]),
                }
                for old in history[:-1]
            ],
        })
    return {
        "format": FORMAT,
        "report_version": version,
        "catalog_rules_sha256": fingerprint(expected),
        "source": {
            "journal": "decision_events",
            "event_watermark": max(event["event_id"] for event in events),
            "history_event_count": len(events),
            "latest_decision_count": len(decisions),
        },
        "counts": counts,
        "decisions": decisions,
    }


def output_preflight(output: Path, db_path: Path, catalog_path: Path) -> Path:
    if output.suffix.lower() != ".json":
        raise SyncError("Output must be a dedicated .json profile")
    if output.name.lower() in CREDENTIAL_NAMES or output.name.startswith(".env"):
        raise SyncError("Refusing a credential-like output path")
    if output.is_symlink():
        raise SyncError("Refusing a symlink output")
    resolved = output.resolve()
    if resolved in {db_path.resolve(), catalog_path.resolve()}:
        raise SyncError("Output cannot overwrite the database or catalog")
    if SENSITIVE_DIRS.intersection(resolved.parts):
        raise SyncError("Refusing an output in a credential or Git metadata directory")
    if output.exists():
        if not output.is_file():
            raise SyncError("Output is not a regular file")
        previous = read_json(output)
        if not isinstance(previous, dict) or previous.get("format") != FORMAT:
            raise SyncError("Refusing to replace an unmanaged JSON file")
    return resolved


def sync(db_path: Path, catalog_path: Path, output: Path, check: bool = False) -> dict:
    # Complete validation precedes both mkdir and output mutation.
    profile = build_profile(db_path, catalog_path)
    target = output_preflight(output, db_path, catalog_path)
    if check:
        if not target.is_file() or read_json(target) != profile:
            raise SyncError("Decision profile is missing or differs from the current completed review")
        return profile
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        descriptor, filename = tempfile.mkstemp(prefix=".decision-profile-", suffix=".tmp", dir=target.parent)
        temporary = Path(filename)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(profile, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return profile


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true", help="Read-only comparison against the latest completed review")
    args = parser.parse_args(argv)
    try:
        profile = sync(args.db, args.catalog, args.output, args.check)
    except (SyncError, OSError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    verb = "current" if args.check else "exported"
    print(f"Decision profile {verb}: {len(profile['decisions'])} rules, "
          f"{profile['counts']['adopt']} adopted, {profile['counts']['reject']} rejected; "
          f"journal watermark {profile['source']['event_watermark']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
