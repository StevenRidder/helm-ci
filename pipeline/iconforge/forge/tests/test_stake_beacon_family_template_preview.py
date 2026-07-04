from __future__ import annotations

from pathlib import Path

from forge import stake_beacon_family_template_preview as preview


ROOT = Path(__file__).resolve().parents[2]


def test_stake_beacon_family_template_preview() -> None:
    result = preview.build(render_outputs=True)

    assert result["status"] == "stake_beacon_family_template_preview_written"
    assert result["summary"]["sample_count"] == 14
    assert result["summary"]["render_count"] == 42
    assert {sample["asset"] for sample in result["samples"]} == {
        "BCNSTK02",
        "BCNSTK03",
        "BCNSTK05",
        "BCNSTK08",
        "BCNSTK60",
        "BCNSTK61",
        "BCNSTK62",
        "BCNSTK77",
        "BCNSTK78",
        "BCNSTK79",
        "BCNSTK80",
        "BCNSTK81",
        "BCNSTK82",
        "BCNSTK83",
    }

    contact_sheet = ROOT / result["outputs"]["contact_sheet"]
    assert contact_sheet.exists()

    for sample in result["samples"]:
        svg = (ROOT / sample["svg"]).read_text()
        assert 'data-origin="generated-owned-artwork"' in svg
        assert 'data-style-contract="helm-openbridge-navigation-v1"' in svg
        assert 'data-source-art="user-provided-BNKSTK"' in svg
        assert 'data-shape-family="beacon-bcnstk-bank-stake-template"' in svg
        assert "var(--" in svg
        assert '<rect x="29.5" y="10" width="5" height="39" rx="1.1"' in svg
        assert '<rect x="30.5" y="49" width="3" height="4" rx="0.6"' in svg
        assert '<rect x="24" y="46" width="16" height="3" rx="1"' in svg
        assert 'data-hole-role="s101-center-cutout"' not in svg
        assert 'data-hole-role="s101-tiny-stake-cutout"' in svg
        assert '<circle data-hole-role="s101-tiny-stake-cutout" cx="32" cy="46" r="2.2" fill="var(--white)"/>' in svg
        assert 'data-outline-role="outer-visible-edges"' in svg
        assert 'M30.6 10H33.4Q34.5 10 34.5 11.1V46' in svg

        for render_path in sample["renders"].values():
            assert (ROOT / render_path).exists()

    stk77 = (ROOT / "assets/svg/stake_beacon_family_template_preview/BCNSTK77.svg").read_text()
    stk79 = (ROOT / "assets/svg/stake_beacon_family_template_preview/BCNSTK79.svg").read_text()
    stk82 = (ROOT / "assets/svg/stake_beacon_family_template_preview/BCNSTK82.svg").read_text()
    assert 'data-fill-pattern="3-band-horizontal"' in stk77
    assert 'fill="var(--white)"' in stk77
    assert 'fill="var(--green)"' in stk77
    assert 'data-fill-pattern="3-band-horizontal"' in stk79
    assert 'fill="var(--red)"' in stk79
    assert 'fill="var(--green)"' in stk79
    assert 'data-fill-pattern="2-band-horizontal"' in stk82


if __name__ == "__main__":
    test_stake_beacon_family_template_preview()
    print("stake beacon family template preview: OK")
