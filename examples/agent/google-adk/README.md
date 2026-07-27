# Google ADK + OpenTelemetry Example Project

This is an example project demonstrating how to use Splunk AO with the Google ADK. This uses the simple [quickstart from the Google ADK documentation](https://google.github.io/adk-docs/get-started/python/#create-an-agent-project), and adds Splunk AO logging.

## Getting Started

To get started with this project, you'll need to have Python 3.10 or later installed. You can then install the required dependencies in a virtual environment:

```bash
pip install -r requirements.txt
```

## Configure environment variables

You will need to configure environment variables to use this project. Copy the `.env.example` file to `.env`, then update the environment variables in the `.env` file with your Google and Splunk AO values:

```ini
# Gemini environment variables
GOOGLE_GENAI_USE_VERTEXAI=0
GOOGLE_API_KEY=

# Splunk AO environment variables
SPLUNK_AO_API_ENDPOINT=
SPLUNK_AO_API_KEY=
SPLUNK_AO_PROJECT=
SPLUNK_AO_AGENT_STREAM=
```

For the `SPLUNK_AO_API_ENDPOINT`, this is different to the console URL that you would normally use. If you are using `app.galileo.ai` for example, the endpoint is `https://api.galileo.ai/otel/v1/traces`.

See the [Splunk AO OTel and OpenInference documentation](https://docs.galileo.ai/sdk-api/third-party-integrations/opentelemetry-and-openinference) for more details.

## Usage

Once the dependencies are installed, you can run the example application using the `adk` command:

```bash
adk run my_agent
```

Traces will be captured and logged to Splunk AO.

## Project Structure

The project structure is as follows:

```folder
google-adk/
├── my_agent/          # The main agent application
│   ├── __init__.py
│   ├── agent.py
│   └── env.example    # List of environment variables
├── requirements.txt   # Python project requirements
└── README.md          # Project documentation
```
