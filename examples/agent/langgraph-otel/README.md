# LangGraph + OpenTelemetry + Splunk AO Integration

This example demonstrates how to add comprehensive observability to your LangGraph AI workflows using OpenTelemetry and Splunk AO. You'll get detailed traces showing the complete execution flow, LLM calls, token usage, and input/output data.

## What are these tools?

**OpenTelemetry** is an observability framework that creates traces showing what functions ran, their timing, and data flow through your application. **OpenInference** automatically instruments AI frameworks like LangChain and OpenAI. **Splunk AO** provides a sophisticated platform for visualizing and analyzing your AI application traces.

For detailed explanations and advanced patterns, see the [LangGraph OpenTelemetry cookbook](https://agent-observability-docs.splunk.com/cookbooks/features/integrations/langgraph-otel-cookbook)

## Quick start

### Prerequisites

- Python 3.10+
- [UV package manager](https://docs.astral.sh/uv/getting-started/installation/)
- [Splunk AO account](https://app.galileo.ai) (free)
- OpenAI API key

### Installation

```bash
# Clone and navigate
git clone https://github.com/rungalileo/sdk-examples
cd sdk-examples/python/agent/langgraph-otel

# Install dependencies
uv sync

# Create environment file
cp .env.example .env
# Edit .env with your API keys (see below)
```

### Environment variables

Create a `.env` file in the project root with the following variables:

```bash
# Your Splunk AO API key (get from https://app.galileo.ai/settings/api-keys)
SPLUNK_AO_API_KEY=your_splunk_ao_api_key_here

# Your Splunk AO project name
SPLUNK_AO_PROJECT=your_project_name

# Log stream for organizing traces
SPLUNK_AO_AGENT_STREAM=langgraph

# Splunk AO console URL (if using a custom deployment is different than https://app.galileo.ai)
SPLUNK_AO_CONSOLE_URL=https://app.galileo.ai

# Your OpenAI API key
OPENAI_API_KEY=your_openai_api_key_here
```

| Variable             | Required | Description                                                                    |
| -------------------- | -------- | ------------------------------------------------------------------------------ |
| `SPLUNK_AO_API_KEY`    | Yes      | Your Splunk AO API key from [settings](https://app.galileo.ai/settings/api-keys) |
| `SPLUNK_AO_PROJECT`    | Yes      | Splunk AO project name (create one in your dashboard)                            |
| `SPLUNK_AO_AGENT_STREAM` | Yes      | Log stream name for organizing traces (default: "default")                     |
| `OPENAI_API_KEY`     | Yes      | Your OpenAI API key from [OpenAI](https://platform.openai.com/api-keys)        |

### Run

```bash
uv run python main.py
```

This runs a question-answering LangGraph workflow with comprehensive OpenTelemetry tracing. Check your Splunk AO project for detailed traces!

## Workflow Overview

The example implements a 3-step question-answering workflow:

1. **Input Validation** (`validate_input`) - Validates and prepares the user's question
2. **Response Generation** (`generate_response`) - Calls OpenAI GPT-3.5 to generate an answer
3. **Answer Formatting** (`format_answer`) - Extracts and formats the final answer

### Trace Hierarchy

In Splunk AO, you'll see a clean trace structure:

```
└── astronomy_qa_session [Question → Final Answer]
    ├── LangGraph [Workflow execution]
    │   ├── validate_input [Input validation]
    │   ├── generate_response [LLM processing]
    │   └── format_answer [Answer formatting]
    └── gpt-3.5-turbo-0125 [Detailed OpenAI API call]
        ├── Token usage (prompt/completion/total)
        ├── Model parameters (temperature, max_tokens)
        └── Input/output messages
```

### Key Observability Benefits

- **Complete Input/Output Visibility** - See data flowing through each step
- **LLM Call Details** - Token usage, model parameters, and timing
- **Session Context** - Grouped operations with meaningful metadata
- **Error Tracking** - Automatic error capture and status tracking
- **Performance Insights** - Timing for each workflow step

### Trace Attributes

Each span includes rich metadata:

- **Session Level**: Question, answer, domain (astronomy), type (Q&A)
- **Node Level**: Input/output values, node type, processing details
- **LLM Level**: Model name, tokens, temperature, messages, vendor

## What's included

- **`main.py`** - Complete LangGraph workflow with OpenTelemetry tracing
- **`pyproject.toml`** - All dependencies managed via UV
- **`.env`** - Environment variables (you'll need to add your API keys)
- **`README.md`** - This comprehensive guide

## Learn more

- [LangGraph OpenTelemetry cookbook](https://agent-observability-docs.splunk.com/cookbooks/features/integrations/langgraph-otel-cookbook)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [Splunk AO Documentation](https://agent-observability-docs.splunk.com/)
- [UV Package Manager](https://docs.astral.sh/uv/)
