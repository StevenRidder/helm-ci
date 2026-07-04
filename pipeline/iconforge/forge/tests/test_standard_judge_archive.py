"""Smoke the standard judge archive helper.

Run:  python -m forge.tests.test_standard_judge_archive
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from .. import standard_judge_archive


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    out_dir = ROOT / "out" / "standard_source_table"
    out_dir.mkdir(parents=True, exist_ok=True)
    src_json = ROOT / "catalog" / "standard_judge_batch_003.json"
    src_md = ROOT / "catalog" / "standard_judge_batch_003.md"
    test_id = "standard_judge_batch_archive_smoke"
    shutil.copyfile(src_json, out_dir / f"{test_id}.json")
    if src_md.exists():
        shutil.copyfile(src_md, out_dir / f"{test_id}.md")
    result = standard_judge_archive.archive(test_id)
    assert result["status"] == "archived_standard_judge_batch"
    assert result["batch_id"] == test_id
    assert (ROOT / result["archived"]["json"]).exists()
    saved = json.loads((ROOT / result["archived"]["json"]).read_text())
    assert saved["summary"]["rows_judged"] == 29
    for rel in [result["archived"]["json"], result["archived"]["markdown"]]:
        if rel:
            (ROOT / rel).unlink(missing_ok=True)
    (out_dir / f"{test_id}.json").unlink(missing_ok=True)
    (out_dir / f"{test_id}.md").unlink(missing_ok=True)
    print("standard judge archive: OK")


if __name__ == "__main__":
    main()
