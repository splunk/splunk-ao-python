"""Single-env trace validation — called by validate_traces.py as a subprocess."""
import os
import sys
import yaml
from dotenv import load_dotenv
from pathlib import Path

env_file = sys.argv[1]
load_dotenv(env_file, override=True)

import config as cfg_mod
from agent import HealthcareAgent

session_id = f"validate-{Path(env_file).name.lstrip('.')}-001"
agent = HealthcareAgent(session_id=session_id)
agent.load_tools()

# RAG query — exercises the full retrieval path
result = agent.process_query([{
    "role": "user",
    "content": "What is the dosage and common side effects of Lisinopril?",
}])

print("Response:", result[:300])
print(f"\nSession ID: {session_id}")
print(f"Env file:   {env_file}")
print(f"Project:    {os.getenv('SPLUNK_AO_PROJECT') or os.getenv('GALILEO_PROJECT')}")
print(f"Stream:     {os.getenv('SPLUNK_AO_AGENT_STREAM') or os.getenv('GALILEO_LOG_STREAM')}")
