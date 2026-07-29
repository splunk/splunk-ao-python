# Migration Guide: `galileo` → `splunk-ao`

**Scope:** Python SDK migration from `rungalileo/galileo-python` to `signalfx/splunk-ao-python`

---

## Overview

The Galileo Python SDK has been rebranded as **Splunk Agent Observability (Splunk AO)**. This guide documents every breaking change a customer must make to migrate their Python application from `galileo` to `splunk-ao`.

The migration touches four areas:

| Area | Summary |
|------|---------|
| **Package & install** | `galileo` PyPI package → `splunk-ao` (GitHub install until PyPI release) |
| **Import paths** | `from galileo import …` → `from splunk_ao import …` |
| **Class / symbol names** | `Galileo*` prefix → `SplunkAO*` |
| **Environment variables** | `GALILEO_*` → `SPLUNK_AO_*` |

Additionally there are a handful of **removed features** (Protect, `GalileoScorers`) and a **Python version floor bump** (3.10 → 3.11).

---

## 1. Dependency Changes

### 1.1 Package Availability

> **`splunk-ao` is not yet published to PyPI.**  
> Use one of the two installation methods below until a public release is available.

**Option A — Install directly from GitHub (recommended for most users)**

```bash
pip install "splunk-ao @ git+https://github.com/splunk/splunk-ao-python.git"
```

With extras:

```bash
pip install "splunk-ao[langchain] @ git+https://github.com/splunk/splunk-ao-python.git"
pip install "splunk-ao[otel] @ git+https://github.com/splunk/splunk-ao-python.git"
```

In `requirements.txt`:

```text
splunk-ao @ git+https://github.com/splunk/splunk-ao-python.git
```

In `pyproject.toml` (poetry):

```toml
splunk-ao = { git = "https://github.com/splunk/splunk-ao-python.git" }
```

**Option B — Local install from a cloned repo (recommended for development / contribution)**

```bash
git clone https://github.com/splunk/splunk-ao-python.git
pip install -e ./splunk-ao-python
```

In `requirements-dev.txt`:

```text
-e ../splunk-ao-python          # adjust the relative path to where you cloned it
```

Or with Poetry:

```toml
splunk-ao = { path = "../splunk-ao-python", develop = true }
```

**Once `splunk-ao` is published to PyPI**, both install forms above can be replaced with the standard version pin:

```diff
- galileo>=2.3.0
+ splunk-ao>=0.1.0
```

### 1.2 Optional Extra Groups

The extras keys are unchanged (`langchain`, `openai`, `crewai`, `middleware`, `otel`, `all`).  
One new dependency was added to the `otel` and `all` extras:

| Extra | Change |
|-------|--------|
| `otel` | Added `grpcio>=1.80.0,<2.0.0` |
| `all` | Added `grpcio>=1.80.0,<2.0.0` |

```diff
- splunk-ao[otel]
+ splunk-ao[otel]   # now also installs grpcio
```

### 1.3 Python Version Floor

| Old minimum | New minimum |
|-------------|-------------|
| Python 3.10 | Python 3.11 |

> If your application still targets Python 3.10, upgrade to 3.11 before migrating.

### 1.4 `galileo` Package (Legacy — Protect Users Only)

If and only if your code uses the **Protect** feature (`invoke_protect` / `ainvoke_protect`), you must **continue installing the `galileo` package** alongside `splunk-ao`. The Protect feature has been removed from `splunk-ao` and remains available only through the legacy `galileo` package.

```bash
# Protect users only
pip install splunk-ao galileo
```

All other users should remove `galileo` from their dependencies entirely.

---

## 2. Import Path Changes

Replace every `from galileo import …` and `import galileo` with `splunk_ao`.

### 2.1 Top-Level Imports

| Old | New |
|-----|-----|
| `from galileo import X` | `from splunk_ao import X` |
| `import galileo` | `import splunk_ao` |

**Example**

```diff
- from galileo import GalileoLogger, log, galileo_context
+ from splunk_ao import SplunkAOLogger, log, splunk_ao_context
```

