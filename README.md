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

## Seed console (recommended)

Interactive CLI — no need to `cd` and run bats by hand:

```bat
console.bat
python -m hemo_gen.console
```

| Command | Meaning |
|---------|---------|
| `python -m hemo_gen.console` | Menu: seed A/B/C, freshness, extend sessions, execute |
| `python -m hemo_gen.console --status` | DB counts + how many days session data is behind |
| `python -m hemo_gen.console --extend` | Generate B-group through **yesterday** (leave today free) |
| `python -m hemo_gen.console --extend --patient-id 6505315` | Extend one patient |
| `python -m hemo_gen.console --extend --dry-run` | Preview only |
| `python -m hemo_gen.console --run a,c,b --yes` | Non-interactive SQL seed |

**Freshness / extend:** console shows latest dialysis date and days behind the playable end (= yesterday). Menu `9` runs generate for lagging patients. Span `today` never writes sessions on the calendar today so the UI still has room to play.

## Seed order (manual bats)

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

REM Rebuild medicine prescriptions (multi-med from medicines.csv, ExpireDate=NULL)
python generate_patient_dialysis.py --rebuild-b07
```

Writes under `seeds/b_sessions/` and updates `.hemo_gen_state.json` at repo root.

**B07 medicines:** catalog in `hemo_gen/data/medicine_catalog.json` + `medicines.csv` (synced from backend seed). Each patient gets ESA ± IV iron ± heparin ± oral CKD meds. `ExpireDate` is always NULL on create (only set when superseding a regimen line in the app). AdministerDate aligns with the patient's dialysis start.

**Keep B03 current (with B02+B07):** use console menu `9` or:

```bat
python -m hemo_gen.console --extend
python generate_patient_dialysis.py --generate-all --span today
```

(`span=today` = generate through **yesterday** only.) Legacy: `python scripts/legacy/generate_b03_incremental.py` (delegates to hemo_gen; `--clone-only` for old B03 clone).

Details: [docs/GENERATOR.md](docs/GENERATOR.md) · Session model: [docs/SESSION_SPEC.md](docs/SESSION_SPEC.md)

## Checkpoint restore

```bat
git checkout seed-2026-07-23 -- seeds/ .hemo_gen_state.json
```

Then run `scripts\seed_a.bat` → `seed_c` → `seed_b`.

## Legacy

`scripts/legacy/generate_b03_incremental.py` — B03-only gap-fill (prefer `hemo_gen` for full B01–B07).
