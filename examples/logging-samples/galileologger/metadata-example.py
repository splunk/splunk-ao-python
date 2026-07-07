from dotenv import load_dotenv

from splunk_ao import SplunkAOLogger
from splunk_ao.config import SplunkAOConfig  # For displaying the log stream URL

# Load environment variables from the .env file
load_dotenv()

# Create a logger instance
logger = SplunkAOLogger()

# Define inputs and outputs
input_prompt = "Explain the following topic succinctly: Newton's First Law"
output_answer = "A body remains at rest or moves in a straight line with constant speed unless acted on by a nonzero net external force."

# Define optional metadata
metadata = {"experimentNumber": "1", "promptVersion": "0.0.1", "field": "physics"}

# Start a Splunk AO session with optional metadata
session_id = logger.start_session(name="Test session", metadata=metadata)

# Initialize a new Trace with optional metadata
trace = logger.start_trace(input=input_prompt, metadata=metadata)

# Add an LLM span to the trace with optional metadata
logger.add_llm_span(
    input=[{"role": "system", "content": input_prompt}], output=output_answer, model="gpt-5-mini", metadata=metadata
)

# Conclude the trace with the final output
logger.conclude(output_answer)

# Flush the trace to Splunk AO
logger.flush()

# Show link to Splunk AO log stream
config = SplunkAOConfig.get()
project_url = f"{config.console_url}project/{logger.project_id}"
log_stream_url = f"{project_url}/log-streams/{logger.log_stream_id}"

print("🚀 Splunk AO Log Stream:")
print(log_stream_url)
