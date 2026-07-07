"""
Upload Existing Evaluation Results to Splunk AO

Use this when you've already run evaluations offline and want to upload
the results and traces to Splunk AO for analysis and visualization.

This is particularly useful when:
- You have historical evaluation data you want to centralize in Splunk AO
- You ran evaluations with a different tool and want to visualize in Splunk AO
- You need to replay past evaluations with full tracing for debugging

How it works:
1. Your JSON file contains: question, context (array of chunks), llm_answer, and ground_truth_answer
2. A Splunk AO dataset is created with just: input (question) and output (ground_truth)
3. During experiment execution, the full data is looked up to create complete traces
4. Splunk AO metrics are computed and all traces are preserved for analysis with proper chunk attribution

Data Flow:
- Splunk AO Dataset: Clean inputs for evaluation (question + ground_truth)
- Local JSON: Full execution data for trace reconstruction (with context chunks array)
- Result: Complete evaluation with metrics and detailed traces
"""

import json
import os
from typing import Any

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Splunk AO imports
from splunk_ao import splunk_ao_context
from splunk_ao.datasets import create_dataset, get_dataset
from splunk_ao.experiments import run_experiment
from splunk_ao.schema.metrics import SplunkAOMetrics


def load_evaluation_data(json_path: str) -> dict[str, dict[str, Any]]:
    """
    Load your existing evaluation results from JSON.

    Creates a lookup dictionary keyed by question for fast access during
    trace reconstruction.

    Expected JSON format:
    [
        {
            "question": "Your question/input",
            "context": ["chunk1", "chunk2", ...] or "single chunk",  # Array of context chunks
            "llm_answer": "The model's response",
            "ground_truth_answer": "Expected correct answer"
        },
        ...
    ]

    Args:
        json_path: Path to JSON file with your evaluation results

    Returns:
        Dict mapping questions to their full evaluation records
    """
    with open(json_path) as f:
        data = json.load(f)

    # Create lookup dict keyed by question
    lookup = {}
    for record in data:
        question = record["question"]
        context = record.get("context", [])

        # Normalize context to always be a list
        if isinstance(context, str):
            context = [context] if context else []
        elif not isinstance(context, list):
            context = [str(context)] if context else []

        lookup[question] = {
            "context": context,
            "llm_answer": record.get("llm_answer", ""),
            "model": record.get("model", "gpt-4o"),
        }  # Allow model override

    return lookup


def create_or_get_dataset(dataset_name: str, evaluation_data: list) -> Any:
    """
    Find existing dataset by name or create a new one.

    This checks if a dataset already exists to avoid duplicates.

    Args:
        dataset_name: Name of the dataset to find or create
        evaluation_data: Data to upload if creating a new dataset

    Returns:
        Dataset object from Splunk AO
    """
    try:
        dataset = get_dataset(name=dataset_name)
        if dataset is not None:
            print(f"✓ Found existing dataset: '{dataset_name}'")
            return dataset
    except Exception as e:
        # Dataset doesn't exist or error occurred
        if "not found" not in str(e).lower() and "does not exist" not in str(e).lower():
            print(f"Warning: {e}")

    # Create new dataset
    print(f"✓ Creating new dataset: '{dataset_name}'")
    dataset = create_dataset(name=dataset_name, content=evaluation_data)
    print(f"  Uploaded {len(evaluation_data)} rows")
    return dataset


def prepare_dataset_for_galileo(json_path: str, dataset_name: str) -> Any:
    """
    Upload your evaluation data to Splunk AO as a dataset.

    Only the input (question) and expected output (ground_truth) are uploaded
    to the dataset. The context and llm_answer are preserved locally and will
    be used during trace reconstruction.

    Args:
        json_path: Path to JSON with your evaluation results
        dataset_name: Name for the dataset in Splunk AO

    Returns:
        Dataset object from Splunk AO
    """
    # Load your evaluation results
    with open(json_path) as f:
        raw_data = json.load(f)

    # Transform to Splunk AO dataset format
    # Only include input and expected output for clean evaluation
    galileo_dataset = []
    for row in raw_data:
        galileo_row = {"input": row["question"], "output": row.get("ground_truth_answer", "")}
        galileo_dataset.append(galileo_row)

    return create_or_get_dataset(dataset_name, galileo_dataset)


