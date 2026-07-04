"""Smoke the FORGE-50 runtime DB contract.

Run:  python3 -m forge.tests.test_runtime_db_contract
"""
from __future__ import annotations

import hashlib
import json
import runpy
import shutil
import sqlite3
import tempfile
from pathlib import Path

from .. import runtime_db_contract


REPO = runtime_db_contract.REPO
SCRIPT = REPO / "scripts" / "augment-opencpn-s52-s101-semantics.py"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_db(tmpdir: Path) -> Path:
    copy_path = tmpdir / "opencpn_s52_portrayal.sqlite"
    shutil.copy2(runtime_db_contract.DB_PATH, copy_path)
    return copy_path


def _checks(payload: dict) -> dict[str, dict]:
    return {check["name"]: check for check in payload["checks"]}


def _pick_candidate(con: sqlite3.Connection) -> int:
    row = con.execute("SELECT s52_lookup_id FROM runtime_symbol_candidate_v1 ORDER BY s52_lookup_id LIMIT 1").fetchone()
    assert row is not None
    return int(row[0])


def _force_candidate_flags_runtime_clear(con: sqlite3.Connection, lookup_id: int) -> None:
    con.execute(
        """
        UPDATE runtime_symbol_candidate
        SET runtime_eligible = 1,
            candidate_status = 'runtime_eligible',
            blocking_gate_count = 0,
            pending_gate_count = 0
        WHERE s52_lookup_id = ?
        """,
        (lookup_id,),
    )


def test_saved_contract_matches_current_db() -> None:
    saved = json.loads(runtime_db_contract.CONTRACT_JSON.read_text())
    saved_mtime = runtime_db_contract.CONTRACT_JSON.stat().st_mtime_ns

    payload = runtime_db_contract.build_contract()
    assert payload["schema"] == "helm.iconforge.runtime_db_contract.v1"
    assert payload["status"] == "contract_pass"
    assert payload["summary"]["lookup_rows"] == 3057
    assert payload["summary"]["candidate_rows"] == 3057
    assert payload["summary"]["runtime_eligible_rows"] == 0
    assert payload["summary"]["runtime_symbol_portrayal_rows"] == 0
    assert payload["summary"]["blocker_rows"] == 4410
    assert payload["summary"]["visual_approval_pending_rows"] == 3057
    assert tuple(payload["summary"]["required_runtime_gates"]) == runtime_db_contract.RUNTIME_REQUIRED_GATES
    assert payload["summary"]["candidate_status_counts"] == {
        "blocked": 336,
        "review_candidate": 2721,
    }

    checks = _checks(payload)
    for name in (
        "sqlite_integrity_check",
        "sqlite_foreign_key_check",
        "runtime_candidate_view_covers_lookup_rows",
        "runtime_blocker_view_explains_ineligible_rows",
        "runtime_portrayal_view_is_strict_gate_clear_surface",
        "runtime_required_gates_cover_all_candidates",
        "runtime_eligibility_matches_gate_state",
        "blocker_rows_are_queryable",
        "zero_runtime_rows_are_deliberate_fail_closed",
        "import_audit_has_no_fail_rows",
    ):
        assert checks[name]["status"] == "pass"

    strict = checks["runtime_portrayal_view_is_strict_gate_clear_surface"]["actual"]
    assert strict["runtime_symbol_portrayal_v1"] == 0
    assert strict["derived_gate_clear_rows"] == 0
    assert strict["leaky_rows"] == 0
    assert strict["missing_required_gate_rows"] == 0

    fail_closed = checks["zero_runtime_rows_are_deliberate_fail_closed"]["actual"]
    assert fail_closed["runtime_eligible_rows"] == 0
    assert fail_closed["runtime_symbol_portrayal_v1"] == 0
    assert fail_closed["visual_approval_pending_rows"] == 3057

    blockers = checks["runtime_blocker_view_explains_ineligible_rows"]["actual"]
    assert blockers["ineligible_without_blockers"] == 0

    assert saved == payload
    assert runtime_db_contract.CONTRACT_JSON.stat().st_mtime_ns == saved_mtime
    assert runtime_db_contract.CONTRACT_MD.exists()


def test_runtime_flag_update_attack_fails_contract() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _copy_db(Path(tmp))
        with sqlite3.connect(db_path) as con:
            lookup_id = _pick_candidate(con)
            _force_candidate_flags_runtime_clear(con, lookup_id)
            con.commit()

        payload = runtime_db_contract.build_contract(db_path=db_path)
        checks = _checks(payload)
        assert payload["status"] == "contract_fail"
        assert checks["runtime_eligibility_matches_gate_state"]["status"] == "fail"
        assert checks["runtime_portrayal_view_is_strict_gate_clear_surface"]["status"] == "pass"
        strict = checks["runtime_portrayal_view_is_strict_gate_clear_surface"]["actual"]
        assert strict["runtime_symbol_portrayal_v1"] == 0
        assert strict["derived_gate_clear_rows"] == 0
        assert strict["leaky_rows"] == 0


def test_missing_gate_attack_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _copy_db(Path(tmp))
        with sqlite3.connect(db_path) as con:
            lookup_id = _pick_candidate(con)
            _force_candidate_flags_runtime_clear(con, lookup_id)
            con.execute("DELETE FROM runtime_symbol_gate WHERE s52_lookup_id = ?", (lookup_id,))
            con.commit()

        payload = runtime_db_contract.build_contract(db_path=db_path)
        checks = _checks(payload)
        assert payload["status"] == "contract_fail"
        assert checks["runtime_required_gates_cover_all_candidates"]["status"] == "fail"
        assert checks["runtime_eligibility_matches_gate_state"]["status"] == "fail"
        strict = checks["runtime_portrayal_view_is_strict_gate_clear_surface"]["actual"]
        assert strict["runtime_symbol_portrayal_v1"] == 0
        assert strict["derived_gate_clear_rows"] == 0
        assert strict["leaky_rows"] == 0


def test_failed_import_audit_row_fails_contract() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _copy_db(Path(tmp))
        with sqlite3.connect(db_path) as con:
            con.execute(
                """
                INSERT OR REPLACE INTO s52_s101_import_audit (check_name, status, expected, actual, detail)
                VALUES ('fixture_forced_failure', 'fail', 'pass', 'fail', 'test fixture')
                """
            )
            con.commit()

        payload = runtime_db_contract.build_contract(db_path=db_path)
        checks = _checks(payload)
        assert payload["status"] == "contract_fail"
        assert checks["import_audit_has_no_fail_rows"]["status"] == "fail"


def test_atomic_augment_failure_preserves_original_db() -> None:
    module = runpy.run_path(str(SCRIPT))
    augment = module["augment"]
    audit_failure = module["AuditFailure"]

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        db_path = _copy_db(tmpdir)
        missing_approval_root = tmpdir / "missing-approval-root"
        before = _sha256(db_path)
        try:
            augment(db_path, missing_approval_root, atomic=True)
        except audit_failure:
            pass
        else:
            raise AssertionError("augment should fail when approval artifacts are missing")
        after = _sha256(db_path)
        assert after == before
        assert not list(tmpdir.glob(f".{db_path.name}.*.tmp"))


def main() -> None:
    test_saved_contract_matches_current_db()
    test_runtime_flag_update_attack_fails_contract()
    test_missing_gate_attack_fails_closed()
    test_failed_import_audit_row_fails_contract()
    test_atomic_augment_failure_preserves_original_db()
    print("runtime DB contract: OK")


if __name__ == "__main__":
    main()
