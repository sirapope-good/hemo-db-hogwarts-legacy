"""DB connection helpers, status probes, and SQL seed execution via docker exec."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field, replace
from pathlib import Path

from hemo_gen.config import a_core_dir, b_sessions_dir, c_stock_dir, repo_root

SCHEMA = "local"

A_FILES = [
    "00-Units.sql",
    "01-Users.sql",
    "02-AspNetUserRoles.sql",
    "03-UserUnits.sql",
    "04-Incomes.sql",
    "05-Patients.sql",
    "06-Update Unit Name to Hogwarts.sql",
    "07-Insert UserPreference with User ID.sql",
    "08-Sections.sql",
    "09-ScheduleMeta.sql",
    "10-ShiftMeta.sql",
    "11-SectionSlotPatient.sql",
    "12-HrEmployees.sql",
]

# FK-safe order (same as scripts/seed_b.bat)
B_FILES = [
    "B01-AvShunts.sql",
    "B02-DialysisPrescriptions.sql",
    "B07-MedicinePrescriptions.sql",
    "B03-HemodialysisRecords.sql",
    "B04-DialysisRecords.sql",
    "B05-Assessment.sql",
    "B06-ExecutionRecords.sql",
]

C_FILES = [
    "C01-Equipments.sql",
    "C02-MedicalSupplies.sql",
    "C03-AutoStock-Equipments.sql",
    "C04-AutoStock-MedicalSupplies.sql",
]

# Master DB (hemo-master), not the tenant schema.
H_FILES = [
    "00-AdminUsers.sql",
]


@dataclass(frozen=True)
class DbConfig:
    container: str = "db"
    user: str = "postgres"
    database: str = "hemopro-local"
    password: str = "your_password_here"
    master_database: str = "hemo-master"

    @classmethod
    def load(cls, root: Path | None = None) -> DbConfig:
        root = root or repo_root()
        values = {
            "container": "db",
            "user": "postgres",
            "database": "hemopro-local",
            "password": "your_password_here",
            "master_database": "hemo-master",
        }
        # Optional KEY=VALUE file (preferred over parsing .bat)
        env_file = root / "scripts" / "db.env"
        if env_file.exists():
            values.update(_parse_env_file(env_file))
        bat_file = root / "scripts" / "db.env.bat"
        if bat_file.exists():
            values.update(_parse_bat_sets(bat_file))

        # Process env wins
        if os.environ.get("HEMO_DB_CONTAINER"):
            values["container"] = os.environ["HEMO_DB_CONTAINER"]
        if os.environ.get("HEMO_DB_USER"):
            values["user"] = os.environ["HEMO_DB_USER"]
        if os.environ.get("HEMO_DB_NAME"):
            values["database"] = os.environ["HEMO_DB_NAME"]
        if os.environ.get("PGPASSWORD"):
            values["password"] = os.environ["PGPASSWORD"]
        if os.environ.get("HEMO_MASTER_DB_NAME"):
            values["master_database"] = os.environ["HEMO_MASTER_DB_NAME"]

        return cls(
            container=values["container"],
            user=values["user"],
            database=values["database"],
            password=values["password"],
            master_database=values["master_database"],
        )


def _parse_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    mapping = {
        "HEMO_DB_CONTAINER": "container",
        "HEMO_DB_USER": "user",
        "HEMO_DB_NAME": "database",
        "PGPASSWORD": "password",
        "HEMO_MASTER_DB_NAME": "master_database",
    }
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key in mapping:
            out[mapping[key]] = val
    return out


def _parse_bat_sets(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    mapping = {
        "HEMO_DB_CONTAINER": "container",
        "HEMO_DB_USER": "user",
        "HEMO_DB_NAME": "database",
        "PGPASSWORD": "password",
        "HEMO_MASTER_DB_NAME": "master_database",
    }
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.upper().startswith("REM") or line.startswith("::"):
            continue
        m = re.match(r"set\s+(?:\"([^=]+)=([^\"]*)\"|([^=]+)=(.*))$", line, flags=re.IGNORECASE)
        if not m:
            continue
        key = (m.group(1) or m.group(3) or "").strip()
        val = (m.group(2) if m.group(1) is not None else m.group(4) or "").strip()
        if key in mapping:
            out[mapping[key]] = val
    return out


@dataclass
class TableCount:
    name: str
    count: int | None  # None = missing / error
    error: str | None = None


@dataclass
class GroupStatus:
    key: str
    label: str
    tables: list[TableCount] = field(default_factory=list)

    @property
    def populated(self) -> bool:
        return any(t.count is not None and t.count > 0 for t in self.tables)

    @property
    def reachable(self) -> bool:
        return any(t.count is not None for t in self.tables)


@dataclass
class DbStatus:
    docker_ok: bool
    container_running: bool
    psql_ok: bool
    message: str
    groups: dict[str, GroupStatus] = field(default_factory=dict)
    config: DbConfig | None = None


@dataclass
class SqlResult:
    path: Path
    ok: bool
    detail: str = ""


def docker_available() -> bool:
    return shutil.which("docker") is not None


def container_running(cfg: DbConfig) -> bool:
    try:
        proc = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", cfg.container],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0 and proc.stdout.strip().lower() == "true"


def run_psql(cfg: DbConfig, sql: str, *, timeout: int = 120) -> tuple[bool, str]:
    """Run SQL via docker exec psql. Returns (ok, stdout_or_stderr)."""
    env = os.environ.copy()
    env["PGPASSWORD"] = cfg.password
    cmd = [
        "docker",
        "exec",
        "-i",
        "-e",
        f"PGPASSWORD={cfg.password}",
        cfg.container,
        "psql",
        "-U",
        cfg.user,
        "-d",
        cfg.database,
        "-v",
        "ON_ERROR_STOP=1",
        "-t",
        "-A",
    ]
    try:
        proc = subprocess.run(
            cmd,
            input=sql,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return False, "psql timed out"
    except OSError as exc:
        return False, str(exc)
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode != 0:
        return False, err or out or f"exit {proc.returncode}"
    return True, out


def run_sql_file(cfg: DbConfig, path: Path, *, timeout: int = 600) -> SqlResult:
    if not path.exists():
        return SqlResult(path=path, ok=False, detail="file not found")
    env = os.environ.copy()
    env["PGPASSWORD"] = cfg.password
    cmd = [
        "docker",
        "exec",
        "-i",
        "-e",
        f"PGPASSWORD={cfg.password}",
        cfg.container,
        "psql",
        "-U",
        cfg.user,
        "-d",
        cfg.database,
        "-v",
        "ON_ERROR_STOP=1",
    ]
    try:
        with path.open("rb") as fh:
            proc = subprocess.run(
                cmd,
                stdin=fh,
                capture_output=True,
                timeout=timeout,
                check=False,
                env=env,
            )
    except subprocess.TimeoutExpired:
        return SqlResult(path=path, ok=False, detail="timed out")
    except OSError as exc:
        return SqlResult(path=path, ok=False, detail=str(exc))
    stdout = (proc.stdout or b"").decode("utf-8", errors="replace").strip()
    stderr = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
    if proc.returncode != 0:
        return SqlResult(path=path, ok=False, detail=stderr or stdout or f"exit {proc.returncode}")
    return SqlResult(path=path, ok=True, detail=stdout)


def _count_sql(table: str, schema: str = SCHEMA) -> str:
    # Avoid failing the whole batch if one table missing: one statement per call
    return f'SELECT COUNT(*) FROM {schema}."{table}";'


def probe_count(cfg: DbConfig, table: str, schema: str = SCHEMA) -> TableCount:
    ok, out = run_psql(cfg, _count_sql(table, schema), timeout=30)
    if not ok:
        return TableCount(name=table, count=None, error=out.splitlines()[-1] if out else "error")
    try:
        return TableCount(name=table, count=int(out.splitlines()[-1].strip()))
    except ValueError:
        return TableCount(name=table, count=None, error=out)


def collect_status(cfg: DbConfig | None = None, root: Path | None = None) -> DbStatus:
    cfg = cfg or DbConfig.load(root)
    if not docker_available():
        return DbStatus(
            docker_ok=False,
            container_running=False,
            psql_ok=False,
            message="docker CLI not found in PATH",
            config=cfg,
        )
    running = container_running(cfg)
    if not running:
        return DbStatus(
            docker_ok=True,
            container_running=False,
            psql_ok=False,
            message=f'container "{cfg.container}" is not running',
            config=cfg,
        )

    ok, msg = run_psql(cfg, "SELECT 1;", timeout=20)
    if not ok:
        return DbStatus(
            docker_ok=True,
            container_running=True,
            psql_ok=False,
            message=f"psql failed: {msg}",
            config=cfg,
        )

    groups = {
        "a": GroupStatus(
            key="a",
            label="A — Core",
            tables=[
                probe_count(cfg, "Units"),
                probe_count(cfg, "Users"),
                probe_count(cfg, "Patients"),
                probe_count(cfg, "Sections"),
                probe_count(cfg, "SectionSlotPatient"),
            ],
        ),
        "b": GroupStatus(
            key="b",
            label="B — Sessions",
            tables=[
                probe_count(cfg, "AvShunts"),
                probe_count(cfg, "DialysisPrescriptions"),
                probe_count(cfg, "MedicinePrescriptions"),
                probe_count(cfg, "HemodialysisRecords"),
                probe_count(cfg, "DialysisRecords"),
                probe_count(cfg, "ExecutionRecords"),
            ],
        ),
        "c": GroupStatus(
            key="c",
            label="C — Stock",
            tables=[
                probe_count(cfg, "Equipments"),
                probe_count(cfg, "MedicalSupplies"),
                probe_count(cfg, "AutoStocks"),
                probe_count(cfg, "AutoStockItems"),
            ],
        ),
        "h": GroupStatus(
            key="h",
            label="H — HemoAdmin",
            tables=[
                probe_count(cfg_for_group(cfg, "h"), "AdminUsers", schema="public"),
            ],
        ),
    }
    return DbStatus(
        docker_ok=True,
        container_running=True,
        psql_ok=True,
        message="ok",
        groups=groups,
        config=cfg,
    )


def hemo_admin_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "seeds" / "hemo_admin"


def cfg_for_group(cfg: DbConfig, group: str) -> DbConfig:
    """Group H writes platform admins in the master database."""
    if group.lower() == "h":
        return replace(cfg, database=cfg.master_database)
    return cfg


def seed_files_for(group: str, root: Path | None = None) -> list[Path]:
    root = root or repo_root()
    g = group.lower()
    if g == "a":
        return [a_core_dir(root) / name for name in A_FILES]
    if g == "b":
        return [b_sessions_dir(root) / name for name in B_FILES]
    if g == "c":
        return [c_stock_dir(root) / name for name in C_FILES]
    if g == "h":
        return [hemo_admin_dir(root) / name for name in H_FILES]
    raise ValueError(f"unknown seed group: {group}")


def normalize_run_order(groups: list[str]) -> list[str]:
    """Canonical order: H → A → C → B (H is master DB; B depends on patients)."""
    wanted = {g.lower() for g in groups}
    order = []
    for g in ("h", "a", "c", "b"):
        if g in wanted:
            order.append(g)
    unknown = wanted - {"a", "b", "c", "h"}
    if unknown:
        raise ValueError(f"unknown groups: {', '.join(sorted(unknown))}")
    return order


def build_warnings(status: DbStatus, groups: list[str]) -> list[str]:
    warnings: list[str] = []
    if not status.psql_ok:
        warnings.append(f"DB not ready: {status.message}")
        return warnings
    selected = [g.lower() for g in groups]
    if "b" in selected:
        patients = _table_count(status, "a", "Patients")
        if patients == 0:
            warnings.append("B selected but Patients=0 — seed A first (or include A).")
        elif patients is None:
            warnings.append("Could not read Patients count — B may fail on FK.")
    for g in selected:
        gs = status.groups.get(g)
        if g == "h" and gs and gs.populated:
            warnings.append(
                "H — HemoAdmin already has AdminUsers — re-seed updates good/nott and resets their password."
            )
            continue
        if gs and gs.populated:
            warnings.append(
                f"{gs.label} already has rows — re-seed will likely hit duplicate key errors."
            )
    return warnings


def _table_count(status: DbStatus, group: str, table: str) -> int | None:
    gs = status.groups.get(group)
    if not gs:
        return None
    for t in gs.tables:
        if t.name == table:
            return t.count
    return None


def run_groups(
    groups: list[str],
    cfg: DbConfig | None = None,
    root: Path | None = None,
    on_start=None,
    on_result=None,
) -> tuple[int, int]:
    """
    Execute selected seed groups. Returns (passed, failed).
    on_start(index, total, path), on_result(index, total, SqlResult)
    """
    root = root or repo_root()
    cfg = cfg or DbConfig.load(root)
    order = normalize_run_order(groups)
    files: list[tuple[DbConfig, Path]] = []
    for g in order:
        group_cfg = cfg_for_group(cfg, g)
        for path in seed_files_for(g, root):
            files.append((group_cfg, path))

    total = len(files)
    passed = 0
    failed = 0
    for i, (group_cfg, path) in enumerate(files, start=1):
        if on_start:
            on_start(i, total, path)
        result = run_sql_file(group_cfg, path)
        if result.ok:
            passed += 1
        else:
            failed += 1
        if on_result:
            on_result(i, total, result)
    return passed, failed
