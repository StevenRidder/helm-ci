"""Archive standard judge batch outputs and refresh table/repair queue.

Run:
  python -m forge.standard_judge_archive standard_judge_batch_004
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import standard_repair_queue
from . import standard_source_table


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
OUT = ROOT / "out" / "standard_source_table"


def archive(batch_id: str) -> dict:
    src_json = OUT / f"{batch_id}.json"
    src_md = OUT / f"{batch_id}.md"
    if not src_json.exists():
        raise FileNotFoundError(src_json)
    dst_json = CATALOG / f"{batch_id}.json"
    dst_md = CATALOG / f"{batch_id}.md"
    data = json.loads(src_json.read_text())
    dst_json.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    if src_md.exists():
        dst_md.write_text(src_md.read_text().rstrip() + "\n")
    table = standard_source_table.build()
    repair = standard_repair_queue.build()
    return {
        "status": "archived_standard_judge_batch",
        "batch_id": batch_id,
        "archived": {
            "json": str(dst_json.relative_to(ROOT)),
            "markdown": str(dst_md.relative_to(ROOT)) if src_md.exists() else None,
        },
        "judge_summary": data.get("summary", {}),
        "source_table_summary": table["summary"],
        "repair_queue_summary": repair["summary"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("batch_id")
    args = parser.parse_args(argv)
    print(json.dumps(archive(args.batch_id), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
