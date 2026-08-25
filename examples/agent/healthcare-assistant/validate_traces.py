"""
Validation script — fires one LLM trace per env and reports success/failure.

  A: original galileo SDK         → agentstream: healthcare-galileo     (.env.galileo)
  B: splunk-ao SDK (standalone)   → agentstream: healthcare-splunk-ao   (.env.splunk-ao-standalone)
  C: splunk-ao SDK (O11y/realm)   → agentstream: healthcare-assistant   (.env.local)

Usage (from 2-app-with-instrumentation/, venv active):
  python validate_traces.py        # all three
  python validate_traces.py a      # just env A
  python validate_traces.py b      # just env B
  python validate_traces.py c      # just env C
"""
import os
import sys
import subprocess
from pathlib import Path

RUNNER = Path(__file__).parent / "_validate_single.py"
RUNNER_GALILEO = Path(__file__).parent / "_validate_galileo.py"

ENVS = {
    "a": (None,                        "A — galileo SDK          → healthcare-galileo",     ".env.galileo"),
    "b": (".env.splunk-ao-standalone", "B — splunk-ao standalone  → healthcare-splunk-ao",  None),
    "c": (".env.local",                "C — splunk-ao O11y/realm  → healthcare-assistant",  None),
}

if __name__ == "__main__":
    targets = [sys.argv[1].lower()] if len(sys.argv) > 1 else ["a", "b", "c"]
    for t in targets:
        env_file, label, galileo_env = ENVS[t]
        print(f"\n{'='*60}")
        print(f"  ENV {label}")
        print(f"{'='*60}")
        if t == "a":
            cmd = [sys.executable, str(RUNNER_GALILEO)]
        else:
            cmd = [sys.executable, str(RUNNER), env_file]
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        if result.returncode != 0:
            print(f"  !! FAILED (exit {result.returncode})")
    print("\nDone — check erden-framework-testing project in AO console.")
