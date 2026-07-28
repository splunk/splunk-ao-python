# Strands Agents + OpenTelemetry Example Project

This is an example project demonstrating how to use Splunk AO with the [Strands Agent SDK](https://strandsagents.com/latest/), using AWS Bedrock as the LLM provider. This uses the simple [quickstart from the Strands Agents documentation](https://strandsagents.com/latest/documentation/docs/user-guide/quickstart/), and adds Splunk AO logging.

## Getting Started

To get started with this project, you'll need to have Python 3.10 or later installed. You can then install the required dependencies in a virtual environment:

```bash
pip install -r requirements.txt
```

## Configure environment variables

You will need to configure environment variables to use this project. Copy the `.env.example` file to `.env`, then update the environment variables in the `.env` file with your AWS and Splunk AO values:

```ini
# AWS environment variables
AWS_BEARER_TOKEN_BEDROCK=

# Splunk AO environment variables
# SPLUNK_AO_API_ENDPOINT=    # Optional, only set this if you are using a custom Splunk AO deployment
SPLUNK_AO_API_KEY=
SPLUNK_AO_PROJECT=
SPLUNK_AO_AGENT_STREAM=
```

For the `SPLUNK_AO_API_ENDPOINT`, you only need to set this if you are using a custom Splunk AO deployment. There is no need to set this if you ae using [app.galileo.ai](https://app.galileo.ai). This endpoint is different to the console URL that you would normally use. See the [Splunk AO OpenTelemetry documentation](https://agent-observability-docs.splunk.com/sdk-api/third-party-integrations/opentelemetry-and-openinference#self-hosted-deployments) for more details.

## Usage

Once the dependencies are installed, you can run the example application:

```bash
python agent.py
```

Traces will be captured and logged to Splunk AO.

## Project Structure

The project structure is as follows:

```folder
strands-agents/
├─ env.example         # List of environment variables
├── agent.py           # The main agent application
├── requirements.txt   # Python project requirements
└── README.md          # Project documentation
```
