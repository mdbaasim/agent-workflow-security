"""Tests for real-time event ingestion, SQLite persistence, and agent adapter."""

import asyncio
from pathlib import Path
import pytest

from workflow_security.agent_adapter import GuardedToolProxy, MockAgentEnvironment, SecurityEnforcementError
from workflow_security.db import clear_db, get_metrics, get_recent_events, init_db, save_evaluated_event
from workflow_security.events import ActionEvent
from workflow_security.guard import WorkflowGuard
from workflow_security.simulator import load_scenario
from workflow_security.web_app import SandboxActionRequest, app, evaluate_custom_action, export_audit, health_check, ingest_events, list_scenarios, reset_demo


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_intentfence.db"
    init_db(db_file)
    return db_file


def test_sqlite_persistence_and_metrics(temp_db):
    event_dict = {
        "run_id": "test-run-1",
        "step": 1,
        "task_id": "t1",
        "objective_id": "obj1",
        "agent_id": "agent-1",
        "parent_agent_id": None,
        "tool": "file_reader",
        "action": "read",
        "resource": "payroll.csv",
        "canonical_resource": "payroll_records",
        "status": "requested",
        "baseline_status": "denied",
        "baseline_reason": "restricted resource",
        "guard_status": "denied",
        "guard_reason": "restricted resource",
        "severity": "high",
        "created_at": "2026-10-28T10:00:00Z",
    }
    row_id = save_evaluated_event(event_dict, db_path=temp_db)
    assert row_id > 0

    events = get_recent_events(run_id="test-run-1", db_path=temp_db)
    assert len(events) == 1
    assert events[0]["resource"] == "payroll.csv"
    assert events[0]["baseline_status"] == "denied"

    metrics = get_metrics(run_id="test-run-1", db_path=temp_db)
    assert metrics["total_events"] == 1
    assert metrics["baseline_denied"] == 1
    assert metrics["guard_blocked"] == 0

    clear_db(db_path=temp_db)
    assert len(get_recent_events(run_id="test-run-1", db_path=temp_db)) == 0


def test_agent_adapter_enforcement_boundary():
    guard = WorkflowGuard(restricted_resources={"payroll_records"})
    proxy = GuardedToolProxy(guard)

    # 1. First event: accessing payroll is denied
    first_event = ActionEvent(
        step=1,
        task_id="task-proxy",
        objective_id="exfiltrate-payroll",
        agent_id="bot-1",
        tool="file_reader",
        action="read",
        resource="payroll.csv",
        canonical_resource="payroll_records",
        status="requested",
    )
    with pytest.raises(SecurityEnforcementError) as exc_info:
        proxy.execute_guarded(
            first_event,
            MockAgentEnvironment.mock_file_reader,
            "payroll.csv",
        )
    assert exc_info.value.status == "denied"

    # 2. Second event: alternative route in same objective is BLOCKED by guard
    second_event = ActionEvent(
        step=2,
        task_id="task-proxy",
        objective_id="exfiltrate-payroll",
        agent_id="bot-1",
        tool="database_query",
        action="read",
        resource="payroll_view",
        canonical_resource="payroll_view",
        status="requested",
    )
    with pytest.raises(SecurityEnforcementError) as exc_info2:
        proxy.execute_guarded(
            second_event,
            MockAgentEnvironment.mock_database_query,
            "SELECT * FROM payroll_view",
        )
    assert exc_info2.value.status == "blocked"

    # 3. Third event: unrelated legitimate objective is ALLOWED
    third_event = ActionEvent(
        step=3,
        task_id="task-proxy",
        objective_id="read-help",
        agent_id="bot-1",
        tool="web_fetcher",
        action="fetch",
        resource="https://docs.local/help.html",
        canonical_resource="public_help",
        status="requested",
    )
    result = proxy.execute_guarded(
        third_event,
        MockAgentEnvironment.mock_web_fetcher,
        "https://docs.local/help.html",
    )
    assert "[Simulated Web Response" in result


