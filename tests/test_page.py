def test_page_uses_the_same_example_curves(root):
    page = (root / "docs/index.html").read_text(encoding="utf-8")
    assert "0.92*(1-Math.exp(-t/4))+0.08*(1-Math.exp(-t/60))" in page
    assert "1/(1+Math.exp(-(t-20)/3))" in page


def test_page_uses_the_same_levees(root):
    page = (root / "docs/index.html").read_text(encoding="utf-8")
    assert "(50*210+100*90)/150" in page
    assert "10.5*Math.pow(yb/210,e)" in page and "9*Math.pow(yb/90,e)" in page


def test_page_holds_the_phase_c_results(root):
    import json

    page = (root / "docs/index.html").read_text(encoding="utf-8")
    assert 'id="wildfires"' in page and 'href="#wildfires"' in page
    i = page.index("var PC=") + len("var PC=")
    pc, _ = json.JSONDecoder().raw_decode(page[i:])
    s = json.loads((root / "results/phase-c/summary.json").read_text(encoding="utf-8"))
    assert [x["k"] for x in pc["sectors"]] == [r["sector"] for r in s["results"] if r["measure"] == "growth_real"]
    for x in pc["sectors"]:
        assert all(abs(a - b) < 0.005 for a, b in zip(x["thrive"], x["pbo"]))
    assert len(pc["nights"]) == len(s["tourism"]["variants"])
    assert all(n["cum"] < 0 for n in pc["nights"])
    assert set(pc["rhodes"]) == {"2023", "2024", "2025"}
