"""Generate the fourth source-priority repair batch."""
from __future__ import annotations

import argparse
import json

from .source_priority_repair_batch_common import build_batch


BATCH_OFFSET = 420
BATCH_LIMIT = 150
BATCH_NUMBER = 4


def build(limit: int = BATCH_LIMIT, *, offset: int = BATCH_OFFSET, render_outputs: bool = False) -> dict:
    return build_batch(batch_number=BATCH_NUMBER, offset=offset, limit=limit, render_outputs=render_outputs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=BATCH_LIMIT)
    parser.add_argument("--offset", type=int, default=BATCH_OFFSET)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args(argv)
    report = build(limit=args.limit, offset=args.offset, render_outputs=args.render)
    print(json.dumps({
        "status": report["status"],
        "batch_offset": report["batch_offset"],
        "batch_size": report["batch_size"],
        "summary": report["summary"],
        "outputs": report["outputs"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
