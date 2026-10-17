
from dataclasses import dataclass
from typing import Literal

from .events import ActionEvent


@dataclass(frozen=True)
class PolicyDecision:
    status: Literal["allowed", "denied"]
    reason: str


def evaluate_action(
    event: ActionEvent,
    restricted_resources: set[str],
) -> PolicyDecision:
    """Check an action against explicit resource restrictions."""

    if event.canonical_resource in restricted_resources:
        return PolicyDecision(
            status="denied",
            reason=(
                f"Access to restricted resource "
                f"'{event.canonical_resource}' is prohibited."
            ),
        )

    return PolicyDecision(
        status="allowed",
        reason="No matching resource restriction was found.",
    )
