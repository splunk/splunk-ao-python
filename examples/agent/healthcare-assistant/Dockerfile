FROM python:3.12-slim AS builder

WORKDIR /app

RUN pip install uv

COPY requirements.txt /app/
RUN uv pip install --system --no-cache -r requirements.txt

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . /app/

RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app

USER app

EXPOSE 8501

CMD ["streamlit", "run", "app.py"]
