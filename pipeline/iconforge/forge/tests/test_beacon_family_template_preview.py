from __future__ import annotations

from pathlib import Path

from forge import beacon_family_template_preview as preview


ROOT = Path(__file__).resolve().parents[2]


def test_beacon_family_template_preview() -> None:
    result = preview.build(render_outputs=True)

    assert result["status"] == "beacon_family_template_preview_written"
    assert result["summary"]["sample_count"] == 14
    assert result["summary"]["render_count"] == 42
    assert {sample["asset"] for sample in result["samples"]} == {
        "BCNGEN01",
        "BCNGEN03",
        "BCNGEN05",
        "BCNGEN60",
        "BCNGEN61",
        "BCNGEN64",
        "BCNGEN65",
        "BCNGEN68",
        "BCNGEN69",
        "BCNGEN70",
        "BCNGEN71",
        "BCNGEN76",
        "BCNGEN79",
        "BCNGEN80",
    }

    contact_sheet = ROOT / result["outputs"]["contact_sheet"]
    assert contact_sheet.exists()

    for sample in result["samples"]:
        svg = (ROOT / sample["svg"]).read_text()
        assert 'data-origin="generated-owned-artwork"' in svg
        assert 'data-style-contract="helm-openbridge-navigation-v1"' in svg
        assert 'data-source-art="user-provided-BCNGEN6"' in svg
        assert 'data-shape-family="beacon-bcngen6-template"' in svg
        assert "#007fff" not in svg
        assert "#003a73" not in svg
        assert "var(--" in svg
        assert '<rect x="25" y="12" width="14" height="34" rx="2"' in svg
        assert '<rect x="18" y="46" width="28" height="4" rx="1.4"' in svg
        assert '<circle cx="32" cy="46" r="7"' in svg
        assert 'data-hole-role="s101-center-cutout"' in svg
        assert '<circle data-hole-role="s101-center-cutout" cx="32" cy="46" r="5.6" fill="var(--white)"/>' in svg
        assert 'data-outline-role="outer-visible-edges"' in svg
        assert 'M27 12H37Q39 12 39 14V46' in svg
        outline = svg.split('data-outline-role="outer-visible-edges"', 1)[1]
        assert "<circle" not in outline
        assert outline.count("<path") == 1

        for render_path in sample["renders"].values():
            assert (ROOT / render_path).exists()

    split_68 = (ROOT / "assets/svg/beacon_family_template_preview/BCNGEN68.svg").read_text()
    split_69 = (ROOT / "assets/svg/beacon_family_template_preview/BCNGEN69.svg").read_text()
    assert 'data-fill-pattern="2-band-horizontal"' in split_68
    assert 'x="25" y="12" width="14" height="17" rx="2" fill="var(--black)"' in split_68
    assert 'x="25" y="29" width="14" height="17" fill="var(--yellow)"' in split_68
    assert 'x="18" y="46" width="28" height="4" rx="1.4" fill="var(--yellow)"' in split_68
    assert 'data-fill-pattern="2-band-horizontal"' in split_69
    assert 'x="25" y="12" width="14" height="17" rx="2" fill="var(--yellow)"' in split_69
    assert 'x="25" y="29" width="14" height="17" fill="var(--black)"' in split_69
    assert 'x="18" y="46" width="28" height="4" rx="1.4" fill="var(--black)"' in split_69

    split_64 = (ROOT / "assets/svg/beacon_family_template_preview/BCNGEN64.svg").read_text()
    split_70 = (ROOT / "assets/svg/beacon_family_template_preview/BCNGEN70.svg").read_text()
    assert 'data-fill-pattern="4-band-horizontal"' in split_64
    assert 'fill="var(--red)"' in split_64
    assert 'fill="var(--white)"' in split_64
    assert 'data-fill-pattern="3-band-horizontal"' in split_70
    assert 'fill="var(--black)"' in split_70
    assert 'fill="var(--yellow)"' in split_70


if __name__ == "__main__":
    test_beacon_family_template_preview()
    print("beacon family template preview: OK")
