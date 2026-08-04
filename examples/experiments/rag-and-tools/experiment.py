import os

from splunk_ao import SplunkAOEvaluators
from splunk_ao.experiments import run_experiment

from app import get_users_horoscope


def main():
    """
    Run the horoscope experiment
    """
    # Define a dataset of astrological signs to use
    # in the experiment
    dataset = [
        {"input": "Aquarius"},
        {"input": "Taurus"},
        {"input": "Gemini"},
        {"input": "Leo"},
    ]

    # Run the experiment
    results = run_experiment(
        "horoscope-experiment-2",
        dataset=dataset,
        function=get_users_horoscope,
        metrics=[
            SplunkAOEvaluators.tool_error_rate,
            SplunkAOEvaluators.tool_selection_quality,
            SplunkAOEvaluators.chunk_attribution_utilization,
            SplunkAOEvaluators.context_adherence,
        ],
        project=os.environ["SPLUNK_AO_PROJECT"],
    )

    # Print a link to the experiment results
    print("Experiment Results:")
    print(results["link"])


if __name__ == "__main__":
    main()
