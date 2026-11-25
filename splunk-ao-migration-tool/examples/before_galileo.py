import os
from galileo import GalileoLogger, log, galileo_context

os.environ["GALILEO_API_KEY"] = "my-api-key"
os.environ["GALILEO_PROJECT"] = "my-project"
os.environ["GALILEO_LOG_STREAM"] = "production"
# os.environ["GALILEO_CONSOLE_URL"] = "my-console-url"
# os.environ["GALILEO_API_URL"] = "my-api-url"

# Decorator approach
@log
def call_llm(prompt: str) -> str:
    return "response"

with galileo_context(project="my-project", log_stream="production"):
    result = call_llm("Hello")

# Direct logger approach
# project/log_stream are constructor args, not start_session args
logger = GalileoLogger(project="my-project", log_stream="production")
logger.start_session(name="my-session")
logger.add_llm_span(input="Hello", output="Hi", model="gpt-4")
logger.conclude()   # closes current span; no flush kwarg
