#!/usr/bin/env python3
"""
Prepare all custom competitions that were registered (no Kaggle download).

This script calls the local prepare helper for each specified competition id,
or discovers all competitions under mlebench/competitions that match a
provided prefix.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure repository root is on sys.path so we can import prepare_local_competition.py
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from prepare_local_competition import prepare_local_competition


REPO_ROOT = Path(__file__).resolve().parents[2]
COMP_DIR = REPO_ROOT / "mlebench" / "competitions"


def list_competitions(prefix: str | None = None) -> list[str]:
    comps = []
    for cfg in sorted(COMP_DIR.rglob("config.yaml")):
        comp_id = cfg.parent.name
        if prefix is None or comp_id.startswith(prefix):
            comps.append(comp_id)
    return comps


def main():
    parser = argparse.ArgumentParser(description="Prepare custom competitions (local data)")
    parser.add_argument("--ids", nargs="*", help="Competition IDs to prepare. If omitted, use --prefix.")
    parser.add_argument("--prefix", type=str, default=None, help="Prepare competitions whose id starts with this prefix.")
    parser.add_argument("--data-dir", type=str, default=None, help="Override data dir (registry cache dir by default)")
    parser.add_argument("--force", action="store_true", help="Force re-preparation")
    parser.add_argument("--no-checksums", action="store_true", help="Skip checksum generation")
    args = parser.parse_args()

    comp_ids = args.ids if args.ids else list_competitions(prefix=args.prefix)

    results = {}
    for comp_id in comp_ids:
        try:
            prepare_local_competition(
                competition_id=comp_id,
                data_dir=Path(args.data_dir) if args.data_dir else None,
                force=args.force,
                generate_checksums_flag=not args.no_checksums,
            )
            results[comp_id] = "ok"
        except Exception as e:
            results[comp_id] = f"error: {e}"

    print(json.dumps({"prepared": results}, indent=2))


if __name__ == "__main__":
    main()


