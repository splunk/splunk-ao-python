"""
Demo session runner — CronJob entrypoint.

Fires the two example queries from config.yaml through the instrumented agent,
then logs one hallucination, all under a single session ID per run.
"""
import asyncio
import importlib.util
import logging
import os
import sys
import time
import uuid

# Ensure the app root (parent of hosted/) is on the path so config, helpers, etc. resolve.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger(__name__)


def _load_instrumented_agent():
    spec = importlib.util.spec_from_file_location(
        "agent_with_instrumentation",
        os.path.join(os.path.dirname(__file__), "..", "agent-with-instrumentation.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["agent_with_instrumentation"] = mod
    spec.loader.exec_module(mod)
    return mod.HealthcareAgent


async def run(HealthcareAgent, config, session_id):
    queries = config["ui"]["example_queries"]
    query_delay = float(os.getenv("QUERY_DELAY_SECONDS", "3"))

    agent = HealthcareAgent(session_id=session_id)
    agent.load_tools()

    for i, question in enumerate(queries, 1):
        log.info("[%d/%d] query=%s", i, len(queries), question[:80])
        try:
            result = await agent._process_query_async([{"role": "user", "content": question}])
            log.info("  → %s", str(result)[:120])
        except Exception:
            log.exception("  query failed")
        if i < len(queries):
            await asyncio.sleep(query_delay)

    return len(queries)


if __name__ == "__main__":
    import config as cfg_mod
    from helpers.hallucination_helpers import log_demo_hallucination

    config = cfg_mod.load_config()
    session_id = f"demo-{uuid.uuid4().hex[:8]}"

    log.info(
        "Demo session starting — project=%s stream=%s session=%s",
        os.getenv("SPLUNK_AO_PROJECT"),
        os.getenv("SPLUNK_AO_AGENT_STREAM"),
        session_id,
    )

    HealthcareAgent = _load_instrumented_agent()
    n = asyncio.run(run(HealthcareAgent, config, session_id))

    time.sleep(float(os.getenv("QUERY_DELAY_SECONDS", "3")))

    log.info("[%d/%d] logging hallucination", n + 1, n + 1)
    try:
        success = log_demo_hallucination(config=config, hallucination_index=0, session_id=session_id)
        log.info("  hallucination logged: %s", success)
    except Exception:
        log.exception("  hallucination failed (non-fatal)")

    log.info("Demo session complete — session=%s", session_id)
