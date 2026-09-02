## Configure

Copy `.env.example` to `.env` and set the credentials and project and agentstream.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Start the retrieval service:
```bash
uvicorn retrieval_service:app --port 8000
```

Then run the orchestrator:
```bash
python main_run.py
```

### Observe batching before the root ends

To demonstrate incremental export, add these values to an existing `.env`:

```dotenv
OTEL_BSP_SCHEDULE_DELAY="1000"
BATCH_DEMO_SLEEP_SECONDS="20"
```

`OTEL_BSP_SCHEDULE_DELAY` is in milliseconds and is read when each batch span
processor is created. After the distributed retrieval call returns, the example
prints a batching-demo message and keeps the orchestrator root active for 20
seconds.

Set`BATCH_DEMO_SLEEP_SECONDS="0"` to disable the pause.

The local tree remains the same as the baseline. Completed children enter the
batch processor at their own end callbacks, so no per-trace flush is needed.
