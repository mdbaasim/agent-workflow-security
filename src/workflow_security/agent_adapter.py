"""Agent security adapter and pre-execution enforcement proxy.

Ensures tools cannot access sensitive resources without passing through
IntentFence's deterministic policy and workflow-aware guard boundary.
"""

from typing import Any, Callable
from .events import ActionEvent
from .guard import WorkflowGuard
from .policy import evaluate_action


class SecurityEnforcementError(Exception):
    """Raised when an agent's requested action is blocked or denied by IntentFence."""

    def __init__(self, status: str, reason: str, event: ActionEvent):
        super().__init__(f"IntentFence {status.upper()}: {reason}")
        self.status = status
        self.reason = reason
        self.event = event


class GuardedToolProxy:
    """Pre-execution enforcement boundary wrapping tool execution."""

    def __init__(self, guard: WorkflowGuard, on_evaluation: Callable[[ActionEvent, Any, Any], None] | None = None):
        self.guard = guard
        self.on_evaluation = on_evaluation

    def execute_guarded(
        self,
        event: ActionEvent,
        tool_fn: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Evaluate action before execution. Blocks access if guard or policy denies."""
        baseline = evaluate_action(event, self.guard.restricted_resources)
        guard_decision = self.guard.evaluate(event)

        if self.on_evaluation:
            self.on_evaluation(event, baseline, guard_decision)

        if guard_decision.status in {"denied", "blocked"}:
            raise SecurityEnforcementError(
                status=guard_decision.status,
                reason=guard_decision.reason,
                event=event,
            )

        # Action is allowed - execute safe synthetic tool
        return tool_fn(*args, **kwargs)


class MockAgentEnvironment:
    """Synthetic local tools for demonstrable real-agent workflow enforcement."""

    @staticmethod
    def mock_file_reader(path: str) -> str:
        return f"[Simulated Content for file: {path}]"

    @staticmethod
    def mock_database_query(query: str) -> dict[str, Any]:
        return {"result": f"[Simulated Result for DB query: {query}]"}

    @staticmethod
    def mock_web_fetcher(url: str) -> str:
        return f"[Simulated Web Response from: {url}]"
