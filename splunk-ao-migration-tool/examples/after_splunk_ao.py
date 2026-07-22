import os
from splunk_ao import SplunkAOLogger, log, splunk_ao_context

os.environ["SPLUNK_AO_API_KEY"] = "my-key"
os.environ["SPLUNK_AO_PROJECT"] = "my-project"
os.environ["SPLUNK_AO_AGENT_STREAM"] = "production"
# os.environ["SPLUNK_AO_CONSOLE_URL"] = "my-console-url"
# os.environ["SPLUNK_AO_API_URL"] = "my-api-url"

# Decorator approach
@log
def call_llm(prompt: str) -> str:
    return "response"

with splunk_ao_context(project="my-project", log_stream="production"):
    result = call_llm("Hello")

# Direct logger approach
# project/log_stream are constructor args, not start_session args
logger = SplunkAOLogger(project="my-project", log_stream="production")
logger.start_session(name="my-session")
logger.add_llm_span(input="Hello", output="Hi", model="gpt-4")
logger.conclude()   # closes current span; no flush kwarg
logger.flush()      # uploads traces
