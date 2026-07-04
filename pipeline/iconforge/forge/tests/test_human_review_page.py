"""Smoke the human remediation review page.

Run:  python3 -m forge.tests.test_human_review_page
"""
from __future__ import annotations

import csv
import tempfile
from pathlib import Path

from .. import human_review_page
from .. import human_review_server


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    result = human_review_page.build(limit=12)
    assert result["status"] == "human_review_page_written"
    assert result["summary"]["rows"] == 12
    assert result["summary"]["default_remediation_rows"] == 0

    html_path = ROOT / result["outputs"]["html"]
    pass_html_path = ROOT / result["outputs"]["pass_html"]
    db_html_path = ROOT / result["outputs"]["db_html"]
    csv_path = ROOT / result["outputs"]["csv"]
    assert html_path.exists()
    assert pass_html_path.exists()
    assert db_html_path.exists()
    assert csv_path.exists()

    html = html_path.read_text()
    assert "Helm Icon Forge Human Review" in html
    assert "needs remediation" in html
    assert "Submit this row" in html
    assert "Final sign-off" in html
    assert "Export checked CSV" in html
    assert "icon_review_remediation.csv" in html
    assert "helm.iconforge.human_review.v1" in html
    assert "/api/save-review" in html
    assert "db_review.html" in html

    pass_html = pass_html_path.read_text()
    assert "Helm Icon Forge Final Sign-Off" in pass_html
    assert "S-101 shape witness" in pass_html
    assert "raw SVG is not color-resolved portrayal" in pass_html
    assert "approveRow" in pass_html
    assert "rejectRow" in pass_html
    assert "Save all sign-offs" in pass_html
    assert "pending queue" in pass_html
    assert "helm.iconforge.human_signoff.v1" in pass_html
    assert "/api/save-signoff" in pass_html

    db_html = db_html_path.read_text()
    assert "Helm Icon Forge DB Evidence Review" in db_html
    assert "/api/proof-review/rows?limit=100" in db_html
    assert "helm.iconforge.db_review_api.v1" in db_html
    assert "Runtime blocked" in db_html

    rows = list(csv.DictReader(csv_path.open()))
    assert len(rows) == 12
    for field in [
        "asset",
        "status",
        "needs_remediation",
        "priority",
        "reason_codes",
        "feedback",
        "expected_change",
        "helm_svg",
    ]:
        assert field in rows[0]
    assert all(row["needs_remediation"] == "false" for row in rows)
    _smoke_s101_shape_witness_label()
    _smoke_reject_to_repair()
    print("human review page: OK")


def _smoke_s101_shape_witness_label() -> None:
    table = human_review_page._read_json(human_review_page.TABLE)
    row = next(item for item in table["rows"] if item["asset"] == "BOYPIL60")
    payload = human_review_page._row_payload(row)
    assert payload["s101_symbol_id"] == "BOYPIL60"
    assert payload["required_colours"] == "red"
    assert "shape witness" in payload["s101_witness_note"]
    assert "required colours: red" in payload["s101_witness_note"]


def _smoke_reject_to_repair() -> None:
    original = {
        "ROOT": human_review_server.ROOT,
        "OUT": human_review_server.OUT,
        "FEEDBACK_JSON": human_review_server.FEEDBACK_JSON,
        "FEEDBACK_CSV": human_review_server.FEEDBACK_CSV,
        "SIGNOFF_JSON": human_review_server.SIGNOFF_JSON,
        "SIGNOFF_CSV": human_review_server.SIGNOFF_CSV,
    }
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        out = tmp / "out" / "human_review"
        human_review_server.ROOT = tmp
        human_review_server.OUT = out
        human_review_server.FEEDBACK_JSON = out / "icon_review_feedback.json"
        human_review_server.FEEDBACK_CSV = out / "icon_review_feedback.csv"
        human_review_server.SIGNOFF_JSON = out / "icon_review_signoff.json"
        human_review_server.SIGNOFF_CSV = out / "icon_review_signoff.csv"
        try:
            result = human_review_server._write_signoff([{
                "asset": "TEST01",
                "name": "test icon",
                "status": "judge_pass_pending_final_approval",
                "final_decision": "reject_remediate",
                "final_approved": False,
                "needs_remediation": True,
                "priority": "high",
                "reason_codes": "human_final_reject;final_approval_rejected",
                "feedback": "Move the mark left.",
                "expected_change": "Move left.",
            }])
            assert result["rejected_rows"] == 1
            assert result["repair_feedback_rows"] == 1
            signoff = human_review_server.SIGNOFF_JSON.read_text()
            feedback = human_review_server.FEEDBACK_JSON.read_text()
            assert "TEST01" in signoff
            assert "final_approval_rejected" in feedback
            feedback_rows = list(csv.DictReader(human_review_server.FEEDBACK_CSV.open()))
            assert feedback_rows[0]["asset"] == "TEST01"
            assert feedback_rows[0]["needs_remediation"] == "True"
        finally:
            human_review_server.ROOT = original["ROOT"]
            human_review_server.OUT = original["OUT"]
            human_review_server.FEEDBACK_JSON = original["FEEDBACK_JSON"]
            human_review_server.FEEDBACK_CSV = original["FEEDBACK_CSV"]
            human_review_server.SIGNOFF_JSON = original["SIGNOFF_JSON"]
            human_review_server.SIGNOFF_CSV = original["SIGNOFF_CSV"]


if __name__ == "__main__":
    main()
