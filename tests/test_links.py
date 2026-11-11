import re

from thrive.book import BOOK

FILES = ["README.md", "CITATION.cff", "docs/index.html"]


def test_book_link_present_everywhere(root):
    for name in FILES:
        assert BOOK.url in (root / name).read_text(encoding="utf-8"), name


def test_no_unregistered_book_doi(root):
    for name in FILES:
        assert "10.1007/978-3-032" not in (root / name).read_text(encoding="utf-8"), name


def test_readme_figures_exist(root):
    readme = (root / "README.md").read_text(encoding="utf-8")
    paths = set(re.findall(r'(docs/figures/[\w-]+\.svg)', readme))
    assert paths
    for p in paths:
        assert (root / p).is_file(), p


def test_social_preview_exists(root):
    page = (root / "docs/index.html").read_text(encoding="utf-8")
    assert "og.png" in page
    assert (root / "docs/og.png").is_file()