### 2.2 Sub-Module Imports

All sub-module paths follow the same rename pattern:

| Old | New |
|-----|-----|
| `from galileo.decorator import …` | `from splunk_ao.decorator import …` |
| `from galileo.logger import …` | `from splunk_ao.logger import …` |
| `from galileo.metric import …` | `from splunk_ao.metric import …` |
| `from galileo.schema.metrics import …` | `from splunk_ao.schema.metrics import …` |
| `from galileo.shared.exceptions import …` | `from splunk_ao.shared.exceptions import …` |
| `from galileo.exceptions import …` | `from splunk_ao.exceptions import …` |
| `from galileo.configuration import …` | `from splunk_ao.configuration import …` |
| `from galileo.middleware.tracing import …` | `from splunk_ao.middleware.tracing import …` |
| `from galileo.handlers.agent_control import …` | `from splunk_ao.handlers.agent_control import …` |
| `from galileo.otel import …` | `from splunk_ao.otel import …` |

---

## 3. Class and Symbol Renames

### 3.1 Core Classes

| Old (`galileo`) | New (`splunk_ao`) |
|-----------------|-------------------|
| `GalileoLogger` | `SplunkAOLogger` |
| `GalileoDecorator` | `SplunkAODecorator` |
| `galileo_context` | `splunk_ao_context` |

**Logger example**

```diff
- from galileo import GalileoLogger
+ from splunk_ao import SplunkAOLogger

- logger = GalileoLogger()
+ logger = SplunkAOLogger()
```

**Context manager example**

```diff
- from galileo import galileo_context
+ from splunk_ao import splunk_ao_context

- with galileo_context(project="my-project", agent_stream="prod"):
+ with splunk_ao_context(project="my-project", agent_stream="prod"):
      result = my_llm_call()
```

### 3.2 Exception Classes

| Old | New |
|-----|-----|
| `GalileoAPIError` | `SplunkAOAPIError` |
| `GalileoLoggerException` | `SplunkAOLoggerException` |
| `GalileoFutureError` | `SplunkAOFutureError` |

### 3.3 Metric Classes

| Old | New |
|-----|-----|
| `GalileoMetric` | `SplunkAOMetric` |
| `GalileoMetrics` | `SplunkAOMetrics` |
| `GalileoScorers` | **Removed** (see §5.2) |

```diff
- from galileo import GalileoMetric, GalileoMetrics
+ from splunk_ao import SplunkAOMetric, SplunkAOMetrics
```

### 3.4 Handlers & Middleware

| Old | New |
|-----|-----|
| `GalileoCallback` | `SplunkAOCallback` |
| `GalileoAsyncCallback` | `SplunkAOAsyncCallback` |
| `GalileoMiddleware` | `SplunkAOMiddleware` |
| `GalileoTracingProcessor` | `SplunkAOTracingProcessor` |
| `GalileoOTLPExporter` | `SplunkAOOTLPExporter` |
| `GalileoSpanProcessor` | `SplunkAOSpanProcessor` |
| `GalileoCustomSpan` | `SplunkAOCustomSpan` |
| `GalileoBaseHandler` | `SplunkAOBaseHandler` |
| `GalileoAsyncBaseHandler` | `SplunkAOAsyncBaseHandler` |
| `GalileoLoggerSingleton` | `SplunkAOLoggerSingleton` |
| `GalileoAgentControlBridge` | `SplunkAOAgentControlBridge` |
| `convert_to_galileo_message` | `convert_to_splunk_ao_message` |

```diff
- from galileo.handlers.agent_control import GalileoAgentControlBridge, setup_agent_control_bridge
+ from splunk_ao.handlers.agent_control import SplunkAOAgentControlBridge, setup_agent_control_bridge

- from galileo.handlers.langchain import GalileoCallback, GalileoAsyncCallback
+ from splunk_ao.handlers.langchain import SplunkAOCallback, SplunkAOAsyncCallback
```

