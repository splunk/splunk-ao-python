# Experiments with RAG and tools

This is an example project demonstrating how to use Splunk AO experiments with applications that use RAG and tools.

This code is used in the [Run an experiment against a RAG app](https://agent-observability-docs.splunk.com/how-to-guides/experiments/rag-and-tools/rag-and-tools) how-to guide in the Splunk AO documentation.

## Get Started

To get started with this project, you'll need to have Python 3.10 or later installed. You can then install the required dependencies in a virtual environment:

```bash
pip install -r requirements.txt
```

## Configure environment variables

Copy `.env.example` to `.env`, choose either the Standalone or O11y block, and update the common OpenAI and Splunk AO
values. Do not mix deployment modes.

```shell
cp .env.example .env
```

O11y requires `SPLUNK_AO_REALM` and `SPLUNK_AO_O11Y_TOKEN` because both scripts emit telemetry. Set
`SPLUNK_AO_O11Y_API_TOKEN` as well when CRUD operations use a dedicated token. Standalone requires
`SPLUNK_AO_API_KEY` and `SPLUNK_AO_CONSOLE_URL`.

## Usage

This sample contains both an application that generates a fake horoscope using a tool and a mock RAG function, as well as an experiment to test the same code.

To run the application, run:

```bash
python app.py
```

Traces will be captured and logged to Splunk AO.

To run the experiment, run:

```bash
python experiment.py
```

A link to the results of the experiment will be written to the console. This is a runner-function experiment: the
horoscope application executes locally, its traces are ingested, and the configured `SplunkAOEvaluators` run in the
Splunk AO platform.

## Project Structure

The project structure is as follows:

```folder
rag-and-tools/
├── .env.example       # Standalone and O11y configuration templates
├── requirements.txt   # Python project requirements
├── app.py             # The main python application
├── experiment.py      # Code to run the main application as an experiment
└── README.md          # Project documentation
```