def create_replay_function(evaluation_lookup: dict[str, dict[str, Any]], system_prompt: str | None = None):
    """
    Create a function that replays your evaluation with full tracing.

    This returns a function that Splunk AO will call for each row in the dataset.
    It reconstructs the full execution trace from your stored results.

    Args:
        evaluation_lookup: Dict mapping questions to their full evaluation data
        system_prompt: Optional system prompt to include in LLM traces

    Returns:
        Function that takes input and returns the LLM answer with full tracing
    """

    # Default system prompt if none provided
    if system_prompt is None:
        system_prompt = (
            "You are a helpful AI assistant. Use the provided context to answer the question accurately and concisely."
        )

    def replay_evaluation(input: str, **kwargs) -> str:
        """
        Replay a single evaluation with full trace reconstruction.

        Args:
            input: The question/input from the Splunk AO dataset

        Returns:
            The LLM answer from your evaluation results
        """
        question = input

        # Look up the full evaluation record
        if question not in evaluation_lookup:
            raise KeyError(f"Question not found in evaluation data: {question[:100]}...")

        eval_record = evaluation_lookup[question]
        context_chunks = eval_record["context"]
        llm_answer = eval_record["llm_answer"]
        model = eval_record.get("model", "gpt-4o")

        # Get Splunk AO logger for trace reconstruction
        logger = splunk_ao_context.get_logger_instance()

        # Log retriever span if context was used
        if context_chunks:
            logger.add_retriever_span(input=question, output=context_chunks, name="Context Retrieval")

        # Format context chunks for the prompt
        # Join multiple chunks with clear separators
        if context_chunks:
            context_text = "\n\n---\n\n".join([f"Chunk {i + 1}:\n{chunk}" for i, chunk in enumerate(context_chunks)])
        else:
            context_text = ""

        # Log LLM span with full prompt and response
        if context_text:
            full_prompt = f"{system_prompt}\n\nContext:\n{context_text}\n\nQuestion:\n{question}"
        else:
            full_prompt = f"{system_prompt}\n\nQuestion:\n{question}"

        logger.add_llm_span(input=full_prompt, output=llm_answer, model=model, name="Answer Generation")

        # Return the answer for evaluation against ground truth
        return llm_answer

    return replay_evaluation


def upload_experiment(
    dataset: Any,
    evaluation_data_path: str,
    project_name: str,
    run_name: str,
    system_prompt: str | None = None,
    metrics: list | None = None,
) -> Any:
    """
    Upload your evaluation results as a Splunk AO experiment.

    This runs an experiment using your existing results, reconstructing
    full traces for visualization and computing Splunk AO metrics.

    Args:
        dataset: Splunk AO dataset object
        evaluation_data_path: Path to your JSON file with full evaluation data
        project_name: Splunk AO project name
        run_name: Name for this experiment run
        system_prompt: Optional system prompt used in your evaluation
        metrics: Optional list of metrics to compute (uses defaults if None)

    Returns:
        Experiment results
    """
    print(f"\nRunning experiment: {run_name}")

    # Load evaluation data for trace reconstruction
    evaluation_lookup = load_evaluation_data(evaluation_data_path)
    print(f"  Loaded {len(evaluation_lookup)} evaluation records")

    # Create replay function with lookup data
    replay_fn = create_replay_function(evaluation_lookup, system_prompt)

    # Use default metrics if none provided
    if metrics is None:
        metrics = [
            SplunkAOMetrics.ground_truth_adherence,
            SplunkAOMetrics.context_adherence,
            SplunkAOMetrics.chunk_attribution_utilization,
            SplunkAOMetrics.completeness,
            SplunkAOMetrics.correctness,
        ]

    # Run experiment with your data
    results = run_experiment(run_name, project=project_name, dataset=dataset, function=replay_fn, metrics=metrics)

    print("✓ Experiment complete!")

    return results


def main() -> None:
    """
    Example: Upload existing evaluation results to Splunk AO

    This script demonstrates how to take evaluation results you already have
    and upload them to Splunk AO for analysis, visualization, and comparison.

    Steps:
    1. Load your evaluation data from JSON
    2. Create/retrieve a Splunk AO dataset (input + expected output only)
    3. Run experiment - reconstructs full traces from your stored results
    4. View results in Splunk AO console with metrics and detailed traces
    """

    # Verify environment configuration
    required_vars = ["SPLUNK_AO_API_KEY", "SPLUNK_AO_CONSOLE_URL", "SPLUNK_AO_PROJECT"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]

    if missing_vars:
        print(f"⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("Create a .env file with your Splunk AO credentials (see .env.example)")
        return

    print("=" * 70)
    print("Upload Existing Evaluation Results to Splunk AO")
    print("=" * 70)

    # Configuration
    EVALUATION_DATA_PATH = "dataset.json"
    DATASET_NAME = "space-mission-support-qa-2"
    RUN_NAME = "historical-evaluation-upload"
    SYSTEM_PROMPT = (
        "You are a space mission support AI assistant. "
        "Use the provided mission logs and technical context to answer "
        "questions accurately. If the answer is not in the context, "
        "say you don't know rather than speculating."
    )

    # Step 1: Create or retrieve dataset
    print(f"\n📊 Preparing dataset: {DATASET_NAME}")
    dataset = prepare_dataset_for_galileo(EVALUATION_DATA_PATH, DATASET_NAME)

    # Step 2: Upload experiment with full traces
    print("\n🚀 Uploading experiment...")
    results = upload_experiment(
        dataset=dataset,
        evaluation_data_path=EVALUATION_DATA_PATH,
        project_name=os.environ.get("SPLUNK_AO_PROJECT"),
        run_name=RUN_NAME,
        system_prompt=SYSTEM_PROMPT,
    )

    if results:
        print("\n✅ Success! View your results in Splunk AO")
        print(f"URL: {results['link']}")


if __name__ == "__main__":
    main()