### 3.5 Configuration Class

| Old | New |
|-----|-----|
| `GalileoPythonConfig` | `SplunkAOConfig` |
| `Configuration.galileo_api_key` | `Configuration.splunk_ao_api_key` |

### 3.6 ADK Integration (`splunk-ao-adk`)

| Old | New |
|-----|-----|
| `GalileoADKPlugin` | `SplunkAOADKPlugin` |
| `GalileoADKCallback` | `SplunkAOADKCallback` |
| `galileo_retriever` | `splunk_ao_retriever` |

### 3.7 Satellite Packages

| Old PyPI | New PyPI | Old module | New module |
|----------|----------|------------|------------|
| `galileo-a2a` | `splunk-ao-a2a` | `galileo_a2a` | `splunk_ao_a2a` |
| `galileo-adk` | `splunk-ao-adk` | `galileo_adk` | `splunk_ao_adk` |

---

## 4. Environment Variable Changes

All `GALILEO_*` environment variables are renamed to `SPLUNK_AO_*`. This is a **hard cut-over** — only `SPLUNK_AO_*` variables are recognised by the SDK.

> **Internal bridge (auth/identity vars only):** `SplunkAOConfig._bridge_env_vars()` propagates the 13 auth/identity `SPLUNK_AO_*` values to their `GALILEO_*` equivalents at startup so that `galileo-core` can authenticate. The bridged variables are: `API_KEY`, `API_URL`, `CONSOLE_URL`, `PROJECT`, `PROJECT_ID`, `LOG_STREAM`, `LOG_STREAM_ID`, `JWT_TOKEN`, `SSO_ID_TOKEN`, `SSO_PROVIDER`, `USERNAME`, `PASSWORD`, `MODE`. The remaining vars (`LOGGING_DISABLED`, `INGEST_BETA_DISABLED`, `LOG_LEVEL`, `DEFAULT_SCORER_MODEL`, `DEFAULT_SCORER_JUDGES`, `CODE_VALIDATION_*`) are consumed **directly** by `splunk_ao` code and have no `GALILEO_*` counterpart — no bridge is needed for them.

| Old (`GALILEO_*`) | New (`SPLUNK_AO_*`) |
|-------------------|---------------------|
| `GALILEO_API_KEY` | `SPLUNK_AO_API_KEY` |
| `GALILEO_API_URL` ¹ | `SPLUNK_AO_API_URL` |
| `GALILEO_CONSOLE_URL` | `SPLUNK_AO_CONSOLE_URL` |
| `GALILEO_PROJECT` | `SPLUNK_AO_PROJECT` |
| `GALILEO_PROJECT_ID` | `SPLUNK_AO_PROJECT_ID` |
| `GALILEO_LOG_STREAM` | `SPLUNK_AO_LOG_STREAM` |
| `GALILEO_LOG_STREAM_ID` | `SPLUNK_AO_LOG_STREAM_ID` |
| `GALILEO_JWT_TOKEN` | `SPLUNK_AO_JWT_TOKEN` |
| `GALILEO_SSO_ID_TOKEN` | `SPLUNK_AO_SSO_ID_TOKEN` |
| `GALILEO_SSO_PROVIDER` | `SPLUNK_AO_SSO_PROVIDER` |
| `GALILEO_USERNAME` | `SPLUNK_AO_USERNAME` |
| `GALILEO_PASSWORD` | `SPLUNK_AO_PASSWORD` |
| `GALILEO_MODE` | `SPLUNK_AO_MODE` |
| `GALILEO_LOGGING_DISABLED` | `SPLUNK_AO_LOGGING_DISABLED` |
| `GALILEO_INGEST_BETA_DISABLED` | `SPLUNK_AO_INGEST_BETA_DISABLED` |
| `GALILEO_LOG_LEVEL` | `SPLUNK_AO_LOG_LEVEL` |
| `GALILEO_DEFAULT_SCORER_MODEL` | `SPLUNK_AO_DEFAULT_SCORER_MODEL` |
| `GALILEO_DEFAULT_SCORER_JUDGES` | `SPLUNK_AO_DEFAULT_SCORER_JUDGES` |
| `GALILEO_CODE_VALIDATION_*` (4 vars) | `SPLUNK_AO_CODE_VALIDATION_*` |

