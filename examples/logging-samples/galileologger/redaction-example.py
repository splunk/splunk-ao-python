# Load environment variables from .env file
from dotenv import load_dotenv

from galileo.resources.models.root_type import RootType
from splunk_ao import SplunkAOLogger
from splunk_ao.config import SplunkAOConfig  # For displaying the log stream URL
from splunk_ao.export import export_records
from splunk_ao.log_streams import get_log_stream
from splunk_ao.projects import get_project

load_dotenv()

logger = SplunkAOLogger()  # Create a logger instance

# Example of how to create "redacted_input", matching "SSN" as sensitive info
# ---------------------------------------------------------------------------
sensitive_info = "SSN"
user_input = "Who's a good bot SSN?"
redacted_input = user_input.replace(sensitive_info, "***")
trace = logger.start_trace(input=user_input, redacted_input=redacted_input)

logger.flush()  # send the trace to Splunk AO

# Example of how to create "redacted_input", matching email as sensitive info
# ---------------------------------------------------------------------------

import re  # regular expression

user_input = "This is the email: example@example.com"

email_match = re.search(r"[\w.-]+@[\w.-]+\.\w+", user_input)
sensitive_info = email_match.group() if email_match else None

if sensitive_info:
    redacted_input = user_input.replace(sensitive_info, "***")
    trace = logger.start_trace(input=user_input, redacted_input=redacted_input)
else:
    trace = logger.start_trace(input=user_input)

logger.flush()  # send the trace to Splunk AO

# It's also possible to use a service such as https://www.private-ai.com/ to create the redacted_input

# Export the logged traces in the logstream

import os

project_name = os.getenv("SPLUNK_AO_PROJECT")
log_stream_name = os.getenv("SPLUNK_AO_LOG_STREAM")

project = get_project(name=project_name)
log_stream = get_log_stream(name=log_stream_name, project_name=project_name)

records = export_records(project_id=project.id, log_stream_id=log_stream.id, root_type=RootType.TRACE)

print(list(records))


# Show link to Splunk AO log stream

config = SplunkAOConfig.get()
project_url = f"{config.console_url}project/{logger.project_id}"
log_stream_url = f"{project_url}/log-streams/{logger.log_stream_id}"

print("🚀 Splunk AO Log Stream:")
print(log_stream_url)
