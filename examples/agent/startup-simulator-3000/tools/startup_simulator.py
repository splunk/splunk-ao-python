import os
import json
from splunk_ao.openai import (
    openai,
)  # 🔍 Splunk AO-wrapped OpenAI client for automatic logging
from agent_framework.tools.base import BaseTool
from agent_framework.models import ToolMetadata
from agent_framework.utils.logging import (
    get_splunk_ao_logger,
)  # 🔍 Splunk AO helper import - gets centralized logger
import asyncio
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# 👀 SPLUNK AO-WRAPPED OPENAI CLIENT: Use Splunk AO's OpenAI wrapper for automatic LLM logging
# This automatically logs all OpenAI API calls to Splunk AO with detailed metrics
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


class StartupSimulatorTool(BaseTool):
    """Tool for generating a silly startup pitch using OpenAI's API"""

    def __init__(self):
        super().__init__()
        self.name = "startup_simulator"
        self.description = "Generate a creative startup pitch based on industry, audience, and a random word"
        # 👀 SPLUNK AO INITIALIZATION: Get the centralized Splunk AO logger instance
        # This ensures all tools use the same Splunk AO configuration and connection
        self.splunk_ao_logger = get_splunk_ao_logger()

    @classmethod
    def get_metadata(cls) -> ToolMetadata:
        return ToolMetadata(
            name="startup_simulator",
            description="Generates a silly startup pitch using OpenAI's API, based on user input.",
            tags=["startup", "generator", "openai", "fun"],
            input_schema={
                "type": "object",
                "properties": {
                    "industry": {
                        "type": "string",
                        "description": "Industry for the startup",
                    },
                    "audience": {"type": "string", "description": "Target audience"},
                    "random_word": {
                        "type": "string",
                        "description": "A random word to include",
                    },
                    "hn_context": {
                        "type": "string",
                        "description": "Recent HackerNews context for inspiration",
                    },
                },
                "required": ["industry", "audience", "random_word"],
            },
            output_schema={
                "type": "string",
                "description": "JSON string containing silly startup pitch data with metadata",
            },
        )

    async def execute(self, industry: str, audience: str, random_word: str, hn_context: str = "") -> str:
        """Execute the startup simulator tool with individual Splunk AO trace"""

        # Log inputs as JSON
        inputs = {
            "industry": industry,
            "audience": audience,
            "random_word": random_word,
            "hn_context": (hn_context[:200] + "..." if len(hn_context) > 200 else hn_context),
            "mode": "silly",
        }
        print(f"Startup Simulator Inputs: {json.dumps(inputs, indent=2)}")

        # 👀 SPLUNK AO LOGGER SETUP: Get the Splunk AO logger for this execution
        # This logger will be used to create traces and spans for observability
        logger = self.splunk_ao_logger
        if not logger:
            print("⚠️  Warning: Splunk AO logger not available, proceeding without logging")
            # ℹ️ FALLBACK: If Splunk AO is not available, use the non-logging version
            return await self._execute_without_splunk_ao(industry, audience, random_word, hn_context)

        # 👀 SPLUNK AO TRACE START: Create a new trace for this tool execution
        # A trace represents the entire lifecycle of this tool call
        # This will appear as a top-level trace in your Splunk AO dashboard
        logger.start_trace(f"Startup Simulator - {industry} targeting {audience}")

        try:
            # 👀 SPLUNK AO SPAN START: Add an LLM span to mark the beginning of tool execution
            # This span shows when the tool started working and what inputs it received
            logger.add_llm_span(
                input=f"Generate startup pitch for {industry} targeting {audience} with word '{random_word}'",
                output="Tool execution started",
                model="startup_simulator",
                num_input_tokens=len(str(inputs)),
                num_output_tokens=0,
                total_tokens=len(str(inputs)),
                duration_ns=0,
            )

            # Create the prompt with HackerNews context
            hn_context_prompt = ""
            if hn_context:
                hn_context_prompt = f"\n\nUse these recent HackerNews stories for inspiration:\n{hn_context}"

            prompt = (
                f"Generate a creative and engaging startup pitch for a {industry} company "
                f"targeting {audience}. The pitch must include the word '{random_word}' naturally. "
                f"Make it fun, innovative, and memorable. Keep it under 500 characters total."
                f"{hn_context_prompt}"
            )

            # Create messages with Splunk AO context
            messages = [{"role": "user", "content": prompt}]

            # 👀 SPLUNK AO-ENHANCED API CALL: Execute the API call using Splunk AO-wrapped OpenAI client
            # This automatically logs the LLM call to Splunk AO with detailed metrics
            # You'll see input/output tokens, model used, and response in your Splunk AO dashboard
            response = client.chat.completions.create(messages=messages, model="gpt-4")

            # Extract the response
            pitch = response.choices[0].message.content.strip()

            # Create structured output
            output = {
                "pitch": pitch,
                "character_count": len(pitch),
                "mode": "silly",
                "hn_context_used": bool(hn_context),
                "timestamp": datetime.now().isoformat(),
                "model": "gpt-4",
                "input_tokens": (response.usage.prompt_tokens if hasattr(response.usage, "prompt_tokens") else 0),
                "output_tokens": (response.usage.completion_tokens if hasattr(response.usage, "completion_tokens") else 0),
                "total_tokens": (response.usage.total_tokens if hasattr(response.usage, "total_tokens") else 0),
            }

            # Log output as JSON to console and for Splunk AO observability
            output_log = {
                "tool_execution": "startup_simulator",
                "inputs": inputs,
                "output": output,
                "metadata": {
                    "character_count": output["character_count"],
                    "mode": output["mode"],
                    "hn_context_used": output["hn_context_used"],
                    "timestamp": output["timestamp"],
                },
            }
            print(f"Startup Simulator Output: {json.dumps(output_log, indent=2)}")

            # 👀 SPLUNK AO SPAN COMPLETION: Add an LLM span to mark successful completion
            # This span shows the final output and completion status
            # It includes token counts and the actual result for observability
            logger.add_llm_span(
                input="Startup pitch generation completed",
                output=pitch,
                model="gpt-4",
                num_input_tokens=output["input_tokens"],
                num_output_tokens=output["output_tokens"],
                total_tokens=output["total_tokens"],
                duration_ns=0,
            )

            # 👀 SPLUNK AO TRACE CONCLUSION: Successfully conclude the trace
            # This marks the trace as completed successfully in Splunk AO
            # The trace will show as "success" in your dashboard
            logger.conclude(output=pitch, duration_ns=0)
            logger.flush()

            # Return JSON string for proper Splunk AO logging display
            splunk_ao_output = {
                "tool_result": "startup_simulator",
                "formatted_output": json.dumps(output, indent=2),
                "pitch": output["pitch"],
                "metadata": output,
            }

            # Return as formatted JSON string for Splunk AO
            return json.dumps(splunk_ao_output, indent=2)

        except Exception as e:
            # 👀 SPLUNK AO ERROR HANDLING: Conclude the trace with error status
            # This marks the trace as failed in Splunk AO and includes the error message
            # The trace will show as "error" in your dashboard with error details
            if logger:
                logger.conclude(output=str(e), duration_ns=0, error=True)
                logger.flush()

            raise e

    async def _execute_without_splunk_ao(self, industry: str, audience: str, random_word: str, hn_context: str = "") -> str:
        """Fallback execution without Splunk AO logging"""
        # ℹ️ FALLBACK METHOD: This method runs when Splunk AO is not available
        # It performs the same functionality but without any observability logging
        # Create the prompt with HackerNews context
        hn_context_prompt = ""
        if hn_context:
            hn_context_prompt = f"\n\nUse these recent HackerNews stories for inspiration:\n{hn_context}"

        prompt = (
            f"Generate a creative and engaging startup pitch for a {industry} company "
            f"targeting {audience}. The pitch must include the word '{random_word}' naturally. "
            f"Make it fun, innovative, and memorable. Keep it under 500 characters total."
            f"{hn_context_prompt}"
        )

        # Create messages
        messages = [{"role": "user", "content": prompt}]

        # Execute the API call
        response = client.chat.completions.create(messages=messages, model="gpt-4")

        # Extract the response
        pitch = response.choices[0].message.content.strip()

        # Create structured output
        output = {
            "pitch": pitch,
            "character_count": len(pitch),
            "mode": "silly",
            "hn_context_used": bool(hn_context),
            "timestamp": datetime.now().isoformat(),
            "model": "gpt-4",
            "input_tokens": (response.usage.prompt_tokens if hasattr(response.usage, "prompt_tokens") else 0),
            "output_tokens": (response.usage.completion_tokens if hasattr(response.usage, "completion_tokens") else 0),
            "total_tokens": (response.usage.total_tokens if hasattr(response.usage, "total_tokens") else 0),
        }

        # Return JSON string for proper Splunk AO logging display
        splunk_ao_output = {
            "tool_result": "startup_simulator",
            "formatted_output": json.dumps(output, indent=2),
            "pitch": output["pitch"],
            "metadata": output,
        }

        return json.dumps(splunk_ao_output, indent=2)


# ℹ️ TEST FUNCTION: This function can be used to test the tool independently
async def main():
    """Test the Startup Simulator tool"""
    tool = StartupSimulatorTool()
    result = await tool.execute(
        industry="Tech",
        audience="Developers",
        random_word="blockchain",
        hn_context="Sample HN context for testing",
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
