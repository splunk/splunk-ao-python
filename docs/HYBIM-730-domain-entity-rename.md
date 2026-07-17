# Domain Entity Rename: Log Streams → Agent Streams, Metrics → Evaluators

**Ticket:** [HYBIM-730](https://splunk.atlassian.net/browse/HYBIM-730)  
**Branch:** `feat/HYBIM-730-domain-rename`  
**Status:** Implemented with full backward compatibility

---

## Summary

Two core SDK domain entities are being renamed to better reflect their purpose:

| Old name | New name | Scope |
|----------|----------|-------|
| Log Stream / `LogStream` | Agent Stream / `AgentStream` | Top-level class, service class, convenience functions |
| Metric / `Metric` | Evaluator / `Evaluator` | Base class and all concrete subclasses |

The old names remain functional but emit `DeprecationWarning` at import time.  
They will be removed in a future major release.

> **Note:** The underlying API endpoints continue to use the previous paths
> (`/log_streams`, `/scorers`) — server-side renaming is tracked separately.

---

## New Public API

### Agent Streams

```python
# Primary class (replaces LogStream)
from splunk_ao import AgentStream

# Create and persist a new agent stream
stream = AgentStream(name="prod-traces", project_name="my-project").create()

# Retrieve an existing stream
stream = AgentStream.get(name="prod-traces", project_name="my-project")

# List streams for a project
streams = AgentStream.list(project_name="my-project")

# Enable evaluators on the stream
from splunk_ao import SplunkAOMetrics
stream.set_metrics([SplunkAOMetrics.correctness, SplunkAOMetrics.completeness])
```

```python
# Service class (replaces LogStreams in splunk_ao.log_streams)
from splunk_ao.agent_streams import AgentStreams

svc = AgentStreams()
stream = svc.get(name="prod-traces", project_name="my-project")
streams = svc.list(project_name="my-project")
```

```python
# Convenience functions (replaces functions in splunk_ao.log_streams)
from splunk_ao.agent_streams import (
    get_agent_stream,
    list_agent_streams,
    create_agent_stream,
    enable_evaluators,
)

stream = get_agent_stream(name="prod-traces", project_name="my-project")
streams = list_agent_streams(project_name="my-project")
stream = create_agent_stream(name="new-stream", project_name="my-project")

# Enable evaluators (formerly enable_metrics)
local_evals = enable_evaluators(
    agent_stream_name="prod-traces",
    project_name="my-project",
    metrics=[SplunkAOMetrics.correctness, "completeness"],
)
```

### Evaluators

```python
# Base class (replaces Metric)
from splunk_ao import Evaluator, LlmEvaluator, CodeEvaluator, LocalEvaluator, SplunkAOEvaluator

# Get an existing evaluator by name or ID
ev = Evaluator.get(name="factuality-checker")

# List all evaluators
evaluators = Evaluator.list()

# Access built-in evaluators
ev = Evaluator.evaluators.correctness
ev = Evaluator.evaluators.completeness

# Create a custom LLM evaluator
llm_ev = LlmEvaluator(
    name="response_quality",
    prompt="Rate the quality 1-10: {input} -> {output}",
    model="gpt-4o-mini",
    judges=3,
).create()

# Create a code-based evaluator
code_ev = CodeEvaluator(
    name="custom_scorer",
    code="def scorer_fn(step): return 1.0",
).create()

# Create a local function-based evaluator
def my_fn(trace):
    return min(len(getattr(trace, "output", "") or "") / 200.0, 1.0)

local_ev = LocalEvaluator(name="response_length", scorer_fn=my_fn)
```

```python
# Evaluators service class (replaces Metrics in splunk_ao.metrics)
from splunk_ao.evaluators import (
    Evaluators,
    create_custom_llm_evaluator,
    get_evaluators,
    delete_evaluator,
)

create_custom_llm_evaluator(name="my-eval", user_prompt="Rate this...")
delete_evaluator(name="old-eval")
```

### Project methods

```python
from splunk_ao import Project

project = Project.get(name="My AI Project")

# New methods
stream = project.create_agent_stream(name="Production Traces")
streams = project.list_agent_streams()
for stream in project.agent_streams:
    print(stream.name)
```

---

## Backward Compatibility

All old names continue to work but emit `DeprecationWarning`:

```python
import warnings
warnings.simplefilter("always", DeprecationWarning)

# These still work — but warn:
from splunk_ao import LogStream       # warns: use AgentStream
from splunk_ao import Metric          # warns: use Evaluator
from splunk_ao import LlmMetric       # warns: use LlmEvaluator
from splunk_ao import CodeMetric      # warns: use CodeEvaluator
from splunk_ao import LocalMetric     # warns: use LocalEvaluator
from splunk_ao import SplunkAOMetric  # warns: use SplunkAOEvaluator

# Project deprecated methods — warn:
project.create_log_stream("foo")   # warns: use create_agent_stream
project.list_log_streams()         # warns: use list_agent_streams
project.logstreams                 # warns: use agent_streams
```

### Migration quick-reference

| Old import | New import |
|------------|------------|
| `from splunk_ao import LogStream` | `from splunk_ao import AgentStream` |
| `from splunk_ao import Metric` | `from splunk_ao import Evaluator` |
| `from splunk_ao import LlmMetric` | `from splunk_ao import LlmEvaluator` |
| `from splunk_ao import CodeMetric` | `from splunk_ao import CodeEvaluator` |
| `from splunk_ao import LocalMetric` | `from splunk_ao import LocalEvaluator` |
| `from splunk_ao import SplunkAOMetric` | `from splunk_ao import SplunkAOEvaluator` |
| `from splunk_ao.log_stream import LogStream` | `from splunk_ao.agent_stream import AgentStream` |
| `from splunk_ao.log_streams import LogStreams` | `from splunk_ao.agent_streams import AgentStreams` |
| `from splunk_ao.log_streams import get_log_stream` | `from splunk_ao.agent_streams import get_agent_stream` |
| `from splunk_ao.log_streams import list_log_streams` | `from splunk_ao.agent_streams import list_agent_streams` |
| `from splunk_ao.log_streams import create_log_stream` | `from splunk_ao.agent_streams import create_agent_stream` |
| `from splunk_ao.log_streams import enable_metrics` | `from splunk_ao.agent_streams import enable_evaluators` |
| `from splunk_ao.metric import Metric` | `from splunk_ao.evaluator import Evaluator` |
| `from splunk_ao.metrics import Metrics` | `from splunk_ao.evaluators import Evaluators` |
| `project.create_log_stream(name)` | `project.create_agent_stream(name)` |
| `project.list_log_streams()` | `project.list_agent_streams()` |
| `project.logstreams` | `project.agent_streams` |

---

## Files Changed

| File | Change |
|------|--------|
| `src/splunk_ao/agent_stream.py` | **New** — `AgentStream` subclass of `LogStream` |
| `src/splunk_ao/agent_streams.py` | **New** — `AgentStreams` service class + convenience functions |
| `src/splunk_ao/evaluator.py` | **New** — `Evaluator`, `LlmEvaluator`, `CodeEvaluator`, `LocalEvaluator`, `SplunkAOEvaluator` |
| `src/splunk_ao/evaluators.py` | **New** — `Evaluators` service class + convenience functions |
| `src/splunk_ao/__future__/agent_stream.py` | **New** — deprecation shim |
| `src/splunk_ao/__future__/evaluator.py` | **New** — deprecation shim |
| `src/splunk_ao/__init__.py` | **Modified** — export new names; PEP 562 `__getattr__` for deprecated old names |
| `src/splunk_ao/project.py` | **Modified** — add `create_agent_stream`, `list_agent_streams`, `agent_streams`; deprecate old methods |
| `docs/HYBIM-730-domain-entity-rename.md` | **New** — this document |

---

## Design Decisions

### Subclassing vs type aliases

`AgentStream` is implemented as a subclass of `LogStream` (rather than a plain
`= LogStream` alias) so that:
- `AgentStream.__name__` is `"AgentStream"`
- Instances created via `AgentStream(...)` have the new name in repr
- Future implementation divergence is possible without API breakage

The same pattern applies to `Evaluator` / `LlmEvaluator` / etc.

### PEP 562 `__getattr__` in `__init__.py`

Old names (`LogStream`, `Metric`, …) are **not** listed in `__all__`, so they
are invisible to tab-completion and static analysis. They are only reachable
via `__getattr__`, which fires a `DeprecationWarning`. This gives existing code
a graceful migration path without polluting the new API surface.

### Server-side API paths unchanged

The API endpoints remain on the old paths (`/log_streams`, `/scorers`).
`AgentStream` / `Evaluator` call into the same service layers (`LogStreams`,
`Metrics`) as before. A separate ticket tracks the server-side rename.

---

## Related

- [HYBIM-730](https://splunk.atlassian.net/browse/HYBIM-730) — this ticket
- [HYBIM-832](https://splunk.atlassian.net/browse/HYBIM-832) — Galileo → Splunk AO env-var rename
- `docs/OTEL_GALILEO_TO_SPLUNK_AO_RENAME.md` — OTel layer rename
