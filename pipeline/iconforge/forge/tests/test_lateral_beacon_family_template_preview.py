from __future__ import annotations

from pathlib import Path

from forge import lateral_beacon_family_template_preview as preview


ROOT = Path(__file__).resolve().parents[2]


def test_lateral_beacon_family_template_preview() -> None:
    result = preview.build(render_outputs=True)

    assert result["status"] == "lateral_beacon_family_template_preview_written"
    assert result["summary"]["sample_count"] == 6
    assert result["summary"]["render_count"] == 18
    assert {sample["asset"] for sample in result["samples"]} == {
        "BCNLAT15",
        "BCNLAT16",
        "BCNLAT21",
        "BCNLAT22",
        "BCNLAT23",
        "BCNLAT50",
    }

    contact_sheet = ROOT / result["outputs"]["contact_sheet"]
    assert contact_sheet.exists()

    for sample in result["samples"]:
        svg = (ROOT / sample["svg"]).read_text()
        assert 'data-origin="generated-owned-artwork"' in svg
        assert 'data-style-contract="helm-openbridge-navigation-v1"' in svg
        assert 'data-source-art="user-provided-BCNLAT"' in svg
        assert 'data-shape-family="beacon-bcnlat-template"' in svg
        assert "#007fff" not in svg
        assert "#003a73" not in svg
        assert "var(--" in svg
        assert '<rect x="23" y="9" width="18" height="46" rx="2.2"' in svg
        assert '<circle cx="32" cy="32" r="2.7" fill="var(--ink)"' in svg
        assert 'data-outline-role="outer-visible-edges"' in svg
        assert 'M25.2 9H38.8Q41 9 41 11.2V52.8' in svg

        for render_path in sample["renders"].values():
            assert (ROOT / render_path).exists()

    lat15 = (ROOT / "assets/svg/lateral_beacon_family_template_preview/BCNLAT15.svg").read_text()
    lat16 = (ROOT / "assets/svg/lateral_beacon_family_template_preview/BCNLAT16.svg").read_text()
    lat23 = (ROOT / "assets/svg/lateral_beacon_family_template_preview/BCNLAT23.svg").read_text()
    assert 'data-fill-pattern="3-band-horizontal"' in lat15
    assert 'fill="var(--red)"' in lat15
    assert 'fill="var(--green)"' in lat15
    assert 'data-fill-pattern="3-band-horizontal"' in lat16
    assert 'fill="var(--green)"' in lat16
    assert 'fill="var(--red)"' in lat16
    assert 'data-fill-pattern="3-band-horizontal"' in lat23
    assert 'fill="var(--black)"' in lat23


if __name__ == "__main__":
    test_lateral_beacon_family_template_preview()
    print("lateral beacon family template preview: OK")
