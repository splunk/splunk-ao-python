"""Run an application function locally as an experiment."""

import os
from pathlib import Path

from dotenv import load_dotenv

from splunk_ao import SplunkAOEvaluators
from splunk_ao.experiments import run_experiment
from splunk_ao.openai import OpenAI

load_dotenv(Path(__file__).with_name(".env"))

client = OpenAI()


def answer_question(input: str) -> str:
    """Application entry point executed once for each local dataset row."""
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "system", "content": "Answer with only the city name."}, {"role": "user", "content": input}],
        temperature=0.0,
    )
    return response.choices[0].message.content or ""


def main() -> None:
    """Execute the runner locally and configure a platform evaluator."""
    dataset = [
        {"input": "What is the capital of France?", "output": "Paris"},
        {"input": "What is the capital of Japan?", "output": "Tokyo"},
    ]

    result = run_experiment(
        "runner-function-example",
        project=os.environ["SPLUNK_AO_PROJECT"],
        dataset=dataset,
        function=answer_question,
        metrics=[SplunkAOEvaluators.correctness],
    )

    print(result["message"])
    print(result["link"])


if __name__ == "__main__":
    main()
