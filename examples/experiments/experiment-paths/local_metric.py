"""Configure a client-side LocalMetricConfig for a function experiment."""

import os
from pathlib import Path

from dotenv import load_dotenv

from splunk_ao import Span, StepType, Trace
from splunk_ao.experiments import run_experiment
from splunk_ao.schema.metrics import LocalMetricConfig

load_dotenv(Path(__file__).with_name(".env"))


def normalize_city(input: str) -> str:
    """Deterministic runner used to keep the local-metric example focused."""
    return input.strip().title()


def exact_match(step: Trace | Span) -> tuple[float, dict[str, str]]:
    """Score the completed trace against the dataset ground truth."""
    generated = str(step.output or "").strip().casefold()
    expected = str(getattr(step, "dataset_output", "") or "").strip().casefold()
    return float(generated == expected), {"generated": generated, "expected": expected}


def main() -> None:
    """Run a function experiment configured with a client-side scorer."""
    dataset = [{"input": "paris", "output": "Paris"}, {"input": "tokyo", "output": "Tokyo"}]
    local_exact_match = LocalMetricConfig(
        name="local_exact_match", scorer_fn=exact_match, scorable_types=[StepType.trace], aggregatable_types=[]
    )

    result = run_experiment(
        "local-metric-example",
        project=os.environ["SPLUNK_AO_PROJECT"],
        dataset=dataset,
        function=normalize_city,
        metrics=[local_exact_match],
    )

    print(result["message"])
    print(result["link"])


if __name__ == "__main__":
    main()
