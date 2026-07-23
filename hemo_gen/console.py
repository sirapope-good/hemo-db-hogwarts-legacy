"""Interactive Hogwarts seed console (stdlib only).

Usage:
  python -m hemo_gen.console
  python -m hemo_gen.console --status
  python -m hemo_gen.console --run a,c,b --yes
  python -m hemo_gen.console --extend
  python -m hemo_gen.console --extend --patient-id 6505315 --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hemo_gen.config import START_DATE, GenConfig, first_business_on_or_after, repo_root
from hemo_gen.freshness import FreshnessReport, collect_freshness
from hemo_gen.seed_ops import (
    DbConfig,
    DbStatus,
    SqlResult,
    build_warnings,
    collect_status,
    normalize_run_order,
    run_groups,
)


def _c(enabled: bool, code: str, text: str) -> str:
    if not enabled:
        return text
    return f"\033[{code}m{text}\033[0m"


def _use_color() -> bool:
    return sys.stdout.isatty() and os_name_supports_color()


def os_name_supports_color() -> bool:
    if sys.platform == "win32":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
            return True
        except Exception:
            return False
    return True


class Style:
    def __init__(self) -> None:
        self.on = _use_color()

    def bold(self, t: str) -> str:
        return _c(self.on, "1", t)

    def green(self, t: str) -> str:
        return _c(self.on, "92", t)

    def red(self, t: str) -> str:
        return _c(self.on, "91", t)

    def yellow(self, t: str) -> str:
        return _c(self.on, "93", t)

    def cyan(self, t: str) -> str:
        return _c(self.on, "96", t)

    def dim(self, t: str) -> str:
        return _c(self.on, "2", t)


def progress_bar(done: int, total: int, width: int = 28) -> str:
    if total <= 0:
        return "[" + (" " * width) + "]"
    filled = int(width * done / total)
    return "[" + ("#" * filled) + ("-" * (width - filled)) + f"] {done}/{total}"


def print_header(style: Style, cfg: DbConfig) -> None:
    print()
    print(style.bold("=" * 60))
    print(style.bold("  Hogwarts Seed Console"))
    print(style.bold("=" * 60))
    print(
        f"  DB  container={style.cyan(cfg.container)}  "
        f"user={cfg.user}  database={cfg.database}"
    )
    print(f"  root={style.dim(str(repo_root()))}")
    print()


def print_freshness(style: Style, report: FreshnessReport) -> None:
    print(style.bold("  Session data freshness"))
    print(
        f"    clinic today={report.clinic_today}  "
        f"generate through={style.cyan(str(report.playable_end))} "
        f"{style.dim('(yesterday — leave today free)')}"
    )
    latest = report.latest_any
    if latest is None:
        print(style.yellow("    ! No B03 / state session dates yet — need generate."))
    else:
        lag_latest = max(0, (report.playable_end - latest).days)
        if lag_latest <= 0:
            print(style.green(f"    Latest session data: {latest} (up to date vs playable end)"))
        else:
            print(
                style.yellow(
                    f"    Latest session data: {latest}  —  {lag_latest} day(s) behind playable end"
                )
            )
        lagging_n = len(report.lagging)
        if lagging_n:
            worst = report.max_days_behind or lag_latest
            extra = f", worst patient {worst}d behind" if worst and worst > lag_latest else ""
            none_n = len([p for p in report.patients if p.last_session_date is None])
            if none_n:
                extra += f", {none_n} with no sessions yet"
            print(style.dim(f"    Patients needing extend: {lagging_n}/{len(report.patients)}{extra}"))
    print()


def print_status(style: Style, status: DbStatus) -> None:
    if not status.docker_ok or not status.container_running or not status.psql_ok:
        print(style.red(f"  DB status: FAIL — {status.message}"))
        print()
        return

    print(style.green("  DB status: OK (docker + psql)"))
    print()
    for key in ("a", "b", "c"):
        g = status.groups[key]
        flag = style.yellow("POPULATED") if g.populated else style.dim("empty/missing")
        print(f"  {style.bold(g.label)}  [{flag}]")
        parts = []
        for t in g.tables:
            if t.count is None:
                parts.append(f"{t.name}=?")
            else:
                parts.append(f"{t.name}={t.count}")
        print("    " + style.dim("  ".join(parts)))
    print()


def print_selection(style: Style, selected: dict[str, bool]) -> None:
    print(style.bold("  Selected seeds (execution order A → C → B):"))
    for key, label in (("a", "A — Core"), ("b", "B — Sessions"), ("c", "C — Stock")):
        mark = style.green("[x]") if selected[key] else style.dim("[ ]")
        print(f"    {mark} {label}")
    print()


def run_extend(
    style: Style,
    *,
    patient_id: str | None = None,
    dry_run: bool = False,
    force_meds: bool = False,
    assume_yes: bool = False,
) -> int:
    """Extend B-group sessions through yesterday (not including today)."""
    root = repo_root()
    report = collect_freshness(root)
    print_freshness(style, report)

    end = report.playable_end
    start = first_business_on_or_after(START_DATE)
    print(
        style.bold(
            f"  Extend target: {start} .. {end}  "
            f"(span=today → through yesterday; today={report.clinic_today} left free)"
        )
    )

    if patient_id:
        targets = [p for p in report.patients if p.patient_id == patient_id]
        if not targets:
            print(style.red(f"  Patient not found: {patient_id}"))
            return 1
    else:
        targets = report.lagging
        if not targets:
            print(style.green("  Nothing to do — all patients already through playable end."))
            return 0
    print(f"  Will process {len(targets)} patient(s)" + (" [dry-run]" if dry_run else ""))
    for p in targets[:8]:
        last = p.last_session_date.isoformat() if p.last_session_date else "none"
        lag = "?" if p.days_behind is None else str(p.days_behind)
        print(style.dim(f"    {p.patient_id}\t{p.name}\tlast={last}\tbehind={lag}d"))
    if len(targets) > 8:
        print(style.dim(f"    ... +{len(targets) - 8} more"))

    if not assume_yes and not dry_run:
        ans = input("  Proceed with generate? [y/N] ").strip().lower()
        if ans not in ("y", "yes"):
            print("  Cancelled.")
            return 0

    from hemo_gen.generator import run_generator

    ok = 0
    sessions = 0
    failed: list[tuple[str, str]] = []
    for i, p in enumerate(targets, start=1):
        print(f"  [{i}/{len(targets)}] {p.patient_id}\t{p.name}")
        seed = abs(hash(p.patient_id)) % (2**31)
        cfg = GenConfig(
            base_dir=root,
            patient_id=p.patient_id,
            start_date=start,
            end_date=end,
            seed=seed,
            dry_run=dry_run,
            force_b01=False,
            force_meds=force_meds,
        )
        try:
            gen = run_generator(cfg)
            ok += 1
            sessions += gen.sessions
            if not dry_run and gen.sessions:
                print(
                    f"    +sessions={gen.sessions} B02+={gen.b02_rows} B07+={gen.b07_rows} "
                    f"B03+={gen.b03_rows} B06+={gen.b06_rows}"
                )
        except SystemExit as exc:
            failed.append((p.patient_id, str(exc)))
            print(style.red(f"    skip: {exc}"))
        except Exception as exc:
            failed.append((p.patient_id, str(exc)))
            print(style.red(f"    error: {exc}"))

    if dry_run:
        print(style.cyan(f"  dry-run done: patients={ok} (no files written)"))
        return 0

    if not failed:
        from hemo_gen.patch_b03_weights import patch_b03_weights
        from hemo_gen.rebuild_b04 import rebuild_b04
        from hemo_gen.rebuild_b05 import rebuild_b05

        print("\n  --- post-steps ---")
        patched, total = patch_b03_weights(root)
        print(f"  patch B03: {patched}/{total}")
        pre, post, items = rebuild_b05(root, None)
        print(f"  rebuild B05: pre={pre} post={post} items={items}")
        scanned, filled, rows = rebuild_b04(root, None, replace_all=True)
        print(f"  rebuild B04-all: sessions={scanned} backfilled={filled} rows+={rows}")

    print()
    print(style.green(f"  RESULT: ok={ok} sessions+={sessions} failed={len(failed)}"))
    return 1 if failed else 0


def extend_submenu(style: Style) -> None:
    while True:
        report = collect_freshness()
        print()
        print(style.bold("  --- Extend B-group sessions ---"))
        print_freshness(style, report)
        print("    E1) Extend ALL lagging patients (through yesterday)")
        print("    E2) Extend ONE patient (enter PatientId)")
        print("    E3) Dry-run all lagging")
        print("    E4) List lagging patients")
        print("    B)  Back")
        print()
        choice = input("  extend> ").strip().lower()
        if choice in ("b", "back", ""):
            return
        if choice == "e1":
            run_extend(style, assume_yes=False)
            input("  Press Enter...")
        elif choice == "e2":
            pid = input("  PatientId: ").strip()
            if pid:
                run_extend(style, patient_id=pid, assume_yes=False)
            input("  Press Enter...")
        elif choice == "e3":
            run_extend(style, dry_run=True, assume_yes=True)
            input("  Press Enter...")
        elif choice == "e4":
            lagging = report.lagging
            if not lagging:
                print(style.green("  None lagging."))
            else:
                for p in lagging:
                    last = p.last_session_date.isoformat() if p.last_session_date else "none"
                    lag = "?" if p.days_behind is None else f"{p.days_behind}d"
                    print(f"    {p.patient_id}\t{p.name}\tlast={last}\tbehind={lag}")
            input("  Press Enter...")
        else:
            print(style.yellow("  Unknown choice."))


def interactive_loop() -> int:
    style = Style()
    cfg = DbConfig.load()
    selected = {"a": True, "b": True, "c": True}

    while True:
        print_header(style, cfg)
        report = collect_freshness()
        print_freshness(style, report)
        status = collect_status(cfg)
        print_status(style, status)
        print_selection(style, selected)

        print("  Menu:")
        print("    1) Toggle A   2) Toggle B   3) Toggle C")
        print("    4) Refresh status")
        print("    5) Execute selected seeds (SQL into DB)")
        print("    6) Select A only / 7) Select all / 8) Select none")
        print("    9) Extend B-group sessions (generate through yesterday)")
        print("    Q) Quit")
        print()
        choice = input("  > ").strip().lower()

        if choice in ("q", "quit", "exit"):
            print("Bye.")
            return 0
        if choice == "1":
            selected["a"] = not selected["a"]
        elif choice == "2":
            selected["b"] = not selected["b"]
        elif choice == "3":
            selected["c"] = not selected["c"]
        elif choice == "4":
            continue
        elif choice == "6":
            selected = {"a": True, "b": False, "c": False}
        elif choice == "7":
            selected = {"a": True, "b": True, "c": True}
        elif choice == "8":
            selected = {"a": False, "b": False, "c": False}
        elif choice == "9":
            extend_submenu(style)
        elif choice == "5":
            groups = [k for k, on in selected.items() if on]
            if not groups:
                print(style.yellow("  Nothing selected."))
                input("  Press Enter...")
                continue
            code = execute_with_confirm(style, cfg, status, groups)
            input("  Press Enter to return to menu...")
            if code != 0:
                continue
        else:
            print(style.yellow("  Unknown choice."))
            input("  Press Enter...")


def execute_with_confirm(
    style: Style,
    cfg: DbConfig,
    status: DbStatus,
    groups: list[str],
    *,
    assume_yes: bool = False,
) -> int:
    try:
        order = normalize_run_order(groups)
    except ValueError as exc:
        print(style.red(f"  {exc}"))
        return 1

    print()
    print(style.bold(f"  Will run: {' → '.join(g.upper() for g in order)}"))
    warnings = build_warnings(status, order)
    for w in warnings:
        print(style.yellow(f"  ! {w}"))

    if not status.psql_ok:
        print(style.red("  Abort: database not reachable."))
        return 1

    if not assume_yes:
        ans = input("  Proceed? [y/N] ").strip().lower()
        if ans not in ("y", "yes"):
            print("  Cancelled.")
            return 0

    print()
    root = repo_root()

    def on_start(i: int, total: int, path: Path) -> None:
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path
        print(f"  {progress_bar(i - 1, total)}  {rel} ...", end="", flush=True)

    def on_result(i: int, total: int, result: SqlResult) -> None:
        if result.ok:
            print(f"\r  {progress_bar(i, total)}  {result.path.name}  {style.green('PASS')}          ")
        else:
            print(f"\r  {progress_bar(i, total)}  {result.path.name}  {style.red('FAIL')}          ")
            detail = result.detail.strip()
            if detail:
                for line in detail.splitlines()[:12]:
                    print(style.red(f"      {line}"))

    passed, failed = run_groups(order, cfg=cfg, root=root, on_start=on_start, on_result=on_result)
    print()
    if failed == 0:
        print(style.green(f"  RESULT: SUCCESS  passed={passed}"))
        return 0
    print(style.red(f"  RESULT: FAILED  passed={passed} failed={failed}"))
    return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Hogwarts interactive seed console (A/B/C + extend sessions + DB status)"
    )
    p.add_argument("--status", action="store_true", help="Print DB + freshness status and exit")
    p.add_argument("--run", metavar="GROUPS", help="Non-interactive seed run, e.g. a,c,b")
    p.add_argument("--extend", action="store_true", help="Extend B-group through yesterday")
    p.add_argument("--patient-id", help="With --extend: one patient only")
    p.add_argument("--dry-run", action="store_true", help="With --extend: summarize only")
    p.add_argument("--force-meds", action="store_true", help="With --extend: replan medicines")
    p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    return p


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass

    args = build_parser().parse_args(argv)
    style = Style()
    cfg = DbConfig.load()

    if args.status:
        print_header(style, cfg)
        print_freshness(style, collect_freshness())
        status = collect_status(cfg)
        print_status(style, status)
        return 0 if status.psql_ok else 1

    if args.extend:
        print_header(style, cfg)
        return run_extend(
            style,
            patient_id=args.patient_id,
            dry_run=args.dry_run,
            force_meds=args.force_meds,
            assume_yes=args.yes or args.dry_run,
        )

    if args.run:
        groups = [g.strip() for g in args.run.replace(" ", "").split(",") if g.strip()]
        print_header(style, cfg)
        print_freshness(style, collect_freshness())
        status = collect_status(cfg)
        print_status(style, status)
        return execute_with_confirm(style, cfg, status, groups, assume_yes=args.yes)

    return interactive_loop()


if __name__ == "__main__":
    raise SystemExit(main())
