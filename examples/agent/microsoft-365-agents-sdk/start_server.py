"""
aiohttp server entry point for the Microsoft 365 Agents SDK example.

Starts the agent on http://localhost:3978/api/messages.
Test locally with: npx @microsoft/m365agentsplayground

APP_MODE=auto        → app_auto.py        (auto-instrumented, local collector)
APP_MODE=manual      → app_manual.py      (manual InferenceScope, local collector)
APP_MODE=auto_lab0   → app_auto_lab0.py   (SplunkAOSpanProcessor, auto-instrumented, lab0/staging)
APP_MODE=manual_lab0 → app_manual_lab0.py (SplunkAOLogger, manual instrumentation, lab0/staging)
APP_MODE=<unset>     → app.py (default)
"""

import os

from aiohttp.web import Application, Request, Response, run_app
from dotenv import load_dotenv

load_dotenv(override=False)

_mode = os.environ.get("APP_MODE", "").lower()
if _mode == "auto":
    from app_auto import ADAPTER, AGENT_APP
elif _mode == "manual":
    from app_manual import ADAPTER, AGENT_APP
elif _mode == "auto_lab0":
    from app_auto_lab0 import ADAPTER, AGENT_APP
elif _mode == "manual_lab0":
    from app_manual_lab0 import ADAPTER, AGENT_APP
else:
    from app import ADAPTER, AGENT_APP

from microsoft_agents.hosting.aiohttp import start_agent_process


async def messages(request: Request) -> Response:
    return await start_agent_process(request, AGENT_APP, ADAPTER)


def main() -> None:
    web_app = Application()
    web_app.router.add_post("/api/messages", messages)

    port = int(os.environ.get("PORT", 3978))
    print(f"Microsoft 365 Agents SDK example running on http://localhost:{port}/api/messages")
    print("Test with: npx @microsoft/m365agentsplayground")
    run_app(web_app, host="localhost", port=port)


if __name__ == "__main__":
    main()