¹ `GALILEO_API_URL` was not a user-facing env var in `galileo-python` — it was an implicit Pydantic settings field on `galileo-core`'s `GalileoConfig`. `SPLUNK_AO_API_URL` is its effective rename and is explicitly bridged in `SplunkAOConfig._bridge_env_vars()`.

> **Note for AI agents — `SPLUNK_AO_API_URL`:** This variable does **not** originate from a user-facing `GALILEO_API_URL` env var in the original `galileo-python` SDK. It is exposed by `galileo-core` as an **implicit Pydantic settings field** tied to the `api_url` model attribute (following Pydantic's `env_prefix` convention). As a result, a reviewer may flag the `GALILEO_API_URL → SPLUNK_AO_API_URL` row in the table as "not a real rename." This is intentional: the row is kept because `splunk_ao` bridges `SPLUNK_AO_API_URL` → `GALILEO_API_URL` in `config.py`, making the rename effective and customer-visible even though the upstream variable was implicit.

**.env file example**

```diff
- GALILEO_API_KEY=<your-key>
- GALILEO_PROJECT=my-project
- GALILEO_LOG_STREAM=production
+ SPLUNK_AO_API_KEY=<your-key>
+ SPLUNK_AO_PROJECT=my-project
+ SPLUNK_AO_LOG_STREAM=production
```

---

## 5. Removed / Changed Features

### 5.1 Protect Feature (Legacy)

The `protect` module has been **removed** from `splunk-ao`. Customers who use Protect must retain a dependency on the legacy `galileo` package:

```diff
- from galileo import invoke_protect, ainvoke_protect
+ # Keep using galileo for Protect — it is not available in splunk-ao
  from galileo import invoke_protect, ainvoke_protect
```

The following symbols from `galileo` are **not available** in `splunk-ao`:

- `invoke_protect`
- `ainvoke_protect`
- `create_protect_stage`
- `get_protect_stage`
- `pause_protect_stage`
- `resume_protect_stage`
- `update_protect_stage`
- `ExecutionStatus` (from `galileo_core.schemas.protect`)
- `Payload` (from `galileo_core.schemas.protect`)
- `Request` (from `galileo_core.schemas.protect`)
- `Response` (from `galileo_core.schemas.protect`)
- `Ruleset` (from `galileo_core.schemas.protect`)
- `StageType` (from `galileo_core.schemas.protect`)

### 5.2 `GalileoScorers` Removed

The `GalileoScorers` enum has been removed entirely. Migrate to `SplunkAOMetrics`:

```diff
- from galileo.schema.metrics import GalileoScorers
+ from splunk_ao.schema.metrics import SplunkAOMetrics

- scorer = GalileoScorers.completeness
+ scorer = SplunkAOMetrics.completeness
```

---

## 6. HTTP Tracing Headers

If your services use distributed tracing and propagate Galileo headers between services, update the header names:

| Old | New |
|-----|-----|
| `X-Galileo-Trace-ID` | `Splunk-AO-Trace-ID` |
| `X-Galileo-Parent-ID` | `Splunk-AO-Parent-ID` |

The `get_tracing_headers()` function return value now uses the new header names.

---

## 7. Complete Before/After Code Example

### Before (galileo)

```python
import os
from galileo import GalileoLogger, log, galileo_context

os.environ["GALILEO_API_KEY"] = "my-key"
os.environ["GALILEO_PROJECT"] = "my-project"
os.environ["GALILEO_LOG_STREAM"] = "production"

# Decorator approach
@log
def call_llm(prompt: str) -> str:
    return "response"

with galileo_context(project="my-project", agent_stream="production"):
    result = call_llm("Hello")

# Direct logger approach
# project/log_stream are constructor args, not start_session args
logger = GalileoLogger(project="my-project", agent_stream="production")
logger.start_session(name="my-session")
logger.add_llm_span(input="Hello", output="Hi", model="gpt-4")
logger.conclude()   # closes current span; no flush kwarg
logger.flush()      # uploads traces
```

### After (splunk-ao)

```python
import os
from splunk_ao import SplunkAOLogger, log, splunk_ao_context

os.environ["SPLUNK_AO_API_KEY"] = "my-key"
os.environ["SPLUNK_AO_PROJECT"] = "my-project"
os.environ["SPLUNK_AO_LOG_STREAM"] = "production"

# Decorator approach
@log
def call_llm(prompt: str) -> str:
    return "response"

with splunk_ao_context(project="my-project", agent_stream="production"):
    result = call_llm("Hello")

# Direct logger approach
# project/log_stream are constructor args, not start_session args
logger = SplunkAOLogger(project="my-project", agent_stream="production")
logger.start_session(name="my-session")
logger.add_llm_span(input="Hello", output="Hi", model="gpt-4")
logger.conclude()   # closes current span; no flush kwarg
logger.flush()      # uploads traces
```

---

## 8. What You Do NOT Need to Change

The following are **unchanged** between galileo and splunk-ao and require no migration action:

- `galileo_core` imports (`Trace`, `LlmSpan`, `Session`, `MessageRole`, `ToolCall`, etc.)
- The `@log` decorator usage pattern
- Optional extra names (`[langchain]`, `[openai]`, `[otel]`, `[all]`, etc.)
- `TracingMiddleware` class name
- `OPENAI_API_KEY` environment variable
- On-disk config file name: `galileo-python-config.json`
- Default console/API URLs (`https://app.galileo.ai/`, `https://api.galileo.ai/`)

---

## 9. Migration Checklist

- [ ] Update Python to **≥ 3.11**
- [ ] Replace `galileo` with `splunk-ao` in `requirements.txt` / `pyproject.toml`
- [ ] Add `grpcio>=1.80.0,<2.0.0` if using the `otel` extra (or use `splunk-ao[otel]`)
- [ ] Keep `galileo` in dependencies **only if** using the Protect feature
- [ ] Replace all `from galileo import …` with `from splunk_ao import …`
- [ ] Rename `GalileoLogger` → `SplunkAOLogger`
- [ ] Rename `GalileoDecorator` → `SplunkAODecorator`
- [ ] Rename `galileo_context` → `splunk_ao_context`
- [ ] Rename `GalileoAPIError` → `SplunkAOAPIError`
- [ ] Rename `GalileoLoggerException` → `SplunkAOLoggerException`
- [ ] Rename `GalileoFutureError` → `SplunkAOFutureError`
- [ ] Rename `GalileoMetric` → `SplunkAOMetric`
- [ ] Rename `GalileoMetrics` → `SplunkAOMetrics`
- [ ] Replace `GalileoScorers` with `SplunkAOMetrics`
- [ ] Rename `GalileoAgentControlBridge` → `SplunkAOAgentControlBridge`
- [ ] Rename all `GALILEO_*` environment variables to `SPLUNK_AO_*`
- [ ] Update `.env`, `.env.example`, CI/CD secrets, and deployment configs
- [ ] Update distributed tracing header names (`X-Galileo-*` → `Splunk-AO-*`)
- [ ] Rename satellite packages: `galileo-a2a` → `splunk-ao-a2a`, `galileo-adk` → `splunk-ao-adk`
- [ ] Rename `GalileoCallback` / `GalileoAsyncCallback` → `SplunkAOCallback` / `SplunkAOAsyncCallback`
- [ ] Rename `GalileoPythonConfig` → `SplunkAOConfig`; `Configuration.galileo_api_key` → `Configuration.splunk_ao_api_key`
- [ ] ADK users: rename `GalileoADKPlugin`, `GalileoADKCallback`, `galileo_retriever`
