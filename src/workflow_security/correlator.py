
from collections.abc import Iterable
from dataclasses import dataclass

from .events import ActionEvent


@dataclass(frozen=True)
class EvasionAlert:
    task_id: str
    denied_step: int
    attempt_step: int
    canonical_resource: str
    original_agent: str
    attempting_agent: str
    original_tool: str
    attempting_tool: str
    reason: str


def detect_policy_evasion(
    events: Iterable[ActionEvent],
) -> list[EvasionAlert]:
    """Detect tool switching or delegation after a resource denial."""

    ordered_events = sorted(
        events,
        key=lambda event: (event.task_id, event.step),
    )

    previous_denials: dict[
        tuple[str, str], ActionEvent
    ] = {}

    alerts: list[EvasionAlert] = []

    for event in ordered_events:
        key = (event.task_id, event.canonical_resource)
        previous = previous_denials.get(key)

        if previous is not None and event.step > previous.step:
            tool_changed = event.tool != previous.tool
            agent_changed = event.agent_id != previous.agent_id

            if tool_changed or agent_changed:
                reasons = []

                if tool_changed:
                    reasons.append("tool switching after denial")

                if agent_changed:
                    reasons.append("different agent pursuing the same resource")

                alerts.append(
                    EvasionAlert(
                        task_id=event.task_id,
                        denied_step=previous.step,
                        attempt_step=event.step,
                        canonical_resource=event.canonical_resource,
                        original_agent=previous.agent_id,
                        attempting_agent=event.agent_id,
                        original_tool=previous.tool,
                        attempting_tool=event.tool,
                        reason="; ".join(reasons),
                    )
                )

        if event.status in {"denied", "blocked"}:
            previous_denials[key] = event

    return alerts
