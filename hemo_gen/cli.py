from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hemo_gen.config import START_DATE, GenConfig, first_business_on_or_after, resolve_end_date
from hemo_gen.generator import run_generator
from hemo_gen.patient_loader import load_patients


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="สร้างข้อมูลฟอกไตครบชุด (B01–B07) ทีละ 1 ผู้ป่วย — Hogwarts seed"
    )
    p.add_argument("--patient-id", help="PatientId จาก 05-Patients.sql")
    p.add_argument("--list-patients", action="store_true", help="แสดงรายชื่อผู้ป่วย")
    p.add_argument("--span", default="today", choices=("2m", "4m", "6m", "today"), help="ช่วงข้อมูลจาก 2025-08-01")
    p.add_argument("--seed", type=int, default=None, help="seed สำหรับ random แบบ deterministic")
    p.add_argument("--dry-run", action="store_true", help="สรุปจำนวนแถว ไม่เขียนไฟล์")
    p.add_argument("--force-b01", action="store_true", help="เขียน B01 แม้มี patient ในไฟล์แล้ว")
    p.add_argument(
        "--patch-b03-weights",
        action="store_true",
        help="แก้ B03 seed ที่ UFGoal=0 / Post weight ว่าง",
    )
    p.add_argument(
        "--rebuild-b04",
        action="store_true",
        help="เติม B04 สำหรับ hemosheet ใน B03 ที่ยังไม่มี DialysisRecord",
    )
    p.add_argument(
        "--rebuild-b04-all",
        action="store_true",
        help="ลบ B04 แล้วสร้างใหม่ทุกรอบ (อัปเดต NSS/Glucose ฯลฯ)",
    )
    p.add_argument(
        "--rebuild-b05",
        action="store_true",
        help="สร้าง B05 ใหม่จาก B03 ทั้งไฟล์ (แก้กรณี Pre/Post vitals หาย)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass

    args = build_parser().parse_args(argv)
    base = Path.cwd()

    if args.list_patients:
        for p in load_patients(base / "05-Patients.sql"):
            print(f"{p.patient_id}\t{p.name}")
        return 0

    if args.patch_b03_weights:
        from hemo_gen.patch_b03_weights import patch_b03_weights

        patched, total = patch_b03_weights(base)
        print(f"patch B03 weights: {patched}/{total} tuples updated")
        return 0

    if args.rebuild_b04 or args.rebuild_b04_all:
        from hemo_gen.rebuild_b04 import rebuild_b04

        scanned, filled, rows = rebuild_b04(
            base,
            args.patient_id,
            replace_all=args.rebuild_b04_all,
        )
        print(f"rebuild B04: sessions={scanned} backfilled={filled} rows+={rows}")
        return 0

    if args.rebuild_b05:
        from hemo_gen.rebuild_b05 import rebuild_b05

        pre, post, items = rebuild_b05(base, args.patient_id)
        print(f"rebuild B05: pre={pre} post={post} items={items}")
        return 0

    if not args.patient_id:
        print("ต้องระบุ --patient-id หรือใช้ --list-patients")
        return 1

    start = first_business_on_or_after(START_DATE)
    end = resolve_end_date(args.span, start, "Asia/Bangkok")
    seed = args.seed if args.seed is not None else abs(hash(args.patient_id)) % (2**31)

    cfg = GenConfig(
        base_dir=base,
        patient_id=args.patient_id,
        start_date=start,
        end_date=end,
        seed=seed,
        dry_run=args.dry_run,
        force_b01=args.force_b01,
    )
    result = run_generator(cfg)
    if not args.dry_run:
        print(
            f"เสร็จ: patient={result.patient_id} sessions={result.sessions} "
            f"B02+={result.b02_rows} B03={result.b03_rows} B04={result.b04_rows} "
            f"B05={result.b05_pre}+{result.b05_post} items={result.b05_items} "
            f"B06={result.b06_rows} B07+={result.b07_rows}"
        )
    return 0
