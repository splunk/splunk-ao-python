"""
aiohttp server entry point for the Microsoft 365 Agents SDK example.

Starts the agent on http://localhost:3978/api/messages.
Test locally with: npx @microsoft/m365agentsplayground
"""

import os

from aiohttp.web import Application, Request, Response, run_app
from dotenv import load_dotenv

load_dotenv()

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
