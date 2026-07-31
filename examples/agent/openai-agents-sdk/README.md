# OpenAI Agents SDK — Splunk AO Trace Processor

Demonstrates how to integrate `splunk-ao` with the [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) using `SplunkAOTracingProcessor`.

The processor registers with the agents runtime via `set_trace_processors()`. It receives every `Trace` and `Span` event (agent runs, LLM calls, tool calls, handoffs) and logs them hierarchically to Splunk AO — no additional instrumentation code needed in the agent itself.

The example defines a `FinanceWeatherAgent` with two tools (`get_weather`, `get_stock_price`) and runs a single query that triggers both.

## Setup

```bash
cp .env.example .env
# fill in SPLUNK_AO_API_KEY, SPLUNK_AO_PROJECT, SPLUNK_AO_AGENT_STREAM, OPENAI_API_KEY

pip install -e .
# or: uv sync
```

## Run

```bash
python main.py
```

## What to expect in Splunk AO

- **Agent span** wrapping the full run (`FinanceWeatherAgent`)
- **LLM span** for the initial tool-selection call
- **Tool call spans** for `get_weather` and `get_stock_price`
- **LLM span** for the final answer generation

## Reference SDK (galileo-python)

Swap one import to run the same example against `galileo-python`:

```python
# from splunk_ao.handlers.openai_agents import SplunkAOTracingProcessor
from galileo.handlers.openai_agents import GalileoTracingProcessor
set_trace_processors([GalileoTracingProcessor()])
```
