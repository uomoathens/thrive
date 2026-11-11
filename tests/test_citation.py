import tomllib

import yaml

import thrive
from thrive.book import BOOK


def test_versions_agree(root):
    cff = yaml.safe_load((root / "CITATION.cff").read_text(encoding="utf-8"))
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert cff["version"] == project["version"] == thrive.__version__


def test_citation_points_to_the_book(root):
    cff = yaml.safe_load((root / "CITATION.cff").read_text(encoding="utf-8"))
    book = cff["preferred-citation"]
    assert book["type"] == "book"
    assert book["url"] == BOOK.url
    assert book["isbn"] == BOOK.isbn_hardcover
    assert book["year"] == BOOK.year
    assert BOOK.title in book["title"] and BOOK.subtitle in book["title"]
