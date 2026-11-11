import argparse
import sys

from thrive import __version__
from thrive.book import BOOK, PHASE_NOTES, PHASES, frameworks_for


def _info() -> str:
    lines = [f"THRIVE {__version__}", "", "Companion software to the book:", f"  {BOOK.citation()}", ""]
    for phase in PHASES:
        lines.append(phase)
        found = frameworks_for(phase)
        if phase in PHASE_NOTES:
            lines.append(f"  {PHASE_NOTES[phase]}")
        for f in found:
            lines.append(f"  {f.acronym:<11} Table {f.table:<4} {f.name}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="thrive", description="THRIVE: who is protected first, and who recovers?")
    parser.add_argument("--version", action="version", version=f"thrive {__version__}")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("info", help="show the book and the frameworks each phase builds on")
    sub.add_parser("cite", help="print the citation of the book")
    args = parser.parse_args(argv)
    if args.command == "info":
        print(_info())
    elif args.command == "cite":
        print(BOOK.citation())
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
