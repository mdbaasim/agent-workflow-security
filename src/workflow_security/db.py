"""SQLite audit persistence for IntentFence security events and decisions."""

import os
import sqlite3
from pathlib import Path
from typing import Any

if os.environ.get("VERCEL"):
    DEFAULT_DB_PATH = Path("/tmp/intentfence.db")
else:
    DEFAULT_DB_PATH = (
        Path(__file__).resolve().parents[2] / "data" / "intentfence.db"
    )


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    target = Path(db_path) if db_path else DEFAULT_DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | str | None = None) -> None:
    """Initialize database tables if they do not exist."""
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                scenario_name TEXT NOT NULL,
                started_at TEXT NOT NULL,
                total_events INTEGER DEFAULT 0,
                status TEXT DEFAULT 'completed'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS evaluated_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                step INTEGER NOT NULL,
                task_id TEXT NOT NULL,
                objective_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                parent_agent_id TEXT,
                tool TEXT NOT NULL,
                action TEXT NOT NULL,
                resource TEXT NOT NULL,
                canonical_resource TEXT NOT NULL,
                raw_status TEXT NOT NULL,
                baseline_status TEXT NOT NULL,
                baseline_reason TEXT,
                guard_status TEXT NOT NULL,
                guard_reason TEXT,
                severity TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_run_id ON evaluated_events(run_id)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_task_obj ON evaluated_events(task_id, objective_id)
            """
        )
        conn.commit()


def record_run(
    run_id: str,
    scenario_name: str,
    started_at: str | None = None,
    db_path: Path | str | None = None,
) -> None:
    """Record a scenario execution run."""
    from datetime import datetime, timezone

    init_db(db_path)
    now_iso = started_at or datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO runs (run_id, scenario_name, started_at, total_events, status)
            VALUES (?, ?, ?, 0, 'active')
            """,
            (run_id, scenario_name, now_iso),
        )
        conn.commit()


def save_evaluated_event(
    event_data: dict[str, Any],
    db_path: Path | str | None = None,
) -> int:
    """Save an evaluated action event along with its baseline and guard decisions."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO evaluated_events (
                run_id, step, task_id, objective_id, agent_id, parent_agent_id,
                tool, action, resource, canonical_resource, raw_status,
                baseline_status, baseline_reason, guard_status, guard_reason,
                severity, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_data.get("run_id", "default-run"),
                event_data["step"],
                event_data["task_id"],
                event_data.get("objective_id", "default-objective"),
                event_data["agent_id"],
                event_data.get("parent_agent_id"),
                event_data["tool"],
                event_data["action"],
                event_data["resource"],
                event_data["canonical_resource"],
                event_data.get("status", "requested"),
                event_data["baseline_status"],
                event_data.get("baseline_reason", ""),
                event_data["guard_status"],
                event_data.get("guard_reason", ""),
                event_data.get("severity", "info"),
                event_data.get("created_at", ""),
            ),
        )
        # Update total_events in runs table
        conn.execute(
            """
            UPDATE runs SET total_events = total_events + 1
            WHERE run_id = ?
            """,
            (event_data.get("run_id", "default-run"),),
        )
        conn.commit()
        return cursor.lastrowid or 0


def get_recent_events(
    run_id: str | None = None,
    limit: int = 100,
    db_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve recorded evaluated events, optionally filtered by run_id."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        if run_id:
            cursor = conn.execute(
                """
                SELECT * FROM evaluated_events
                WHERE run_id = ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (run_id, limit),
            )
        else:
            cursor = conn.execute(
                """
                SELECT * FROM evaluated_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
        rows = cursor.fetchall()
        # Return in ascending order for timeline display
        results = [dict(row) for row in rows]
        if not run_id:
            results.reverse()
        return results


def get_metrics(
    run_id: str | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Compute summary security metrics from persisted decisions."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        query = "SELECT baseline_status, guard_status FROM evaluated_events"
        params: tuple = ()
        if run_id:
            query += " WHERE run_id = ?"
            params = (run_id,)
        rows = conn.execute(query, params).fetchall()

        total = len(rows)
        baseline_allowed = sum(1 for r in rows if r["baseline_status"] == "allowed")
        baseline_denied = sum(1 for r in rows if r["baseline_status"] == "denied")
        guard_blocked = sum(1 for r in rows if r["guard_status"] == "blocked")
        guard_denied = sum(1 for r in rows if r["guard_status"] == "denied")
        caught_alternative = any(
            r["baseline_status"] == "allowed" and r["guard_status"] == "blocked"
            for r in rows
        )

        return {
            "total_events": total,
            "baseline_allowed": baseline_allowed,
            "baseline_denied": baseline_denied,
            "guard_blocked": guard_blocked,
            "guard_denied": guard_denied,
            "caught_alternative": caught_alternative,
        }


def clear_db(db_path: Path | str | None = None) -> None:
    """Clear all records for demo resets."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM evaluated_events")
        conn.execute("DELETE FROM runs")
        conn.commit()
