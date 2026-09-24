"""Run a server-side prompt-template experiment."""

import os
from pathlib import Path

from dotenv import load_dotenv

from splunk_ao import Message, MessageRole, SplunkAOEvaluators
from splunk_ao.datasets import create_dataset, get_dataset
from splunk_ao.experiments import run_experiment
from splunk_ao.prompts import create_prompt, get_prompt

load_dotenv(Path(__file__).with_name(".env"))


def main() -> None:
    """Create reusable inputs, then ask Splunk AO to execute the prompt remotely."""
    project_name = os.environ["SPLUNK_AO_PROJECT"]

    dataset_name = "experiment-paths-geography"
    dataset = get_dataset(name=dataset_name, project_name=project_name)
    if dataset is None:
        dataset = create_dataset(
            name=dataset_name,
            project_name=project_name,
            content=[
                {"input": "What is the capital of France?", "output": "Paris"},
                {"input": "What is the capital of Japan?", "output": "Tokyo"},
            ],
        )

    prompt_name = "experiment-paths-geography-prompt"
    prompt = get_prompt(name=prompt_name)
    if prompt is None:
        prompt = create_prompt(
            name=prompt_name,
            project_name=project_name,
            template=[
                Message(role=MessageRole.system, content="Answer with only the city name."),
                Message(role=MessageRole.user, content="{{input}}"),
            ],
        )

    result = run_experiment(
        "prompt-template-example",
        project=project_name,
        dataset=dataset,
        prompt_template=prompt,
        prompt_settings={
            "model_alias": os.getenv("SPLUNK_AO_PROMPT_MODEL_ALIAS", "GPT-4o"),
            "max_tokens": 32,
            "temperature": 0.0,
        },
        metrics=[SplunkAOEvaluators.correctness],
    )

    print(result["message"])
    print(result["link"])


if __name__ == "__main__":
    main()
