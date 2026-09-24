import os
import time
from pathlib import Path

from dotenv import load_dotenv

from splunk_ao import SplunkAOEvaluators, splunk_ao_context
from splunk_ao.experiments import create_experiment
from splunk_ao.projects import create_project, get_project
from splunk_ao.resources.models import MetricSuccess
from splunk_ao.search import get_sessions
from splunk_ao.utils.metrics import create_metric_configs

# Provide the name of a session-level metric
METRIC_NAME = SplunkAOEvaluators.conversation_quality

# example custom metric name (must be set up in advance)
# METRIC_NAME = "multi-turn-session-test-metric-apples"

# Load environment variables from the .env file.
load_dotenv(Path(__file__).with_name(".env"))

# Get the Splunk AO project

project_name = os.environ["SPLUNK_AO_PROJECT"]
project_obj = get_project(name=project_name)
if not project_obj:
    project_obj = create_project(project_name)

print(f"Project name: {project_obj.name}, Project ID: {project_obj.id}")

# Create a unique experiment

time_suffix = time.strftime("%m%d-%H%M")

experiment = create_experiment(
    experiment_name=f"multi-turn-experiment-{time_suffix}", experiment_group="multi-turn examples"
)
print(f"Experiment name: {experiment.name}")

splunk_ao_context.init(project=project_obj.name, experiment_id=experiment.id)

# Enable a session-level metric in the created experiment, and get the metric ID

metric_configs, _ = create_metric_configs(project_id=project_obj.id, run_id=experiment.id, metrics=[METRIC_NAME])
assert len(metric_configs) == 1
metric_name = metric_configs[0].name
metric_id = metric_configs[0].id
print(f"Metric Name: {metric_name}")
print(f"Metric ID: {metric_id}")

# Log a multi-turn convo using Splunk AO context and logger

multi_turn_convo = [
    {"user": "What is your favorite fruit?", "assistant": "I like blueberries. What about you?"},
    {"user": "I like strawberries.", "assistant": "Strawberries are great! Do you like blueberries too?"},
    {"user": "Yes, I do!", "assistant": "Awesome! Blueberries are delicious and packed with nutrients."},
]


logger = splunk_ao_context.get_logger_instance(project=project_obj.name, experiment_id=experiment.id)

# Create a session and log traces for each turn in the conversation

logger.start_session()

for turn in multi_turn_convo:
    logger.start_trace(input=turn["user"], name="User turn")
    logger.add_llm_span(input=turn["user"], output=turn["assistant"], model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    logger.conclude(output=turn["assistant"])


# This one-shot script has finished producing telemetry. terminate() drains
# completed spans and shuts down SDK-owned exporter resources.
logger.terminate()

# Poll the session-level metric until it's computed

poll_interval_seconds = 10
deadline = time.monotonic() + 300
while time.monotonic() < deadline:
    sessions = get_sessions(project_id=project_obj.id, experiment_id=experiment.id)
    assert len(sessions.records) > 0, "No sessions found for the experiment"

    session = sessions.records[0]
    metric = session.metric_info.get(metric_id)

    if isinstance(metric, MetricSuccess):
        print(f"Metric {METRIC_NAME} computed successfully with value: {metric.value}")
        break
    print(f"Metric is not computed yet, retrying in {poll_interval_seconds} seconds...")

    time.sleep(poll_interval_seconds)
else:
    raise TimeoutError(f"Metric {METRIC_NAME} was not computed within 300 seconds")
