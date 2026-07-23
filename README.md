# Hogwarts Legacy — Hemodialysis Pro seed

Demo SQL seed + Python generators for local Hemodialysis Pro (tenant **Hogwarts**).

Two dialysis units:

| UnitId | Name |
|--------|------|
| `-1` | Hogwarts Hospital Wing |
| `1` | Azkaban Ward |

Staff = Hogwarts professors; patients = Order / students / Weasleys vs Death Eaters / Ministry dark-side.

## Layout

```text
seeds/a_core/      # users, patients, schedule (hand-authored)
seeds/b_sessions/  # B01–B07 dialysis history (generated; kept in git)
seeds/c_stock/     # equipment / supplies / AutoStock
hemo_gen/          # generator + interactive console
scripts/           # seed_a / seed_b / seed_c bats
docs/              # GENERATOR.md, SESSION_SPEC.md
```

## Quick start

1. Postgres in Docker (`HEMO_DB_*` — see below).
2. Open console:

```bat
console.bat
python -m hemo_gen.console
```

3. Seed DB (order **A → C → B**), or non-interactive:

```bat
python -m hemo_gen.console --run a,c,b --yes
```

4. Keep sessions fresh (through **yesterday**; today left empty for UI play):

```bat
python -m hemo_gen.console --extend --yes
```

Menu **E1** = extend all lagging patients (includes patients with no sessions yet).

## Console cheatsheet

| Command | Meaning |
|---------|---------|
| `python -m hemo_gen.console` | Interactive menu |
| `… --status` | DB table counts + freshness |
| `… --extend` | Generate B-group through yesterday |
| `… --extend --patient-id 6505315` | One patient |
| `… --extend --dry-run` | Preview only |
| `… --run a,c,b --yes` | Seed A then C then B |

## Manual bats (same order)

1. `scripts\seed_a.bat` — core  
2. `scripts\seed_c.bat` — stock  
3. `scripts\seed_b.bat` — sessions (B01→B02→B07→B03→B04→B05→B06)

Generate/update B files first if needed (`--extend` or `scripts\generate_all.bat`).

## DB connection

Defaults in `scripts\_db_env.bat`. Override:

```bat
copy scripts\db.env.bat.example scripts\db.env.bat
```

| Variable | Default |
|----------|---------|
| `HEMO_DB_CONTAINER` | `db` |
| `HEMO_DB_USER` | `postgres` |
| `HEMO_DB_NAME` | `hemopro-local` |
| `PGPASSWORD` | set in env / `db.env.bat` |

## Checkpoint (git tag)

Prefer annotated tags over `*-backup/` folders:

```bat
git tag -a seed-YYYY-MM-DD -m "Hogwarts A/B/C + state checkpoint"
git checkout seed-2026-07-23 -- seeds/ .hemo_gen_state.json
```

Then re-seed A → C → B.

## More detail

- Generator: [docs/GENERATOR.md](docs/GENERATOR.md)
- Session model: [docs/SESSION_SPEC.md](docs/SESSION_SPEC.md)
