import json
import aiohttp
from splunk_ao import log  # 🔍 Splunk AO decorator import for tool spans
from agent_framework.tools.base import BaseTool
from agent_framework.models import ToolMetadata
from agent_framework.utils.logging import (
    get_splunk_ao_logger,
)  # 🔍 Splunk AO helper import - gets centralized logger
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()


class HackerNewsTool(BaseTool):
    """Tool for fetching trending stories from HackerNews"""

    def __init__(self):
        super().__init__()
        self.name = "hackernews_tool"
        self.description = "Fetch trending stories from HackerNews for creative inspiration"
        # 👀 SPLUNK AO INITIALIZATION: Get the centralized Splunk AO logger instance
        # This ensures all tools use the same Splunk AO configuration and connection
        self.splunk_ao_logger = get_splunk_ao_logger()

    @classmethod
    def get_metadata(cls) -> ToolMetadata:
        return ToolMetadata(
            name="hackernews_tool",
            description="Fetches trending stories from HackerNews for creative inspiration and context",
            tags=["news", "inspiration", "tech", "trending"],
            input_schema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of stories to fetch",
                        "default": 3,
                    }
                },
                "required": [],
            },
            output_schema={
                "type": "string",
                "description": "JSON string containing HackerNews stories with metadata",
            },
        )

    # 👀 SPLUNK AO TOOL SPAN DECORATOR: This decorator creates a tool span for HTTP API calls
    # Since this tool makes HTTP requests to HackerNews API (not LLM calls), we use span_type="tool"
    # The name "Tool-HackerNews" will appear in your Splunk AO dashboard as a tool span
    @log(span_type="tool", name="Tool-HackerNews")
    async def execute(self, limit: int = 3) -> str:
        """Fetch trending stories from HackerNews"""

        # Log inputs
        inputs = {"limit": limit, "timestamp": datetime.now().isoformat()}
        print(f"HackerNews Tool Inputs: {json.dumps(inputs, indent=2)}")

        # 👀 SPLUNK AO LOGGER SETUP: Get the Splunk AO logger for this execution
        # This logger will be used to create traces and spans for observability
        logger = self.splunk_ao_logger
        if not logger:
            print("⚠️  Warning: Splunk AO logger not available, proceeding without logging")
            # ℹ️ FALLBACK: If Splunk AO is not available, use the non-logging version
            return await self._execute_without_splunk_ao(limit)

        # 👀 SPLUNK AO TRACE START: Create a new trace for this tool execution
        # A trace represents the entire lifecycle of this tool call
        # This will appear as a top-level trace in your Splunk AO dashboard
        logger.start_trace(f"HackerNews Tool - Fetching {limit} stories")

        try:
            # 🔧 TOOL EXECUTION: This tool makes HTTP API calls to HackerNews
            # Since it's not an LLM call, we don't need LLM spans here
            # The @log decorator above automatically creates the tool span

            # Fetch top story IDs
            async with aiohttp.ClientSession() as session:
                async with session.get("https://hacker-news.firebaseio.com/v0/topstories.json") as response:
                    if response.status != 200:
                        raise Exception(f"Failed to fetch top stories: {response.status}")

                    story_ids = await response.json()
                    story_ids = story_ids[:limit]  # Get only the requested number

                    # Fetch individual story details
                    stories = []
                    for story_id in story_ids:
                        async with session.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json") as story_response:
                            if story_response.status == 200:
                                story_data = await story_response.json()
                                if story_data and "title" in story_data:
                                    stories.append(
                                        {
                                            "id": story_data.get("id"),
                                            "title": story_data.get("title"),
                                            "url": story_data.get("url"),
                                            "score": story_data.get("score", 0),
                                            "by": story_data.get("by"),
                                            "time": story_data.get("time"),
                                        }
                                    )

            # Format stories for context
            formatted_stories = []
            for story in stories:
                formatted_stories.append(f"• {story['title']} (Score: {story['score']})")

            context = "\n".join(formatted_stories)

            # Create structured output
            output = {
                "stories": stories,
                "formatted_context": context,
                "story_count": len(stories),
                "requested_limit": limit,
                "timestamp": datetime.now().isoformat(),
                "source": "hackernews",
            }

            # Log output as JSON
            output_log = {
                "tool_execution": "hackernews_tool",
                "inputs": inputs,
                "output": output,
                "metadata": {
                    "story_count": output["story_count"],
                    "requested_limit": output["requested_limit"],
                    "timestamp": output["timestamp"],
                },
            }
            print(f"HackerNews Tool Output: {json.dumps(output_log, indent=2)}")

            # 👀 SPLUNK AO TRACE CONCLUSION: Successfully conclude the trace
            # This marks the trace as completed successfully in Splunk AO
            # The trace will show as "success" in your dashboard
            logger.conclude(output=context, duration_ns=0)
            logger.flush()

            # Return JSON string for proper Splunk AO logging display
            splunk_ao_output = {
                "tool_result": "hackernews_tool",
                "formatted_output": json.dumps(output, indent=2),
                "context": context,
                "metadata": output,
            }

            return json.dumps(splunk_ao_output, indent=2)

        except Exception as e:
            # 👀 SPLUNK AO ERROR HANDLING: Conclude the trace with error status
            # This marks the trace as failed in Splunk AO and includes the error message
            # The trace will show as "error" in your dashboard with error details
            if logger:
                logger.conclude(output=str(e), duration_ns=0, error=True)
                logger.flush()

            raise e

    async def _execute_without_splunk_ao(self, limit: int = 3) -> str:
        """Fallback execution without Splunk AO logging"""
        # ℹ️ FALLBACK METHOD: This method runs when Splunk AO is not available
        # It performs the same functionality but without any observability logging
        # Fetch top story IDs
        async with aiohttp.ClientSession() as session:
            async with session.get("https://hacker-news.firebaseio.com/v0/topstories.json") as response:
                if response.status != 200:
                    raise Exception(f"Failed to fetch top stories: {response.status}")

                story_ids = await response.json()
                story_ids = story_ids[:limit]  # Get only the requested number

                # Fetch individual story details
                stories = []
                for story_id in story_ids:
                    async with session.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json") as story_response:
                        if story_response.status == 200:
                            story_data = await story_response.json()
                            if story_data and "title" in story_data:
                                stories.append(
                                    {
                                        "id": story_data.get("id"),
                                        "title": story_data.get("title"),
                                        "url": story_data.get("url"),
                                        "score": story_data.get("score", 0),
                                        "by": story_data.get("by"),
                                        "time": story_data.get("time"),
                                    }
                                )

        # Format stories for context
        formatted_stories = []
        for story in stories:
            formatted_stories.append(f"• {story['title']} (Score: {story['score']})")

        context = "\n".join(formatted_stories)

        # Create structured output
        output = {
            "stories": stories,
            "formatted_context": context,
            "story_count": len(stories),
            "requested_limit": limit,
            "timestamp": datetime.now().isoformat(),
            "source": "hackernews",
        }

        # Return JSON string for proper Splunk AO logging display
        splunk_ao_output = {
            "tool_result": "hackernews_tool",
            "formatted_output": json.dumps(output, indent=2),
            "context": context,
            "metadata": output,
        }

        return json.dumps(splunk_ao_output, indent=2)


# ℹ️ TEST FUNCTION: This function can be used to test the tool independently
async def main():
    """Test the HackerNews tool"""
    tool = HackerNewsTool()
    result = await tool.execute(limit=3)
    print(f"Result: {result}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
