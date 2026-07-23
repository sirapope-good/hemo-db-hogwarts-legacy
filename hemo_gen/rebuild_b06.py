"""Rebuild B06 ExecutionRecords to match current B07 / state medicine IDs."""

from __future__ import annotations

import datetime as dt
import random
from pathlib import Path

from hemo_gen.config import B03_FILE, B06_FILE, b_file, state_path
from hemo_gen.execution import B06_COLUMNS, build_session_executions
from hemo_gen.medicine_prescription import MedicinePrescriptionRow, load_templates
from hemo_gen.rebuild_b04 import _load_b03_sessions
from hemo_gen.session_builder import BuiltSession
from hemo_gen.sql_io import append_rows
from hemo_gen.state import GenState


def _built_from_ref(ref) -> BuiltSession:
    return BuiltSession(
        hemo_id=ref.hemo_id,
        b03_fields=[],
        cycle_start=ref.cycle_start,
        cycle_end=ref.cycle_end,
        completed=ref.completed,
        uf_goal=ref.uf_goal,
        pre_weight=ref.pre_weight,
        post_weight=ref.post_weight,
        dry_weight=ref.post_weight,
    )


def rebuild_b06(base: Path, patient_id: str | None = None, *, dry_run: bool = False) -> tuple[int, int]:
    """Returns (sessions_scanned, execution_rows)."""
    state = GenState.load(state_path(base))
    templates = load_templates()
    b03_path = b_file(B03_FILE, base)
    b06_path = b_file(B06_FILE, base)
    sessions = _load_b03_sessions(b03_path, patient_id)
    rows: list[list[str]] = []

    for ref in sessions:
        ps = state.for_patient(ref.patient_id)
        active: list[MedicinePrescriptionRow] = []
        for key, rx_id in ps.medicine_prescription_ids.items():
            tmpl = templates.get(key)
            if not tmpl:
                continue
            active.append(
                MedicinePrescriptionRow(
                    id=rx_id,
                    key=key,
                    role=tmpl.role,
                    medicine_id=tmpl.medicine_id,
                    non_dialysis=tmpl.non_dialysis,
                    execute_chance=tmpl.execute_chance,
                    route=tmpl.route,
                    fields=[],
                )
            )
        if not active:
            continue
        rng = random.Random(abs(hash(ref.hemo_id)) % (2**31))
        rows.extend(build_session_executions(_built_from_ref(ref), active, rng))

    if dry_run:
        return len(sessions), len(rows)

    b06_path.write_text("", encoding="utf-8")
    if rows:
        append_rows(b06_path, "ExecutionRecords", B06_COLUMNS, rows, "hemo_gen ExecutionRecords")
    else:
        b06_path.write_text("-- hemo_gen ExecutionRecords (empty)\n", encoding="utf-8")
    return len(sessions), len(rows)
