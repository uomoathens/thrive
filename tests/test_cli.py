import pytest

from thrive import __version__
from thrive.book import FRAMEWORKS, PHASES
from thrive.cli import main


def test_info_lists_phases_and_frameworks(capsys):
    assert main(["info"]) == 0
    out = capsys.readouterr().out
    for phase in PHASES:
        assert phase in out
    for f in FRAMEWORKS:
        assert f.acronym in out


def test_cite_prints_the_book(capsys):
    main(["cite"])
    out = capsys.readouterr().out
    assert "AI for Resilient Cities" in out and "Springer" in out


def test_version(capsys):
    with pytest.raises(SystemExit):
        main(["--version"])
    assert __version__ in capsys.readouterr().out
