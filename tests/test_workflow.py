
import json
import pytest

from workflow_security.events import ActionEvent
from workflow_security.policy import evaluate_action
from workflow_security.correlator import detect_policy_evasion
from workflow_security.guard import WorkflowGuard
from workflow_security.simulator import load_scenario

def make_event(
    resource: str,
    *,
    step: int = 1,
    objective_id: str = "default-objective",
    agent_id: str = "agent-main",
    parent_agent_id: str | None = None,
    tool: str = "file_reader",
    canonical_resource: str | None = None,
    status: str = "requested",
) -> ActionEvent:
    return ActionEvent(
        step=step,
        task_id="test-1",
        objective_id=objective_id,
        agent_id=agent_id,
        parent_agent_id=parent_agent_id,
        tool=tool,
        action="read",
        resource=resource,
        canonical_resource=canonical_resource or resource,
        status=status,
    )


def test_restricted_resource_is_denied():
    event = make_event("payroll_records")

    decision = evaluate_action(
        event,
        restricted_resources={"payroll_records"},
    )

    assert decision.status == "denied"


def test_unrestricted_resource_is_allowed():
    event = make_event("public_docs")

    decision = evaluate_action(
        event,
        restricted_resources={"payroll_records"},
    )

    assert decision.status == "allowed"


def test_detects_tool_switch_after_denial():
    events = [
        make_event(
            "payroll.csv",
            step=1,
            tool="file_reader",
            canonical_resource="payroll_records",
            status="denied",
        ),
        make_event(
            "finance.payroll_view",
            step=2,
            tool="database_query",
            canonical_resource="payroll_records",
            status="requested",
        ),
    ]

    alerts = detect_policy_evasion(events)

    assert len(alerts) == 1
    assert alerts[0].original_tool == "file_reader"
    assert alerts[0].attempting_tool == "database_query"


def test_detects_delegation_after_denial():
    events = [
        make_event(
            "payroll.csv",
            step=1,
            agent_id="agent-main",
            tool="file_reader",
            canonical_resource="payroll_records",
            status="denied",
        ),
        make_event(
            "finance.payroll_view",
            step=2,
            agent_id="agent-helper",
            parent_agent_id="agent-main",
            tool="database_query",
            canonical_resource="payroll_records",
            status="requested",
        ),
    ]

    alerts = detect_policy_evasion(events)

    assert len(alerts) == 1
    assert alerts[0].original_agent == "agent-main"
    assert alerts[0].attempting_agent == "agent-helper"


def test_different_resource_does_not_trigger_alert():
    events = [
        make_event(
            "payroll.csv",
            step=1,
            canonical_resource="payroll_records",
            status="denied",
        ),
        make_event(
            "public_docs",
            step=2,
            tool="document_reader",
            canonical_resource="public_docs",
            status="requested",
        ),
    ]

    alerts = detect_policy_evasion(events)

    assert alerts == []


def test_workflow_guard_blocks_alternative_route_after_denial():
    guard = WorkflowGuard(
        restricted_resources={"payroll_records"}
    )

    first = make_event(
        "payroll.csv",
        step=1,
        tool="file_reader",
        canonical_resource="payroll_records",
        objective_id="export-payroll",
    )

    first_decision = guard.evaluate(first)
    assert first_decision.status == "denied"

    second = make_event(
        "finance.payroll_view",
        step=2,
        tool="database_query",
        canonical_resource="payroll_view",
        objective_id="export-payroll",
    )

    second_decision = guard.evaluate(second)

    assert second_decision.status == "blocked"
    assert "previously denied" in second_decision.reason


def test_workflow_guard_allows_unrelated_objective():
    guard = WorkflowGuard(
        restricted_resources={"payroll_records"}
    )

    restricted = make_event(
        "payroll.csv",
        step=1,
        canonical_resource="payroll_records",
        objective_id="export-payroll",
    )

    assert guard.evaluate(restricted).status == "denied"

    unrelated = make_event(
        "public_docs",
        step=2,
        tool="document_reader",
        canonical_resource="public_docs",
        objective_id="summarize-public-docs",
    )

    assert guard.evaluate(unrelated).status == "allowed"


def test_load_scenario_from_json(tmp_path):
    scenario = {
        "restricted_resources": ["payroll_records"],
        "events": [
            {
                "step": 1,
                "task_id": "test-load-1",
                "objective_id": "export-payroll",
                "agent_id": "agent-main",
                "tool": "file_reader",
                "action": "read",
                "resource": "payroll.csv",
                "canonical_resource": "payroll_records",
                "status": "requested",
            }
        ],
    }

    path = tmp_path / "scenario.json"
    path.write_text(json.dumps(scenario), encoding="utf-8")

    restricted_resources, events = load_scenario(path)

    assert restricted_resources == {"payroll_records"}
    assert len(events) == 1
    assert events[0].task_id == "test-load-1"


def test_load_scenario_rejects_empty_events(tmp_path):
    scenario = {
        "restricted_resources": ["payroll_records"],
        "events": [],
    }

    path = tmp_path / "empty.json"
    path.write_text(json.dumps(scenario), encoding="utf-8")

    with pytest.raises(ValueError, match="at least one event"):
        load_scenario(path)


def test_load_scenario_rejects_different_task_ids(tmp_path):
    event = {
        "step": 1,
        "task_id": "task-1",
        "objective_id": "export-payroll",
        "agent_id": "agent-main",
        "tool": "file_reader",
        "action": "read",
        "resource": "payroll.csv",
        "canonical_resource": "payroll_records",
        "status": "requested",
    }

    second_event = event.copy()
    second_event["step"] = 2
    second_event["task_id"] = "task-2"

    scenario = {
        "restricted_resources": ["payroll_records"],
        "events": [event, second_event],
    }

    path = tmp_path / "different_tasks.json"
    path.write_text(json.dumps(scenario), encoding="utf-8")

    with pytest.raises(ValueError, match="share one task_id"):
        load_scenario(path)
