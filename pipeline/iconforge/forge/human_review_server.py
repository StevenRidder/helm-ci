"""Serve the Icon Forge human review page and collect feedback.

Run:
  python3 -m forge.human_review_server --port 9017
"""
from __future__ import annotations

import argparse
import csv
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import human_review_page


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "human_review"
FEEDBACK_JSON = OUT / "icon_review_feedback.json"
FEEDBACK_CSV = OUT / "icon_review_feedback.csv"
SIGNOFF_JSON = OUT / "icon_review_signoff.json"
SIGNOFF_CSV = OUT / "icon_review_signoff.csv"


CSV_FIELDS = [
    "asset",
    "name",
    "status",
    "needs_remediation",
    "priority",
    "reason_codes",
    "feedback",
    "expected_change",
]

SIGNOFF_FIELDS = [
    "asset",
    "name",
    "status",
    "final_decision",
    "final_approved",
    "needs_remediation",
    "priority",
    "reason_codes",
    "feedback",
    "expected_change",
]


class ReviewHandler(SimpleHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802 - http.server API
        if self.path not in {"/api/save-review", "/api/save-signoff"}:
            self.send_error(404, "unknown endpoint")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            rows = payload.get("rows") or []
            if self.path == "/api/save-review":
                result = _write_feedback(rows)
            else:
                result = _write_signoff(rows)
        except Exception as exc:  # noqa: BLE001 - show useful browser error.
            self.send_error(400, str(exc))
            return
        body = json.dumps(result).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _merge_rows(path: Path, rows: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text()).get("rows") or []
        except json.JSONDecodeError:
            existing = []
        for row in existing:
            asset = row.get("asset")
            if asset:
                merged[str(asset)] = row
    for row in rows:
        asset = row.get("asset")
        if asset:
            merged[str(asset)] = row
    return [merged[key] for key in sorted(merged)]


def _write_feedback(rows: list[dict]) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    merged_rows = _merge_rows(FEEDBACK_JSON, rows)
    payload = {
        "schema": "helm.iconforge.human_review.v1",
        "rows": merged_rows,
        "checked_rows": [row for row in merged_rows if row.get("needs_remediation")],
    }
    FEEDBACK_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with FEEDBACK_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in merged_rows:
            if not row.get("needs_remediation"):
                continue
            writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})
    return {
        "status": "saved",
        "rows": len(merged_rows),
        "submitted_rows": len(rows),
        "checked_rows": len(payload["checked_rows"]),
        "json": str(FEEDBACK_JSON.relative_to(ROOT)),
        "csv": str(FEEDBACK_CSV.relative_to(ROOT)),
    }


def _write_signoff(rows: list[dict]) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    merged_rows = _merge_rows(SIGNOFF_JSON, rows)
    approved = [
        row for row in merged_rows
        if row.get("final_approved") or row.get("final_decision") == "approve"
    ]
    rejected = [row for row in merged_rows if row.get("final_decision") == "reject_remediate"]
    feedback_result = _write_feedback(_rejected_feedback_rows(rejected)) if rejected else None
    payload = {
        "schema": "helm.iconforge.human_signoff.v1",
        "rows": merged_rows,
        "approved_rows": approved,
        "rejected_rows": rejected,
    }
    SIGNOFF_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with SIGNOFF_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SIGNOFF_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in merged_rows:
            if row.get("final_decision") == "pending" and not row.get("feedback"):
                continue
            writer.writerow({field: row.get(field, "") for field in SIGNOFF_FIELDS})
    return {
        "status": "saved",
        "rows": len(merged_rows),
        "submitted_rows": len(rows),
        "approved_rows": len(approved),
        "rejected_rows": len(rejected),
        "repair_feedback_rows": feedback_result["checked_rows"] if feedback_result else 0,
        "json": str(SIGNOFF_JSON.relative_to(ROOT)),
        "csv": str(SIGNOFF_CSV.relative_to(ROOT)),
        "repair_feedback_json": str(FEEDBACK_JSON.relative_to(ROOT)),
        "repair_feedback_csv": str(FEEDBACK_CSV.relative_to(ROOT)),
    }


def _rejected_feedback_rows(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        feedback = row.get("feedback") or ""
        expected = row.get("expected_change") or ""
        out.append({
            "asset": row.get("asset"),
            "name": row.get("name"),
            "status": "final_review_rejected",
            "needs_remediation": True,
            "priority": row.get("priority") or "high",
            "reason_codes": row.get("reason_codes") or "human_final_reject;final_approval_rejected",
            "feedback": feedback,
            "expected_change": expected or feedback,
            "source": "final_signoff_reject_to_repair",
        })
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9017)
    args = parser.parse_args(argv)
    human_review_page.build()
    server = ThreadingHTTPServer((args.host, args.port), ReviewHandler)
    print(f"serving http://{args.host}:{args.port}/out/human_review/icon_review.html")
    print(f"signoff http://{args.host}:{args.port}/out/human_review/pass_review.html")
    print(f"feedback csv: {FEEDBACK_CSV}")
    print(f"signoff csv: {SIGNOFF_CSV}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
