import os

# Load environment variables from the .env file
from dotenv import load_dotenv
from strands import Agent, tool
from strands.models.openai import OpenAIModel
from strands.telemetry import StrandsTelemetry
from strands_tools import calculator, current_time

load_dotenv(override=True)

# Derive OTLP endpoint from realm (O11y Cloud) or fall back to explicit endpoint
realm = os.environ.get("SPLUNK_AO_REALM")
if realm:
    endpoint = f"https://ingest.{realm}.observability.splunkcloud.com/v2/trace/otlp"
else:
    endpoint = os.environ["SPLUNK_AO_API_ENDPOINT"]
os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = endpoint

# O11y Cloud auth via ingest token
os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"X-SF-Token={os.environ['SPLUNK_AO_O11Y_TOKEN']}"

# Routing keys go into resource attributes (not OTLP headers) for O11y Cloud
os.environ["OTEL_RESOURCE_ATTRIBUTES"] = (
    f"splunk_ao.project.name={os.environ['SPLUNK_AO_PROJECT']},"
    f"splunk_ao.logstream.name={os.environ['SPLUNK_AO_AGENT_STREAM']}"
)

# Setup telemetry for the Strands agent using Splunk AO as the OTel backend
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# Uncomment this line to see the OTel output in the console
# strands_telemetry.setup_console_exporter()


# This agent code is from the simple quickstart from the
# Strands Agents documentation
# https://strandsagents.com/latest/documentation/docs/user-guide/quickstart/


# Define a custom tool as a Python function using the @tool decorator
@tool
def letter_counter(word: str, letter: str) -> int:
    """
    Count occurrences of a specific letter in a word.

    Args:
        word (str): The input word to search in
        letter (str): The specific letter to count

    Returns:
        int: The number of occurrences of the letter in the word
    """
    if not isinstance(word, str) or not isinstance(letter, str):
        return 0

    if len(letter) != 1:
        raise ValueError("The 'letter' parameter must be a single character")

    return word.lower().count(letter.lower())


# Create an agent with tools from the community-driven strands-tools package
# as well as our custom letter_counter tool
model = OpenAIModel(model_id="gpt-4o-mini")
agent = Agent(model=model, tools=[calculator, current_time, letter_counter])

# Ask the agent a question that uses the available tools
message = """
I have 4 requests:

1. What is the time right now?
2. Calculate 3111696 / 74088
3. Tell me how many letter R's are in the word "strawberry" 🍓
"""
agent(message)

# Flush spans before exit so BatchSpanProcessor delivers them
from opentelemetry import trace as trace_api
trace_api.get_tracer_provider().force_flush()
