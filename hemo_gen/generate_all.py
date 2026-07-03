"""Generate B01–B07 สำหรับผู้ป่วยทุกคนใน 05-Patients.sql"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hemo_gen.config import START_DATE, GenConfig, first_business_on_or_after, resolve_end_date
from hemo_gen.generator import run_generator
from hemo_gen.patient_loader import load_patients


@dataclass
class GenerateAllResult:
    patients: int = 0
    sessions: int = 0
    failed: list[tuple[str, str]] | None = None


def generate_all_patients(
    base: Path,
    span: str = "today",
    dry_run: bool = False,
    force_b01: bool = False,
    post_steps: bool = True,
) -> GenerateAllResult:
    patients = load_patients(base / "05-Patients.sql")
    if not patients:
        raise SystemExit("ไม่พบผู้ป่วยใน 05-Patients.sql")

    start = first_business_on_or_after(START_DATE)
    end = resolve_end_date(span, start, "Asia/Bangkok")
    result = GenerateAllResult(failed=[])

    print(f"generate-all: patients={len(patients)} span={span} ({start} .. {end}) dry_run={dry_run}")

    for i, patient in enumerate(patients, start=1):
        pid = patient.patient_id
        print(f"[{i}/{len(patients)}] {pid}\t{patient.name}")
        seed = abs(hash(pid)) % (2**31)
        cfg = GenConfig(
            base_dir=base,
            patient_id=pid,
            start_date=start,
            end_date=end,
            seed=seed,
            dry_run=dry_run,
            force_b01=force_b01,
        )
        try:
            gen = run_generator(cfg)
            result.patients += 1
            result.sessions += gen.sessions
            if not dry_run:
                print(
                    f"  sessions={gen.sessions} B03={gen.b03_rows} B04={gen.b04_rows} "
                    f"B05={gen.b05_pre}+{gen.b05_post} B06={gen.b06_rows} B07+={gen.b07_rows}"
                )
        except SystemExit as exc:
            result.failed.append((pid, str(exc)))
            print(f"  ข้าม: {exc}")
        except Exception as exc:
            result.failed.append((pid, str(exc)))
            print(f"  ผิดพลาด: {exc}")

    if dry_run or not post_steps:
        return result

    from hemo_gen.patch_b03_weights import patch_b03_weights
    from hemo_gen.rebuild_b04 import rebuild_b04
    from hemo_gen.rebuild_b05 import rebuild_b05

    print("\n--- post-steps ---")
    patched, total = patch_b03_weights(base)
    print(f"patch B03: {patched}/{total} tuples updated")
    pre, post, items = rebuild_b05(base, None)
    print(f"rebuild B05: pre={pre} post={post} items={items}")
    scanned, filled, rows = rebuild_b04(base, None, replace_all=True)
    print(f"rebuild B04-all: sessions={scanned} backfilled={filled} rows+={rows}")

    return result
