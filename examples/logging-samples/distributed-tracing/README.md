# Splunk AO Distributed Tracing - Decorator Example

This example demonstrates distributed tracing across two services using Splunk AO's `@log` decorator.

## Architecture

- **Retrieval Service** (`retrieval_service.py`): A FastAPI service running on port 8000 that handles information retrieval
- **Orchestrator Service** (`main_run.py`): The main client that coordinates the RAG pipeline by calling the retrieval service

## Setup Instructions

### 1. Create and Activate Virtual Environment

```bash
# Navigate to the distributed-tracing example directory
cd python/logging-samples/distributed-tracing

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate 
```

### 2. Install Dependencies
Run

```bash
pip install -r requirements.txt
```



### 3. Configure Environment Variables
Your `.env` should look like this. Feel free to follow the `.env.example` and enter your credentials
```bash

# Required: Your Splunk AO API key
SPLUNK_AO_API_KEY="your-splunk-ao-api-key"

# Required: OpenAI API key
OPENAI_API_KEY="your-openai-api-key"

# Required: Enable distributed mode for distributed tracing
SPLUNK_AO_MODE=distributed

# Optional: Splunk AO project and log stream names
SPLUNK_AO_PROJECT="your-splunk-ao-project"
SPLUNK_AO_LOG_STREAM=distributed-tracing-example

# Provide the console url below if you are not using app.galileo.ai
# SPLUNK_AO_CONSOLE_URL="your-splunk-ao-console-url"
```

### 4. Run the Services

You need to run both services in **separate terminal processes**.

#### Terminal 1: Start the Retrieval Service

```bash
# Make sure you're in the distributed-tracing example directory
# cd python/logging-samples/distributed-tracing

# Activate venv (if not already activated)
# source venv/bin/activate

# Start the retrieval service on port 8000
uvicorn retrieval_service:app --reload --port 8000
```

You should see output like:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

#### Terminal 2: Run the Orchestrator

```bash
# In a NEW terminal, navigate to the distributed-tracing example directory
cd python/logging-samples/distributed-tracing

# Activate venv
source venv/bin/activate

# Run the orchestrator
python main_run.py
```

## Expected Output

When you run the orchestrator, you should see:

```
============================================================
Question: What did Galileo Galilei research?
============================================================
Answer: Galileo Galilei made scientific observations that transformed our understanding of the universe.
```