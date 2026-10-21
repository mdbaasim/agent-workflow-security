
"""Run IntentFence's synthetic workflow security evaluation."""

import argparse
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

    if not isinstance(data, dict):
        raise ValueError("Scenario JSON must contain an object.")

    if not isinstance(data.get("restricted_resources"), list):
        raise ValueError("'restricted_resources' must be a list.")

    if not isinstance(data.get("events"), list):
        raise ValueError("'events' must be a list.")

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


def run_scenario(
    path: Path = DEFAULT_SCENARIO,
    include_ai: bool = False,
) -> None:
    """Evaluate a scenario and optionally request local AI analysis."""

    restricted_resources, events = load_scenario(path)

    print("\n=== IntentFence Security Evaluation ===")
    print("Synthetic data only; no real resources are accessed.")
    print(f"Scenario: {path.name}")

    print("\n--- Baseline: Per-Action Policy Checks ---")
    baseline_decisions = []

    for event in events:
        decision = evaluate_action(event, restricted_resources)
        baseline_decisions.append(decision)

        print(
            f"Step {event.step} | {event.tool} | "
            f"{decision.status.upper()}"
        )

    print("\n--- Workflow-Aware Guard ---")
    guard = WorkflowGuard(restricted_resources)
    guard_decisions = []

    for event in events:
        decision = guard.evaluate(event)
        guard_decisions.append(decision)

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
            f"baseline={baseline.status.upper()}, "
            f"workflow_guard={guarded.status.upper()}"
        )

    caught_alternative = any(
        baseline.status == "allowed"
        and guarded.status == "blocked"
        for baseline, guarded in zip(
            baseline_decisions, guard_decisions
        )
    )

    print(
        "\nAlternative-route attempt caught: "
        f"{'YES' if caught_alternative else 'NO'}"
    )

    if include_ai:
        from .ai_analyzer import analyze_workflow

        print("\n--- Local AI Security Report (Qwen3) ---")

        try:
            report = analyze_workflow(
                events,
                baseline_decisions,
                guard_decisions,
            )
            print(report)
        except RuntimeError as exc:
            print(f"AI analysis unavailable: {exc}")
            print("The deterministic security evaluation is complete.")
            print("Check Ollama and retry with the --ai option.")


def main() -> None:
    """Parse command-line options and run the evaluation."""

    parser = argparse.ArgumentParser(
        description="IntentFence synthetic workflow security evaluator."
    )

    parser.add_argument(
        "--ai",
        action="store_true",
        help="Add a local Qwen3 analysis using Ollama.",
    )

    parser.add_argument(
        "--scenario",
        type=Path,
        default=DEFAULT_SCENARIO,
        help="Path to a JSON scenario file.",
    )

    args = parser.parse_args()
    run_scenario(path=args.scenario, include_ai=args.ai)


if __name__ == "__main__":
    main()
