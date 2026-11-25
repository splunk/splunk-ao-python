FROM python:3.12-slim

WORKDIR /app

RUN pip install uv --no-cache-dir

# Install splunk-ao from local source (main branch — no unreleased local changes).
# Build context is repo root.
COPY pyproject.toml poetry.lock* README.md /sdk/
COPY src/ /sdk/src/
RUN uv pip install --system --no-cache /sdk

# Install example dependencies, pinning splunk-ao to the local version above.
COPY examples/agent/healthcare-assistant/requirements.txt /app/
RUN uv pip install --system --no-cache -r requirements.txt --override /dev/stdin <<'EOF'
splunk-ao
EOF

COPY examples/agent/healthcare-assistant/ /app/

RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app

USER app

CMD ["python", "hosted/run_demo_session.py"]
