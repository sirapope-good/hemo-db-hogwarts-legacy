# Hogwarts Legacy — SQL seed & generators

Demo / local seed data for Hemodialysis Pro (tenant Hogwarts).

## Layout

```text
seeds/
  a_core/       # hand-authored core (00–11)
  b_sessions/   # generated B01–B07 (keep in git for ready-to-seed)
  c_stock/      # equipments / medical supplies / AutoStock
hemo_gen/       # Python generator package
scripts/        # seed_a / seed_b / seed_c / generate_all (+ legacy/)
docs/           # SESSION_SPEC.md, GENERATOR.md
data/           # source spreadsheets / notes
```

## Checkpoints (git tag)

อย่าสร้างโฟลเดอร์ `*-backup/` ใน repo อีก — ใช้ annotated tag:

```bat
git tag -a seed-YYYY-MM-DD -m "Hogwarts A/B/C + state checkpoint"
```

กู้คืน seed เข้า branch ปัจจุบัน:

```bat
git checkout seed-2026-07-23 -- seeds/ .hemo_gen_state.json
```

ดู tag ที่มี: `git tag -l "seed-*"`

Checkpoint ปัจจุบันของชุดที่ rearrange แล้ว: **`seed-2026-07-23`**

## Seed order

1. `scripts\seed_a.bat` — core users/patients/schedule  
2. Generate B-group if needed: `scripts\generate_all.bat` (or `python generate_patient_dialysis.py …`)  
3. `scripts\seed_c.bat` — stock  
4. `scripts\seed_b.bat` — B01→B02→B07→B03→B04→B05→B06  

Root wrappers (`run_*_seed.bat`, `generate_all_patients.bat`) call the same scripts.

## DB connection

Defaults are in `scripts\_db_env.bat`. Override with env vars or copy:

```bat
copy scripts\db.env.bat.example scripts\db.env.bat
```

| Variable | Default |
|----------|---------|
| `HEMO_DB_CONTAINER` | `db` |
| `HEMO_DB_USER` | `postgres` |
| `HEMO_DB_NAME` | `hemopro-local` |
| `PGPASSWORD` | `your_password_here` |

## Generator (quick)

```bat
python generate_patient_dialysis.py --list-patients
python generate_patient_dialysis.py --generate-all --span today
scripts\generate_all.bat --span 4m --dry-run
```

Writes under `seeds/b_sessions/` and updates `.hemo_gen_state.json` at repo root.

Details: [docs/GENERATOR.md](docs/GENERATOR.md) · Session model: [docs/SESSION_SPEC.md](docs/SESSION_SPEC.md)

## Checkpoint restore

```bat
git checkout seed-2026-07-23 -- seeds/ .hemo_gen_state.json
```

Then run `scripts\seed_a.bat` → `seed_c` → `seed_b`.

## Legacy

`scripts/legacy/generate_b03_incremental.py` — B03-only gap-fill (prefer `hemo_gen` for full B01–B07).
