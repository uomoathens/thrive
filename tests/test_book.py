import re

import pytest

from thrive.book import BOOK, FRAMEWORKS, PHASES, frameworks_for


def isbn13_ok(isbn: str) -> bool:
    digits = [int(c) for c in isbn if c.isdigit()]
    if len(digits) != 13:
        return False
    total = sum(d * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits[:12]))
    return (10 - total % 10) % 10 == digits[12]


def test_isbns_are_valid():
    assert isbn13_ok(BOOK.isbn_hardcover)
    assert isbn13_ok(BOOK.isbn_ebook)


def test_book_url_matches_hardcover_isbn():
    assert BOOK.url.endswith(BOOK.isbn_hardcover.replace("-", ""))


def test_every_framework_has_a_known_phase():
    assert {f.phase for f in FRAMEWORKS} <= set(PHASES)


def test_framework_tables_match_their_chapters():
    for f in FRAMEWORKS:
        assert f.table.split(".")[0] == str(f.chapter)


def test_frameworks_for_rejects_unknown_phase():
    with pytest.raises(ValueError):
        frameworks_for("Guessing")


def test_readme_lists_every_framework_with_its_table(root):
    readme = (root / "README.md").read_text(encoding="utf-8")
    for f in FRAMEWORKS:
        assert re.search(rf"{re.escape(f.acronym)} \(Table {re.escape(f.table)}\)", readme), f.acronym
