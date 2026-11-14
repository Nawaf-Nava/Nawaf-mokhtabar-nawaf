#!/usr/bin/env python3
"""Upload a completed Strix run bundle to a configured viewer deployment.

This utility transports results only; it does not start scans or execute targets.
"""

# ruff: noqa: T201

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, cast
from urllib.parse import urlsplit


_RUN_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_MAX_ARCHIVE_BYTES = 48 * 1024 * 1024
_ALLOWED_FILES = frozenset(
    {
        "run.json",
        "vulnerabilities.json",
        "vulnerabilities.csv",
        "penetration_test_report.md",
        "findings.sarif",
        "events.jsonl",
        "coverage.json",
        ".state/agents.json",
        ".state/agents.db",
    }
)
_TERMINAL_STATUSES = frozenset({"completed", "failed", "stopped", "interrupted"})


def _included_files(run_dir: Path) -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = []
    for path in run_dir.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(run_dir).as_posix()
        if relative in _ALLOWED_FILES or (
            PurePosixPath(relative).parent.as_posix() == "vulnerabilities"
            and path.suffix == ".md"
        ):
            files.append((path, relative))
    return files


def _bundle(run_dir: Path, run_name: str) -> bytes:
    if not _RUN_NAME.fullmatch(run_name):
        raise ValueError("Invalid run name")
    record_path = run_dir / "run.json"
    record: Any = json.loads(record_path.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise TypeError("Run record is not a JSON object")
    run_record = cast("dict[str, Any]", record)
    if (
        run_record.get("run_name") != run_name
        or run_record.get("status") not in _TERMINAL_STATUSES
        or not run_record.get("end_time")
    ):
        raise ValueError("Only completed/terminal runs with a matching run_name can be uploaded")

    output = io.BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, relative in _included_files(run_dir):
            archive.write(path, relative)
    payload = output.getvalue()
    if len(payload) > _MAX_ARCHIVE_BYTES:
        raise ValueError("Run artifact bundle exceeds the 48 MiB upload limit")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_name", help="Completed run name under STRIX_RUNS_DIR")
    args = parser.parse_args()

    base_url = os.environ.get("STRIX_VIEWER_URL", "").rstrip("/")
    token = os.environ.get("STRIX_WORKER_TOKEN", "")
    parsed = urlsplit(base_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.path not in ("", "/"):
        print("ERROR: STRIX_VIEWER_URL must be an HTTPS origin.", file=sys.stderr)
        return 2
    if len(token) < 32:
        print("ERROR: STRIX_WORKER_TOKEN must be at least 32 characters.", file=sys.stderr)
        return 2

    run_dir = Path(os.environ.get("STRIX_RUNS_DIR", "strix_runs")) / args.run_name
    try:
        payload = _bundle(run_dir, args.run_name)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"ERROR: Cannot prepare run bundle: {exc}", file=sys.stderr)
        return 2

    request = urllib.request.Request(  # noqa: S310 - URL origin is validated as HTTPS above
        f"{base_url}/api/worker/runs",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/zip",
            "X-Strix-Run-Name": args.run_name,
        },
        method="POST",
    )
    try:
        # URL origin was restricted to HTTPS above; this is a deliberate upload.
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310  # nosec B310
            result = json.loads(response.read())
            if response.status != 201 or result.get("ok") is not True:
                print("ERROR: Viewer rejected the run bundle.", file=sys.stderr)
                return 1
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        print("ERROR: Could not upload the run bundle to the viewer.", file=sys.stderr)
        return 1

    print(f"Uploaded completed run {args.run_name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
