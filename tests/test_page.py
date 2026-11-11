def test_page_uses_the_same_example_curves(root):
    page = (root / "docs/index.html").read_text(encoding="utf-8")
    assert "0.92*(1-Math.exp(-t/4))+0.08*(1-Math.exp(-t/60))" in page
    assert "1/(1+Math.exp(-(t-20)/3))" in page


def test_page_uses_the_same_levees(root):
    page = (root / "docs/index.html").read_text(encoding="utf-8")
    assert "(50*210+100*90)/150" in page
    assert "10.5*Math.pow(yb/210,e)" in page and "9*Math.pow(yb/90,e)" in page
