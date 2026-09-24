"""Upload reconstructed historical traces with client-precomputed scores.

This deliberately uses the SDK's structured-ingestion compatibility path.
The collector keeps each complete LoggedTrace until flush(), while the
ingestor sends the resulting TracesIngestRequest to the trace API.
"""

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from galileo_core.schemas.logging.step import Metrics
from splunk_ao.experiments import create_experiment
from splunk_ao.logger.logger import SplunkAOLogger
from splunk_ao.schema.trace import TracesIngestRequest

load_dotenv(Path(__file__).with_name(".env"))


HISTORICAL_RESULTS: list[dict[str, Any]] = [
    {
        "input": "What is the capital of France?",
        "output": "Paris",
        "ground_truth": "Paris",
        "exact_match": 1.0,
        "quality_score": 0.98,
    },
    {
        "input": "What is the capital of Australia?",
        "output": "Sydney",
        "ground_truth": "Canberra",
        "exact_match": 0.0,
        "quality_score": 0.20,
    },
]


def build_experiment_loggers(project_id: str, experiment_id: str) -> tuple[SplunkAOLogger, SplunkAOLogger]:
    """Return an isolated structured collector and its API ingestor."""
    ingestor = SplunkAOLogger(project_id=project_id, experiment_id=experiment_id)

    def forward_reliably(request: TracesIngestRequest) -> None:
        # Ask the backend to finish ingestion before responding. The current
        # telemetry API logs upload failures instead of raising them to user code.
        request.reliable = True
        ingestor.ingest_traces(request)

    collector = SplunkAOLogger(
        project_id=project_id, experiment_id=experiment_id, mode="batch", ingestion_hook=forward_reliably
    )
    return collector, ingestor


def upload_result(collector: SplunkAOLogger, result: dict[str, Any], row_number: int) -> None:
    """Reconstruct one trace and attach scores calculated before ingestion."""
    trace = collector.start_trace(
        input=result["input"],
        name="historical-evaluation",
        metadata={"source": "offline-import", "row_number": row_number},
        tags=["historical", "precomputed-scores"],
        dataset_input=result["input"],
        dataset_output=result["ground_truth"],
        external_id=f"historical-row-{row_number}",
    )

    # Simulate the operation that originally produced the stored answer. No
    # model is called: this is a reconstruction of an already completed run.
    collector.add_llm_span(
        input=result["input"], output=result["output"], model="historical-model", name="answer-generation"
    )

    # These values were calculated before the Splunk AO upload. This is not a
    # LocalMetricConfig and the platform does not recompute these two scores.
    trace.metrics = Metrics(
        offline_exact_match=result["exact_match"],
        offline_quality_score=result["quality_score"],
        test_success=float(result["exact_match"] == 1.0),
    )
    collector.conclude(output=result["output"])


def main() -> None:
    """Create one experiment and upload two historical evaluation records."""
    project_name = os.environ["SPLUNK_AO_PROJECT"]
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    experiment = create_experiment(project_name=project_name, experiment_name=f"precomputed-score-import-{timestamp}")

    collector, ingestor = build_experiment_loggers(
        project_id=str(experiment.project_id), experiment_id=str(experiment.id)
    )
    try:
        for row_number, result in enumerate(HISTORICAL_RESULTS, start=1):
            upload_result(collector, result, row_number)

        # Required for ingestion-hook compatibility mode. It builds and sends
        # one structured request containing both complete LoggedTrace objects.
        collector.flush()
    finally:
        collector.terminate()
        ingestor.terminate()

    print(f"Uploaded {len(HISTORICAL_RESULTS)} historical rows")
    print(f"Project ID: {experiment.project_id}")
    print(f"Experiment ID: {experiment.id}")


if __name__ == "__main__":
    main()
