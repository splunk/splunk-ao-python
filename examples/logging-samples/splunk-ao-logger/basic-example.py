from splunk_ao import SplunkAOLogger
from splunk_ao.config import SplunkAOConfig  # For displaying the log stream URL

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()

# Create a logger instance
logger = SplunkAOLogger()

# Start a session
session_id = logger.start_session(name="Test session")

# Start a new trace
trace = logger.start_trace("Say this is a test")

# Add an LLM span to the trace
logger.add_llm_span(
    input="Say this is a test",
    output="Hello, this is a test",
    model="gpt-4o",
    num_input_tokens=10,
    num_output_tokens=3,
    total_tokens=13,
    duration_ns=1000,
)

# Conclude the trace with the final output
logger.conclude(output="Hello, this is a test", duration_ns=1000)


# Show link to Splunk AO log stream
config = SplunkAOConfig.get()
project_url = f"{config.console_url}project/{logger.project_id}"
log_stream_url = f"{project_url}/log-streams/{logger.agent_stream_id}"

print("🚀 Splunk AO Log Stream:")
print(log_stream_url)
