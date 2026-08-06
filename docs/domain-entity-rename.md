# Domain Entity Rename: Log Streams → Agent Streams, Metrics → Evaluators

**Ticket:** [HYBIM-730](https://splunk.atlassian.net/browse/HYBIM-730)
**Branch:** `feat/HYBIM-730-domain-rename`
**Status:** Implemented — hard cut-over, no backward compatibility

---

## Summary

Two core SDK domain entities were renamed to better reflect their purpose. This
is a **hard cut-over**: the old names are gone entirely. Migration for existing
users is handled by the separate migration guide and the `galileo` compatibility
SDK.

| Old name | New name | Scope |
|----------|----------|-------|
| `LogStream` / `LogStreams` | `AgentStream` / `AgentStreams` | Top-level class, service class, convenience functions |
| `Metric` / `Metrics` | `Evaluator` / `Evaluators` | Base class and all concrete subclasses |
| `LlmMetric` | `LlmEvaluator` | Concrete subclass |
| `CodeMetric` | `CodeEvaluator` | Concrete subclass |
| `LocalMetric` | `LocalEvaluator` | Concrete subclass |
| `SplunkAOMetric` | `SplunkAOEvaluator` | Concrete subclass |
| `BuiltInMetrics` | `BuiltInEvaluators` | Built-in scorer accessor class |

> **Note:** The underlying API endpoints continue to use the previous paths
> (`/log_streams`, `/scorers`) — server-side renaming is tracked separately.

---

## New Public API

### Agent Streams

```python
from splunk_ao import AgentStream

# Create and persist a new agent stream
stream = AgentStream(name="prod-traces", project_name="my-project").create()

# Retrieve an existing stream
stream = AgentStream.get(name="prod-traces", project_name="my-project")

# List streams for a project
streams = AgentStream.list(project_name="my-project")

# Enable evaluators on the stream
from splunk_ao.schema.metrics import SplunkAOEvaluators
stream.set_metrics([SplunkAOEvaluators.correctness, SplunkAOEvaluators.completeness])
```

```python
# Service class
from splunk_ao.agent_streams import AgentStreams

svc = AgentStreams()
stream = svc.get(name="prod-traces", project_name="my-project")
streams = svc.list(project_name="my-project")
new_stream = svc.create(name="new-stream", project_name="my-project")
```

```python
# Module-level convenience functions
from splunk_ao.agent_streams import get_agent_stream, list_agent_streams, create_agent_stream, enable_evaluators

stream  = get_agent_stream(name="prod-traces", project_name="my-project")
streams = list_agent_streams(project_name="my-project")
stream  = create_agent_stream(name="new-stream", project_name="my-project")
```

```python
# Project methods
from splunk_ao.project import Project

project = Project.get(name="My AI Project")
stream  = project.create_agent_stream(name="Production Traces")
streams = project.list_agent_streams()
for s in project.agent_streams:
    print(s.name)
```

### Evaluators

```python
from splunk_ao import Evaluator, LlmEvaluator, LocalEvaluator, SplunkAOEvaluator

# Access built-in scorers
ev = Evaluator.metrics.correctness
ev = Evaluator.metrics.completeness

# Get a custom evaluator by name or id
ev = Evaluator.get(name="my-evaluator")
ev = Evaluator.get(id="<uuid>")

# Create a custom LLM evaluator
llm_ev = LlmEvaluator(
    name="response_quality",
    prompt="Rate the quality of this response on a scale of 1-10: {response}",
    model="gpt-4o-mini",
).create()

# Create a local evaluator
def my_scorer(trace):
    return 1.0 if "answer" in trace.output else 0.0

local_ev = LocalEvaluator(name="has_answer", scorer_fn=my_scorer)
```

```python
# Service class
from splunk_ao.evaluators import Evaluators

svc = Evaluators()
evaluators = svc.get_evaluators()
svc.delete_evaluator(name="old-evaluator")
svc.create_custom_llm_evaluator(name="quality", prompt="...", model="gpt-4o-mini")
```

---

## Files Changed

### Source files deleted → replaced

| Deleted | Replaced by |
|---------|-------------|
| `src/splunk_ao/log_stream.py` | `src/splunk_ao/agent_stream.py` |
| `src/splunk_ao/log_streams.py` | `src/splunk_ao/agent_streams.py` |
| `src/splunk_ao/metric.py` | `src/splunk_ao/evaluator.py` |
| `src/splunk_ao/metrics.py` | `src/splunk_ao/evaluators.py` |

All `__future__` shim files were also deleted — no backward compatibility wrappers remain.

### Other source files updated

| File | Change |
|------|--------|
| `src/splunk_ao/__init__.py` | Exports only new names; deprecated `__getattr__` shims removed |
| `src/splunk_ao/project.py` | Removed `create_log_stream`, `list_log_streams`, `logstreams`; added `create_agent_stream`, `list_agent_streams`, `agent_streams` |
| `src/splunk_ao/__future__/__init__.py` | Updated to new class names |
| `src/splunk_ao/export.py` | Updated to `AgentStreams` |
| `src/splunk_ao/logger/logger.py` | Updated to `AgentStreams` |
| `src/splunk_ao/types.py` | `MetricSpec` now references `Evaluator` |

### Test files renamed and updated

| Old | New |
|-----|-----|
| `tests/test_log_stream.py` | `tests/test_agent_stream.py` |
| `tests/test_log_streams_metrics.py` | `tests/test_agent_streams_evaluators.py` |
| `tests/test_log_streams_pagination.py` | `tests/test_agent_streams_pagination.py` |
| `tests/test_metric.py` | `tests/test_evaluator.py` |
| `tests/test_metric_types.py` | `tests/test_evaluator_types.py` |
| `tests/test_metrics.py` | `tests/test_evaluators.py` |

All `@patch` paths, imports, assertions, and parameter names updated throughout the full test suite.

---

## Migration

For users upgrading from a version that used the old names:

- **Internal users**: the `galileo` SDK provides backward compatibility.
- **External users**: see the separate migration guide and the `splunk-ao-migration-tool`.

**Quick find-and-replace reference:**

```
LogStream        → AgentStream
LogStreams        → AgentStreams
Metric           → Evaluator      (OO class, not schema model)
LlmMetric        → LlmEvaluator
CodeMetric       → CodeEvaluator
LocalMetric      → LocalEvaluator
SplunkAOMetric   → SplunkAOEvaluator
BuiltInMetrics   → BuiltInEvaluators
Metrics          → Evaluators     (service class)

# Module imports
from splunk_ao.log_stream  import …  →  from splunk_ao.agent_stream  import …
from splunk_ao.log_streams import …  →  from splunk_ao.agent_streams import …
from splunk_ao.metric      import …  →  from splunk_ao.evaluator     import …
from splunk_ao.metrics     import …  →  from splunk_ao.evaluators    import …

# Method names
project.create_log_stream(…)   →  project.create_agent_stream(…)
project.list_log_streams(…)    →  project.list_agent_streams(…)
project.logstreams             →  project.agent_streams
log_stream.enable_metrics(…)   →  agent_stream.set_metrics(…)
enable_metrics(…)              →  enable_evaluators(…)   (AgentStreams service / module-level only)
delete_metric(…)               →  delete_evaluator(…)
get_metrics(…)                 →  get_evaluators(…)
create_custom_llm_metric(…)    →  create_custom_llm_evaluator(…)
```

---

## Design Decisions

- **Hard cut-over, no shims**: Per PR review, no `DeprecationWarning` wrappers or `__getattr__` shims are included. The old module names (`log_stream`, `log_streams`, `metric`, `metrics`) no longer exist. Any import of the old names raises `ModuleNotFoundError` / `ImportError`.
- **API endpoints unchanged**: The rename is purely client-side. The server still uses `/log_streams` and `/scorers` paths, so no backend changes are required for this release.
- **`BuiltInEvaluators`**: A direct rename of `BuiltInMetrics`. Accessed via `Evaluator.metrics` (the attribute name `metrics` is kept for API stability; a `scorers` alias is also available for legacy internal use).
- **`SchemaMetric` is not renamed**: `splunk_ao.schema.metrics.Metric` is the Pydantic schema model used in API payloads. It is distinct from the OO `Evaluator` class and is not renamed in this ticket.

---

## Related

- [HYBIM-730](https://splunk.atlassian.net/browse/HYBIM-730) — this ticket
- [HYBIM-832](https://splunk.atlassian.net/browse/HYBIM-832) — env-var rename (`GALILEO_*` → `SPLUNK_AO_*`)
- [HYBIM-914](https://splunk.atlassian.net/browse/HYBIM-914) — env-var rename (`SPLUNK_AO_LOG_STREAM` → `SPLUNK_AO_AGENT_STREAM`)
- PR #100 — this PR
