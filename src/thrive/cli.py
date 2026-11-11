import argparse
import sys

from thrive import __version__
from thrive.allocate import allocate, project_values
from thrive.audit import certify
from thrive.book import BOOK, PHASE_NOTES, PHASES, frameworks_for
from thrive.examples import (
    IDENTITY_CHANGES,
    LEVEE_COST,
    NEED_CHANGES,
    biased_decide,
    fair_decide,
    liscow_levees,
    need_blind_decide,
    recovery_example,
    triage_cases,
)
from thrive.recovery import robust_recovery
from thrive.weights import crossover


def _info() -> str:
    lines = [f"THRIVE {__version__}", "", "Companion software to the book:", f"  {BOOK.citation()}", ""]
    for phase in PHASES:
        lines.append(phase)
        if phase in PHASE_NOTES:
            lines.append(f"  {PHASE_NOTES[phase]}")
        for f in frameworks_for(phase):
            lines.append(f"  {f.acronym:<11} Table {f.table:<4} {f.name}")
    return "\n".join(lines)


def _demo() -> str:
    out = ["Examples only. None of these numbers is a THRIVE result.", "", "1. Which levee gets built? (example of Z. Liscow, NBER 2023)"]
    levees = liscow_levees()
    for eta in (0.0, 0.5, 1.0, 2.0):
        a, b = project_values(levees, eta)
        plan = allocate(levees, LEVEE_COST, eta)
        out.append(f"   eta {eta:.1f}: A ${a / 1e6:.1f}m, B ${b / 1e6:.1f}m, funded: {', '.join(plan.selected)}")
    flip = crossover(lambda e: project_values(levees, e)[0] - project_values(levees, e)[1])
    passes = crossover(lambda e: project_values(levees, e)[1] - LEVEE_COST)
    out.append(f"   B overtakes A at eta {flip:.2f} and passes the $10m cost at eta {passes:.2f}")
    out += ["", "2. Who recovered first? (made-up curves)"]
    groups = recovery_example()
    finding = robust_recovery(groups, {g: 1.0 for g in groups}, [0.90, 0.97])
    for a, days, order in zip(finding.alphas, finding.days, finding.orders):
        out.append(f"   recovered = {a:.0%}: " + ", ".join(f"{g} day {d}" for g, d in days.items()) + f"; first: {order[0]}")
    out.append(f"   same order under every threshold: {'yes' if finding.stable else 'no, so no finding is kept'}")
    out += ["", "3. Fairness check on three made-up decision rules"]
    cases = triage_cases()
    for label, rule in (("fair rule", fair_decide), ("rule that marks down foreign names", biased_decide), ("rule that ignores need", need_blind_decide)):
        cert = certify(cases, rule, IDENTITY_CHANGES, NEED_CHANGES)
        why = "" if cert.passed else " (" + ", ".join(c.name for c in cert.failures()) + ")"
        out.append(f"   {label}: {'PASS' if cert.passed else 'FAIL'}{why}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="thrive", description="THRIVE: who is protected first, and who recovers?")
    parser.add_argument("--version", action="version", version=f"thrive {__version__}")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("info", help="show the book and the frameworks each phase builds on")
    sub.add_parser("cite", help="print the citation of the book")
    sub.add_parser("demo", help="run the worked examples of the README")
    args = parser.parse_args(argv)
    if args.command == "info":
        print(_info())
    elif args.command == "cite":
        print(BOOK.citation())
    elif args.command == "demo":
        print(_demo())
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
