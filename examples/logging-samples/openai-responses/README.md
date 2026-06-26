# Log OpenAI Responses API calls with tool use

This is an example project demonstrating how to use Splunk AO to log [OpenAI Responses API](https://platform.openai.com/docs/api-reference/responses) calls, including multi-turn tool calling. The example uses Splunk AO's wrapped OpenAI client to automatically instrument and log all API interactions.

The example defines two simulated tools (`get_weather` and `get_stock_price`), sends a user query that triggers both tool calls, executes the functions locally, and feeds the results back to the model for a final response.

## Getting Started

To get started with this project, you'll need to have Python 3.12 or later installed. You can then install the required dependencies in a virtual environment:

```bash
pip install -r requirements.txt 
```

Or, if you're using [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

You will also need an [OpenAI API key](https://platform.openai.com/api-keys).

## Configure environment variables

You will need to configure the following environment variables:

```ini
# Your Splunk AO API key
SPLUNK_AO_API_KEY="your-splunk-ao-api-key"

# Your Splunk AO project name
SPLUNK_AO_PROJECT="your-splunk-ao-project-name"

# The name of the Log stream you want to use for logging
SPLUNK_AO_LOG_STREAM="your-splunk-ao-log-stream"

# Provide the console url below if you are using a
# custom deployment, and not using the free tier, or app.galileo.ai.
# This will look something like "console.galileo.yourcompany.com".
# SPLUNK_AO_CONSOLE_URL="your-splunk-ao-console-url"

# OpenAI properties
OPENAI_API_KEY="your-openai-api-key"
```

## Usage

Once the dependencies are installed, you can run the example application:

```bash
python main.py
```

The application will send a query asking about the weather in San Francisco and the stock price of Apple. It will:

1. Call the OpenAI Responses API with the defined tools.
2. Parse the function calls returned by the model.
3. Execute the simulated `get_weather` and `get_stock_price` functions.
4. Send the tool results back to the model for a final natural language response.

All API calls are automatically logged to Splunk AO via the wrapped OpenAI client (`from splunk_ao import openai`).

## Project Structure

The project structure is as follows:

```folder
openai-responses/
├── main.py            # The main application file
├── pyproject.toml     # Python project configuration and dependencies
├── .python-version    # Python version specification
└── README.md          # Project documentation
```