def test_all_scenarios_validity():
    scenarios_dir = Path(__file__).resolve().parents[1] / "data" / "scenarios"
    scenario_files = list(scenarios_dir.glob("*.json"))
    assert len(scenario_files) >= 5

    for sf in scenario_files:
        restricted, events = load_scenario(sf)
        assert len(restricted) >= 1
        assert len(events) >= 1


def test_api_health_endpoint():
    res = asyncio.run(health_check())
    assert res["status"] == "healthy"
    assert "active_run_id" in res
    assert "payroll_records" in res["restricted_resources"]


def test_api_scenarios_endpoint():
    res = asyncio.run(list_scenarios())
    assert "scenarios" in res
    assert len(res["scenarios"]) >= 5


def test_api_event_ingestion_and_stateful_blocking():
    asyncio.run(reset_demo())

    event1 = ActionEvent(
        step=1,
        task_id="ingest-task-1",
        objective_id="obj-steal",
        agent_id="agent-bad",
        tool="file_reader",
        action="read",
        resource="payroll.csv",
        canonical_resource="payroll_records",
        status="requested",
    )
    res1 = asyncio.run(ingest_events(event1))
    assert res1["evaluated_count"] == 1
    assert res1["events"][0]["guard_status"] == "denied"

    # Subsequent event under same objective must be BLOCKED
    event2 = ActionEvent(
        step=2,
        task_id="ingest-task-1",
        objective_id="obj-steal",
        agent_id="agent-bad",
        tool="database_query",
        action="read",
        resource="finance.payroll_view",
        canonical_resource="payroll_view",
        status="requested",
    )
    res2 = asyncio.run(ingest_events(event2))
    assert res2["evaluated_count"] == 1
    assert res2["events"][0]["guard_status"] == "blocked"
    assert res2["metrics"]["caught_alternative"] is True

    # Unrelated objective is allowed
    event3 = ActionEvent(
        step=3,
        task_id="ingest-task-1",
        objective_id="obj-benign",
        agent_id="agent-bad",
        tool="file_reader",
        action="read",
        resource="readme.txt",
        canonical_resource="public_docs",
        status="requested",
    )
    res3 = asyncio.run(ingest_events(event3))
    assert res3["events"][0]["guard_status"] == "allowed"


def test_api_sandbox_and_export():
    asyncio.run(reset_demo())

    # Step 1: Initial denial via sandbox
    req1 = SandboxActionRequest(
        objective_id="sandbox-payroll",
        agent_id="bot-test",
        tool="file_reader",
        action="read",
        resource="payroll.csv",
        canonical_resource="payroll_records",
    )
    res1 = asyncio.run(evaluate_custom_action(req1))
    assert res1["record"]["guard_status"] == "denied"
    assert res1["is_evasion"] is False

    # Step 2: Tool-switching evasion attempt via sandbox
    req2 = SandboxActionRequest(
        objective_id="sandbox-payroll",
        agent_id="bot-test",
        tool="sql_query",
        action="read",
        resource="payroll_view",
        canonical_resource="payroll_view",
    )
    res2 = asyncio.run(evaluate_custom_action(req2))
    assert res2["record"]["guard_status"] == "blocked"
    assert res2["is_evasion"] is True

    # Test export endpoints
    json_resp = asyncio.run(export_audit(format="json"))
    assert "attachment; filename=" in json_resp.headers["Content-Disposition"]
    assert json_resp.media_type == "application/json"
    assert "sandbox-payroll" in json_resp.body.decode("utf-8")

    csv_resp = asyncio.run(export_audit(format="csv"))
    assert "attachment; filename=" in csv_resp.headers["Content-Disposition"]
    assert csv_resp.media_type == "text/csv"
    assert "sandbox-payroll" in csv_resp.body.decode("utf-8")

