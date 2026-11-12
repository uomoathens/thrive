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
    pa = sub.add_parser("phase-a", help="download open US data and compare flood funding with social vulnerability")
    pa.add_argument("--config", default="config/phase-a.toml")
    pa.add_argument("--out", default="results/phase-a")
    pb = sub.add_parser("phase-b", help="who was in the water of Storm Daniel: Copernicus flood extent against the 1 km population grid")
    pb.add_argument("--config", default="config/phase-b.toml")
    pb.add_argument("--out", default="results/phase-b")
    pt = sub.add_parser("thriving", help="when did the flooded land of Thessaly come back: Sentinel-2 greenness after Storm Daniel")
    pt.add_argument("--config", default="config/thriving.toml")
    pt.add_argument("--out", default="results/thriving")
    ps = sub.add_parser("site", help="update the page and the README from the latest results, or stop if a stated finding no longer holds")
    ps.add_argument("--root", default=".")
    ps.add_argument("--report", default=None)
    args = parser.parse_args(argv)
    if args.command == "info":
        print(_info())
    elif args.command == "cite":
        print(BOOK.citation())
    elif args.command == "demo":
        print(_demo())
    elif args.command == "phase-a":
        from pathlib import Path

        from thrive.data.phase_a import run

        summary = run(Path(args.config), Path(args.out))
        r = summary["r_cov_most_vs_least_vulnerable"]
        print(f"Phase A done: {summary['counties']} counties, coverage ratio {r:.2f}" if r is not None else "Phase A done: coverage ratio not defined")
    elif args.command == "phase-b":
        from pathlib import Path

        from thrive.data.phase_b import run as run_b

        summary = run_b(Path(args.config), Path(args.out))
        print(f"Phase B done: {summary['population_exposed']:,.0f} residents in flooded cells, {summary['flooded_km2']:,.0f} km2 flooded")
    elif args.command == "thriving":
        from pathlib import Path

        from thrive.data.thriving import run as run_t

        summary = run_t(Path(args.config), Path(args.out))
        print(f"Thriving done: {summary['items_used']} scenes used, direction: {summary['direction']}")
    elif args.command == "site":
        from pathlib import Path

        from thrive.site import SiteError, build

        try:
            out = build(Path(args.root))
        except SiteError as exc:
            lines = ["The page and the README were not changed, because these statements no longer match the latest results:", ""] + [f"- {p}" for p in exc.problems]
            text = "\n".join(lines)
            print(text)
            if args.report:
                Path(args.report).write_text(text + "\n", encoding="utf-8")
            return 2
        print("Updated: " + ", ".join(out["changed"]) if out["changed"] else "Page and README already match the latest results")
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
