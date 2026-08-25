"""
Env A validation — runs the original galileo-based agent (from pre-migration commit 0f4a7d4057)
against the Galileo staging console (healthcare-galileo agentstream).

Called by validate_traces.py as a subprocess with .env.galileo loaded.
"""
import os
import sys
import types
import yaml
from dotenv import load_dotenv
from pathlib import Path
import subprocess

load_dotenv(".env.galileo", override=True)

# Pull the galileo-based agent.py from the last pre-migration commit
result = subprocess.run(
    ["git", "show", "0f4a7d4057:workshop/healthcare-assistant/2-app-with-instrumentation/agent.py"],
    cwd=Path(__file__).parent.parent.parent.parent,  # repo root
    capture_output=True, text=True,
)
if result.returncode != 0:
    print("ERROR: could not get galileo agent.py from commit 0f4a7d4057:", result.stderr)
    sys.exit(1)

original_agent_src = result.stdout

# Patch the source to inject api-version query param (same fix as current agent.py)
# The pre-migration agent has plain ChatOpenAI(...) calls with no default_query.
# We patch by adding a monkeypatch before exec so the network calls work against Azure.
api_version_patch = """
import os as _os
_orig_ChatOpenAI = ChatOpenAI
class ChatOpenAI(_orig_ChatOpenAI):
    def __init__(self, *a, **kw):
        _av = _os.environ.get("OPENAI_API_VERSION")
        if _av and "default_query" not in kw:
            kw["default_query"] = {"api-version": _av}
        super().__init__(*a, **kw)
"""

# Disable RAG for speed
cfg = yaml.safe_load(Path("config.yaml").read_text())
cfg["rag"]["enabled"] = False

import config as cfg_mod
cfg_mod.load_config = lambda: cfg

# Execute original agent source in a fresh module namespace
agent_mod = types.ModuleType("agent_galileo")
agent_mod.__file__ = str(Path(__file__).parent / "agent.py")
sys.modules["agent"] = agent_mod

exec(compile(original_agent_src, "agent_galileo.py", "exec"), agent_mod.__dict__)
exec(compile(api_version_patch, "patch", "exec"), agent_mod.__dict__)

HealthcareAgent = agent_mod.HealthcareAgent

agent = HealthcareAgent(session_id="validate-galileo-001")
agent.load_tools()
result = agent.process_query([{
    "role": "user",
    "content": "What is the dosage and common side effects of Lisinopril?",
}])

print("Response:", result[:300])
print(f"\nSession ID: validate-galileo-001")
print(f"Project:    {os.getenv('GALILEO_PROJECT')}")
print(f"Log stream: {os.getenv('GALILEO_LOG_STREAM')}")
