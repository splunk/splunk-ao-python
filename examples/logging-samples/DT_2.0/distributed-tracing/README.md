## Configure

Copy `.env.example` to `.env` and set the credentials and project and agentstream.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

Start the retrieval service in one terminal:
```bash
uvicorn retrieval_service:app --reload --port 8000
```

Run the orchestrator in another:
```bash
python main_run.py
```

Each top level `orchestrator_agent()` call creates an independent trace. Its
outbound request carries the active orchestrator workflow span ID, and the
retrieval endpoint's workflow becomes its direct downstream child.
