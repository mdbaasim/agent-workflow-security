
from workflow_security.events import ActionEvent
from workflow_security.policy import evaluate_action
from workflow_security.correlator import detect_policy_evasion
from workflow_security.guard import WorkflowGuard


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
