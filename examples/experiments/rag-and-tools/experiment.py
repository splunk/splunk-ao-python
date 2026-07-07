import os

from app import get_users_horoscope

from splunk_ao import SplunkAOMetrics
from splunk_ao.experiments import run_experiment


def main() -> None:
    """
    Run the horoscope experiment
    """
    # Define a dataset of astrological signs to use
    # in the experiment
    dataset = [{"input": "Aquarius"}, {"input": "Taurus"}, {"input": "Gemini"}, {"input": "Leo"}]

    # Run the experiment
    results = run_experiment(
        "horoscope-experiment-2",
        dataset=dataset,
        function=get_users_horoscope,
        metrics=[
            SplunkAOMetrics.tool_error_rate,
            SplunkAOMetrics.tool_selection_quality,
            SplunkAOMetrics.chunk_attribution_utilization,
            SplunkAOMetrics.context_adherence,
        ],
        project=os.environ["SPLUNK_AO_PROJECT"],
    )

    # Print a link to the experiment results
    print("Experiment Results:")
    print(results["link"])


if __name__ == "__main__":
    main()
