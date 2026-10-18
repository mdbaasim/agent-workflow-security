
import json
from pathlib import Path

from .events import ActionEvent
from .guard import WorkflowGuard
from .policy import evaluate_action


DEFAULT_SCENARIO = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "scenarios"
    / "alternative_route.json"
)


def load_scenario(path: Path) -> tuple[set[str], list[ActionEvent]]:
    """Load and validate a synthetic workflow scenario from JSON."""

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    restricted_resources = set(data["restricted_resources"])
    events = [
        ActionEvent.model_validate(event)
        for event in data["events"]
    ]

    if not events:
        raise ValueError("The scenario must contain at least one event.")

    task_ids = {event.task_id for event in events}
    if len(task_ids) != 1:
        raise ValueError("All events in a scenario must share one task_id.")

    return restricted_resources, events


def run_scenario(path: Path = DEFAULT_SCENARIO) -> None:
    restricted_resources, events = load_scenario(path)

    print("\n=== AI Agent Security Evaluation ===")
    print("Synthetic data only; no real resources are accessed.")
    print(f"Scenario: {path.name}")

    print("\n--- Baseline: Per-Action Policy Checks ---")
    baseline_decisions = []

    for event in events:
        decision = evaluate_action(event, restricted_resources)
        baseline_decisions.append(decision.status)

        print(
            f"Step {event.step} | {event.tool} | "
            f"{decision.status.upper()}"
        )

    print("\n--- Proposed: Workflow-Aware Guard ---")
    guard = WorkflowGuard(restricted_resources)
    guard_decisions = []

    for event in events:
        decision = guard.evaluate(event)
        guard_decisions.append(decision.status)

        print(
            f"Step {event.step} | {event.tool} | "
            f"{decision.status.upper()}"
        )
        print(f"Reason: {decision.reason}")

    print("\n--- Comparison ---")
    for event, baseline, guarded in zip(
        events, baseline_decisions, guard_decisions
    ):
        print(
            f"Step {event.step}: "
            f"baseline={baseline.upper()}, "
            f"workflow_guard={guarded.upper()}"
        )

    caught_alternative = any(
        baseline == "allowed" and guarded == "blocked"
        for baseline, guarded in zip(
            baseline_decisions, guard_decisions
        )
    )

    print(
        "\nAlternative-route attempt caught: "
        f"{'YES' if caught_alternative else 'NO'}"
    )


if __name__ == "__main__":
    run_scenario()
