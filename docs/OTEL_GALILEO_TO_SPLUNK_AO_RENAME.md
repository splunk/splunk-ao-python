# OTel Layer: Galileo → Splunk AO Rename

**Branch:** `rename/galileo-to-splunk-ao`  
**Ticket:** Internal refactor (follow-on to HYBIM-832)

## Summary

This change removes the remaining `galileo` branding from the OpenTelemetry integration layer. All `Galileo`-prefixed symbols, variable names, and OTel attribute values in the OTel module have been renamed to their `SplunkAO` / `splunk-ao` equivalents.

---

## What Changed

### 1. Import alias

| Before | After |
|--------|-------|
| `from galileo_core.schemas.logging.span import Span as GalileoSpan` | `from galileo_core.schemas.logging.span import Span as SplunkAOSpan` |

Affected files:
- `src/splunk_ao/otel.py`
- `src/splunk_ao/handlers/openai_agents/handler.py`
- `src/splunk_ao/utils/openai_agents.py`

### 2. OTel instrumentation scope name

| Before | After |
|--------|-------|
| `tracer_provider.get_tracer("galileo-tracer")` | `tracer_provider.get_tracer("splunk-ao-tracer")` |

This is the **OTel instrumentation scope** name. It appears as `otel.scope.name` / `instrumentation.name` in traces exported to any OTel-compatible backend.

### 3. `gen_ai.system` attribute value

| Before | After |
|--------|-------|
| `span.set_attribute("gen_ai.system", "galileo-otel")` | `span.set_attribute("gen_ai.system", "splunk-ao-otel")` |

This attribute is set on every span emitted by `start_splunk_ao_span()`.

### 4. Internal parameter and variable names

| Before | After | Location |
|--------|-------|----------|
| `galileo_span` (parameter) | `splunk_ao_span` | `otel.py` — `_set_retriever_span_attributes`, `_set_tool_span_attributes`, `_set_workflow_span_attributes` |
| `galileo_span: GalileoSpan` (parameter) | `splunk_ao_span: SplunkAOSpan` | `otel.py` — `start_splunk_ao_span` |
| `galileo_span: GalileoSpan` (parameter) | `span: SplunkAOSpan` | `handler.py` — `add_splunk_ao_custom_span` |
| `span: GalileoSpan` (parameter) | `span: SplunkAOSpan` | `utils/openai_agents.py` — `SplunkAOCustomSpan.__init__` |

### 5. Docstring

| Before | After |
|--------|-------|
| `"""Add a Galileo custom span to the trace."""` | `"""Add a Splunk AO custom span to the trace."""` |

### 6. Example variable names

| Before | After | File |
|--------|-------|------|
| `galileo_span_processor` | `splunk_ao_span_processor` | `examples/agent/google-adk/my_agent/agent.py` |
| `galileo_span_processor` | `splunk_ao_span_processor` | `examples/agent/langgraph-open-telemetry/main.py` |
| `start_galileo_span` | `start_splunk_ao_span` | `examples/rag/cli-rag-demo/python-service/app.py` |

---

## Impact on Users

### Potentially breaking: OTel span attributes

If you have dashboards, alerts, or queries that filter on `gen_ai.system = "galileo-otel"` or `otel.scope.name = "galileo-tracer"` in your observability backend (Splunk, Datadog, Jaeger, etc.), update those filters:

| Attribute | Old value | New value |
|-----------|-----------|-----------|
| `gen_ai.system` | `galileo-otel` | `splunk-ao-otel` |
| `otel.scope.name` / `instrumentation.name` | `galileo-tracer` | `splunk-ao-tracer` |

### Not breaking: Public Python API

The public functions `start_splunk_ao_span()`, `add_splunk_ao_span_processor()`, `SplunkAOSpanProcessor`, and `SplunkAOCustomSpan` are **unchanged**. Only their internal parameter names changed.

### Example code updates

If you copied variable names from the examples (e.g. `galileo_span_processor`), update them to `splunk_ao_span_processor`. These are local variable names with no API contract.

---

## Files Changed

```
src/splunk_ao/otel.py
src/splunk_ao/handlers/openai_agents/handler.py
src/splunk_ao/utils/openai_agents.py
examples/agent/google-adk/my_agent/agent.py
examples/agent/langgraph-open-telemetry/main.py
examples/rag/cli-rag-demo/python-service/app.py
tests/test_otel.py
tests/test_openai_agents_utils.py
```

---

## Related

- [HYBIM-832](https://splunk.atlassian.net/browse/HYBIM-832) — `SPLUNK_AO_ENV_RENAME.md` removed (superseded migration docs)
- [HYBIM-730](https://splunk.atlassian.net/browse/HYBIM-730) — Domain entity rename (Metrics → Evaluators, Log Streams → Agent Streams) — separate upcoming PR
- `splunk-ao-migration-tool/README.md` — full Galileo → Splunk AO migration guide
