#!/usr/bin/env python3
"""Focused smoke test for scripts/build-s52-proof-inventory.py."""
from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build-s52-proof-inventory.py"
SOURCE_DB = ROOT / "artifacts" / "opencpn_s52_portrayal.sqlite"
SITE_INDEX = ROOT / "pipeline" / "iconforge" / "public" / "proof" / "site-index.json"


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        db = tmpdir / "opencpn_s52_portrayal.sqlite"
        site_index = tmpdir / "site-index.json"
        out = tmpdir / "s52-portrayal-inventory.json"
        shutil.copyfile(SOURCE_DB, db)
        shutil.copyfile(SITE_INDEX, site_index)

        subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--db",
                str(db),
                "--site-index",
                str(site_index),
                "--output",
                str(out),
                "--skip-upstream-check",
            ],
            check=True,
        )

        payload = json.loads(out.read_text())
        with sqlite3.connect(db) as conn:
            lookup_rows = conn.execute("select count(*) from s52_proof_inventory_lookup").fetchone()[0]
            resource_rows = conn.execute("select count(*) from s52_proof_inventory_resource").fetchone()[0]
            missing = conn.execute(
                "select value from s52_proof_inventory_summary where key='public_missing_referenced_symbols'"
            ).fetchone()[0]

        assert payload["schema"] == "helm.forge.s52_portrayal_inventory.v1"
        assert lookup_rows == payload["counts"]["lookup_rows"] == 3057
        assert resource_rows == payload["counts"]["resource_rows"] == 1495
        assert json.loads(missing)["symbols"] == [
            "ADDMRK01",
            "ADDMRK02",
            "ADDMRK05",
            "DWRTPT51",
            "PLNPOS02",
        ]
        assert payload["proof_gate"]["full_s52_proof_claim_allowed"] is False


if __name__ == "__main__":
    main()
