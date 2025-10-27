#!/usr/bin/env python3
"""
Orchestrate registering and preparing custom competitions from local data.

This script calls the sibling scripts:
  - register_custom_competitions.py
  - prepare_custom_competitions.py

Flow
1) Run register to scaffold competitions under mlebench/competitions.
2) Run prepare for only the newly created competitions (and any extra IDs).

Examples
  python scripts/add_new_competition/orchestrate_custom_competitions.py \
    --custom-root ./custom_data --register-limit 10 --force

  python scripts/add_new_competition/orchestrate_custom_competitions.py \
    --skip-register --ids freiburg-groceries waste-classification
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = Path(__file__).resolve().parent


def run_cmd(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def parse_json_stdout(stdout: str) -> dict:
    stdout = stdout.strip()
    try:
        return json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        # Best-effort: find last JSON object in output
        last_brace = stdout.rfind("}")
        first_brace = stdout.find("{")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            snippet = stdout[first_brace : last_brace + 1]
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                pass
        raise


def main():
    parser = argparse.ArgumentParser(description="Register and prepare custom competitions (local data)")
    parser.add_argument("--custom-root", type=str, default=str(REPO_ROOT / "custom_data"), help="Path to custom_data root")
    parser.add_argument("--register-limit", type=int, default=None, help="Limit number of datasets to register")
    parser.add_argument("--skip-register", action="store_true", help="Skip the registration step and only prepare")
    parser.add_argument("--ids", nargs="*", help="Explicit competition IDs to prepare (in addition to newly created ones)")
    parser.add_argument("--data-dir", type=str, default=None, help="Override registry data dir for preparation")
    parser.add_argument("--force", action="store_true", help="Force re-preparation even if already prepared")
    parser.add_argument("--no-checksums", action="store_true", help="Skip checksum generation during preparation")
    args = parser.parse_args()

    register_script = SCRIPTS_DIR / "register_custom_competitions.py"
    prepare_script = SCRIPTS_DIR / "prepare_custom_competitions.py"

    summary: dict = {"register": None, "prepare": None}

    created_ids: list[str] = []

    if not args.skip_register:
        cmd = [sys.executable, str(register_script), "--custom-root", args.custom_root]
        if args.register_limit is not None:
            cmd += ["--limit", str(args.register_limit)]

        rc, out, err = run_cmd(cmd)
        summary["register"] = {"rc": rc, "stdout": out, "stderr": err, "cmd": shlex.join(cmd)}
        if rc != 0:
            print(json.dumps(summary, indent=2))
            sys.exit(rc)

        try:
            payload = parse_json_stdout(out)
            created_ids = payload.get("created_competitions", []) or []
        except Exception:
            # Continue but with no created list
            created_ids = []

    # Merge explicit ids
    to_prepare: list[str] = []
    if created_ids:
        to_prepare.extend(created_ids)
    if args.ids:
        to_prepare.extend(args.ids)

    # Deduplicate while preserving order
    seen = set()
    to_prepare_unique = []
    for cid in to_prepare:
        if cid not in seen:
            seen.add(cid)
            to_prepare_unique.append(cid)

    if not to_prepare_unique:
        summary["prepare"] = {"skipped": True, "reason": "No competition IDs to prepare."}
        print(json.dumps(summary, indent=2))
        return

    # Prepare step
    cmd = [sys.executable, str(prepare_script), "--ids", *to_prepare_unique]
    if args.data_dir:
        cmd += ["--data-dir", args.data_dir]
    if args.force:
        cmd += ["--force"]
    if args.no_checksums:
        cmd += ["--no-checksums"]

    rc, out, err = run_cmd(cmd)
    summary["prepare"] = {"rc": rc, "stdout": out, "stderr": err, "cmd": shlex.join(cmd)}

    print(json.dumps(summary, indent=2))
    sys.exit(rc)


if __name__ == "__main__":
    main()


