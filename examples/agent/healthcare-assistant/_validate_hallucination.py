"""2-app hallucination demo validation.

Validates that log_demo_hallucination() logs correctly and whether the trace
appears in the same session as the chat query or as a separate session.

Env variants:
  A: splunk-ao SDK  → lab0
  B: splunk-ao SDK  → Galileo staging
  C: galileo SDK    → Galileo staging (baseline)

Usage (from 2-app-with-instrumentation/, using .venv):
  .venv/bin/python3 _validate_hallucination.py       # all
  .venv/bin/python3 _validate_hallucination.py a     # lab0 only
  .venv/bin/python3 _validate_hallucination.py b     # staging splunk-ao
  .venv/bin/python3 _validate_hallucination.py c     # staging galileo
"""
import asyncio
import importlib.util
import os
import sys
from pathlib import Path

ENVS = {
    "a": (".env.local",           "A — splunk-ao SDK  → lab0",           "splunk_ao"),
    "b": (".env.splunk-ao-standalone", "B — splunk-ao SDK  → staging",    "splunk_ao"),
    "c": (".env.galileo",          "C — galileo SDK    → staging",        "galileo"),
}

CHAT_QUERY = ("RAG path", "What is the dosage and common side effects of Lisinopril?")

# Patch openai.AsyncOpenAI to inject api-version for Azure APIM before any import.
import openai as _openai_module
_orig_async_init = _openai_module.AsyncOpenAI.__init__

def _patched_async_init(self, *args, **kwargs):
    dq = dict(kwargs.pop("default_query", None) or {})
    dq.setdefault("api-version", os.getenv("OPENAI_API_VERSION", "2024-12-01-preview"))
    kwargs["default_query"] = dq
    _orig_async_init(self, *args, **kwargs)

_openai_module.AsyncOpenAI.__init__ = _patched_async_init


def _load_env(env_file: str):
    from dotenv import load_dotenv
    for var in [
        "SPLUNK_AO_API_KEY", "SPLUNK_AO_CONSOLE_URL", "SPLUNK_AO_PROJECT",
        "SPLUNK_AO_AGENT_STREAM", "SPLUNK_AO_REALM", "SPLUNK_AO_O11Y_TOKEN",
        "SPLUNK_AO_O11Y_API_TOKEN",
        "GALILEO_API_KEY", "GALILEO_CONSOLE_URL", "GALILEO_PROJECT", "GALILEO_LOG_STREAM",
    ]:
        os.environ.pop(var, None)
    load_dotenv(Path(__file__).parent / env_file, override=True)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


async def run_env(key: str, env_file: str, label: str, sdk: str):
    print(f"\n{'='*65}")
    print(f"  ENV {label}")
    print(f"{'='*65}")

    _load_env(env_file)

    sys.path.insert(0, str(Path(__file__).parent))

    # Load agent and hallucination helpers for the right SDK
    if sdk == "galileo":
        agent_mod = _load_module("agent_galileo", Path(__file__).parent / "_agent_galileo.py")
        hall_mod = _load_module("hallucination_helpers_galileo",
                                Path(__file__).parent / "_hallucination_helpers_galileo.py")
    else:
        for mod_name in ["agent", "agent_galileo"]:
            sys.modules.pop(mod_name, None)
        import agent as agent_mod
        from helpers import hallucination_helpers as hall_mod

    session_id = f"validate-hallucination-{key}-001"
    agent = agent_mod.HealthcareAgent(session_id=session_id)
    agent.load_tools()

    # Step 1: send a real chat query (creates the session in AO)
    label_q, query = CHAT_QUERY
    print(f"\n  [Step 1] Chat query — {label_q}")
    result = await agent._process_query_async([{"role": "user", "content": query}])
    print(f"  Response: {str(result)[:200]}")

    # Step 2: log the hallucination — passing session_id but NO existing_logger
    #         (mirrors the Streamlit behavior when no logger is in session state)
    print(f"\n  [Step 2] log_demo_hallucination(existing_logger=None, session_id={session_id!r})")
    config = agent.config
    success = hall_mod.log_demo_hallucination(
        config=config,
        existing_logger=None,
        session_id=session_id,
    )
    print(f"  Success: {success}")

    project = os.getenv("SPLUNK_AO_PROJECT") or os.getenv("GALILEO_PROJECT")
    stream  = os.getenv("SPLUNK_AO_AGENT_STREAM") or os.getenv("GALILEO_LOG_STREAM")
    realm   = os.getenv("SPLUNK_AO_REALM") or os.getenv("SPLUNK_AO_CONSOLE_URL") or os.getenv("GALILEO_CONSOLE_URL")
    print(f"\n  Project:      {project}")
    print(f"  Agent stream: {stream}")
    print(f"  Endpoint:     {realm}")
    print(f"  session_id:   {session_id}")
    print()
    print("  >> Check console: do chat trace and hallucination trace share the same session?")


async def main():
    targets = [sys.argv[1].lower()] if len(sys.argv) > 1 else ["a", "b", "c"]
    for t in targets:
        env_file, label, sdk = ENVS[t]
        await run_env(t, env_file, label, sdk)
    print("\nDone — check AO console / Galileo staging for session grouping.")


if __name__ == "__main__":
    asyncio.run(main())
