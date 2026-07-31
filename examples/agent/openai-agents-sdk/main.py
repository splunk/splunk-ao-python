import asyncio
import json
from random import randint

from agents import Agent, Runner, function_tool, set_trace_processors
from dotenv import load_dotenv

from splunk_ao.handlers.openai_agents import SplunkAOTracingProcessor

load_dotenv()

# Register Splunk AO as the trace processor for the OpenAI Agents SDK.
# The processor receives every Trace and Span event from the agents runtime
# and logs them hierarchically to Splunk AO.
set_trace_processors([SplunkAOTracingProcessor()])


@function_tool
def get_weather(location: str) -> str:
    """Get the current weather for a given location."""
    conditions = ["sunny", "cloudy", "rainy", "windy"]
    temp = randint(10, 35)
    return json.dumps({"location": location, "condition": conditions[randint(0, 3)], "temperature_c": temp})


@function_tool
def get_stock_price(symbol: str) -> str:
    """Get the current stock price for a given ticker symbol."""
    prices = {"AAPL": 178.50, "GOOGL": 141.25, "MSFT": 378.90, "AMZN": 153.40}
    price = prices.get(symbol.upper(), 100.00)
    return json.dumps({"symbol": symbol.upper(), "price": price, "currency": "USD"})


agent = Agent(
    name="FinanceWeatherAgent",
    instructions=(
        "You are a helpful assistant. "
        "Use get_weather to answer weather questions and get_stock_price for stock questions."
    ),
    tools=[get_weather, get_stock_price],
)


async def main() -> None:
    result = await Runner.run(
        agent,
        "What's the weather in Tokyo and what's Apple's current stock price?",
    )
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
