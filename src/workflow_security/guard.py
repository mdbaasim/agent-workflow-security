
from dataclasses import dataclass
from typing import Literal

from .events import ActionEvent
from .policy import evaluate_action


@dataclass(frozen=True)
class GuardDecision:
    status: Literal["allowed", "denied", "blocked"]
    reason: str


class WorkflowGuard:
    """Combine per-action policy checks with denial-aware tracking."""

    def __init__(self, restricted_resources: set[str]) -> None:
        self.restricted_resources = set(restricted_resources)
        self.denied_objectives: dict[
            tuple[str, str], ActionEvent
        ] = {}

    def evaluate(self, event: ActionEvent) -> GuardDecision:
        key = (event.task_id, event.objective_id)

        # First, apply the independent per-action policy.
        policy_decision = evaluate_action(
            event,
            self.restricted_resources,
        )

        if policy_decision.status == "denied":
            self.denied_objectives.setdefault(key, event)

            return GuardDecision(
                status="denied",
                reason=policy_decision.reason,
            )

        # Then, check whether this exact objective was previously denied.
        previous = self.denied_objectives.get(key)

        if previous is not None:
            return GuardDecision(
                status="blocked",
                reason=(
                    f"Objective '{event.objective_id}' was previously denied "
                    f"at step {previous.step}. Further actions in this objective "
                    "remain blocked pending trusted approval."
                ),
            )

        return GuardDecision(
            status="allowed",
            reason=policy_decision.reason,
        )

    def approve_objective(
        self,
        task_id: str,
        objective_id: str,
    ) -> None:
        """Reset a denial after approval by a trusted controller."""

        self.denied_objectives.pop(
            (task_id, objective_id),
            None,
        )
