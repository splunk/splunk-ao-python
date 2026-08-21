# splunk_ao_migrate — Regex-Based Migration Tool

Automatically migrate Python code from the `galileo` SDK to `splunk-ao-python`
using ordered regex substitutions.

## What it does

Rewrites every file type the migration touches in a single pass, then renames any
directories or files whose names contain `galileo`:

| File type | Examples | What changes |
|-----------|----------|--------------|
| Python source | `*.py` | Imports, class names, kwargs, env-var strings, HTTP headers |
| Doc files | `*.md`, `*.rst` | Same rules as Python; known Galileo doc URLs rewritten to Splunk AO equivalents; all other URLs left intact |
| Dependency files | `requirements*.txt`, `pyproject.toml` | Package names, Python identifiers, uv source keys, pytest env vars, brand prose, `requires-python` floor |
| Environment files | `.env`, `.env.example` | All `GALILEO_*` keys → `SPLUNK_AO_*`; `galileo` in placeholder values |
| Filesystem paths | directories, filenames | `galileo-a2a/` → `splunk-ao-a2a/`, `galileo_a2a/` → `splunk_ao_a2a/`, etc. |

## Installation

```bash
# Install from the package directory
pip install ./splunk_ao_migrate

# Or with uv
uv pip install ./splunk_ao_migrate
```

No external dependencies — uses Python stdlib only.

## Usage

```bash
# Rewrite an entire directory in place
splunk-ao-migrate src/

# Rewrite a single file
splunk-ao-migrate my_agent.py

# Preview changes without writing (dry run)
splunk-ao-migrate --dry-run src/

# Suppress the summary report
splunk-ao-migrate --no-report src/

# Run directly without installing
python splunk_ao_migrate/migrate.py --dry-run src/

# Run as a module
python -m splunk_ao_migrate.migrate --dry-run src/

# Run with uv
uv run python splunk_ao_migrate/migrate.py --dry-run src/
```

## Package layout

```
splunk_ao_migrate/
  migrate.py      ← CLI entry point (also registered as splunk-ao-migrate console script)
  rules.py        ← all substitution rules (imports, symbols, kwargs, env-vars, headers)
  transformer.py  ← applies rules to source text, returns TransformResult
  reporter.py     ← formats and prints the migration summary report
  pyproject.toml  ← package metadata and entry point declaration
  README.md       ← this file
```

## What gets migrated

### Python files

- `from galileo import …` → `from splunk_ao import …`
- `from galileo.metric import …` → `from splunk_ao.evaluator import …`
- `GalileoLogger` → `SplunkAOLogger` (and all other `Galileo*` class renames)
- `GalileoMetric` / `GalileoMetrics` / `GalileoScorers` → `SplunkAOEvaluator` / `SplunkAOEvaluators`
- `SplunkAOMetric` → `SplunkAOEvaluator`, `SplunkAOMetrics` → `SplunkAOEvaluators`
- Domain renames: `Metric` → `Evaluator`, `LlmMetric` → `LlmEvaluator`, `LocalMetric` → `LocalEvaluator`, etc.
- **Not renamed**: `MetricSpec` and `LocalMetricConfig` — these remain as live names in `splunk-ao` (the rename proposal `EvaluatorSpec` / `LocalEvaluatorConfig` was not implemented)
- `LogStream` → `AgentStream`, `.logstreams` → `.agent_streams`
- Method renames: `get_log_stream` → `get_agent_stream`, `create_log_stream` → `create_agent_stream`, `list_log_streams` → `list_agent_streams`, `delete_metric` → `delete_evaluator`, `create_custom_llm_metric` → `create_custom_llm_evaluator`
- **Not renamed**: `get_metrics()` and `set_metrics()` on `AgentStream` — these remain as live method names; only the module-level `get_evaluators()` function is the new API
- Keyword argument and parameter renames: `log_stream=` → `agent_stream=`, `log_stream_name=` → `agent_stream_name=`, `logstream=` → `agentstream=`; also catches typed parameter declarations like `log_stream: str | None = None` → `agent_stream: str | None = None`
- Config file renames: `galileo-python-config.json` → `splunk-ao-config.json`, `galileo-config.json` → `splunk-ao-config.json`
- `GALILEO_*` env-var string literals → `SPLUNK_AO_*` (including `GALILEO_API_ENDPOINT`, `GALILEO_API_KEY`, `GALILEO_CONSOLE_URL`, `GALILEO_HOME_DIR`, etc.)
- `X-Galileo-Trace-ID` / `X-Galileo-Parent-ID` HTTP headers
- `GalileoSpanProcessor` → `SplunkAOSpanProcessor`, `add_galileo_span_processor` → `add_splunk_ao_span_processor`
- `GalileoObserver` → `SplunkAOObserver`
- `galileo_*` prefixed identifiers (e.g. `galileo_session_id`) → `splunk_ao_*`
- `_galileo_` mid-identifier and attribute patterns (e.g. `func._galileo_is_retriever`, `self._handler._galileo_logger`) → `_splunk_ao_*`; the rule fires after `.`, spaces, and quotes, not just within word characters
- `GALILEO_OBSERVE_KEY` constant name → `SPLUNK_AO_OBSERVE_KEY` (the string wire value `"galileo_observe"` is intentionally left unchanged for A2A metadata compatibility)
- `galileo-a2a` package name in string literals and pip installs → `splunk-ao-a2a` (hyphenated; handled before the generic `galileo` rule to avoid producing the wrong underscore form)
- `Galileo.ai` brand name in prose → `Splunk AO`
- `Galileo` brand name in comments/docstrings → `Splunk AO`

### Doc files (`.md`, `.rst`)

Doc files are processed in three passes:

1. **URL pass**: known Galileo documentation URLs are rewritten to their Splunk AO equivalents:
   - `https://docs.galileo.ai/` → `https://agent-observability-docs.splunk.com/`
   - `.../add-galileo-to-crewai/add-galileo-to-crewai` → `.../add-splunk-ao-to-crewai/add-splunk-ao-to-crewai`
   - `-galileo.md` filename references → `-splunk-ao.md`
   - `-galileo.txt` filename references → `-splunk-ao.txt`
   - `/what-is-galileo` → `/what-is-splunk-agent-observability`
   - `/getting-started/logging` → `/concepts/logging/overview`
   - `/concepts/experiments/overview` → `/sdk-api/experiments/experiments`
2. **Prose pass**: all the same symbol, import, env-var, and brand-name substitutions as Python files, with one exception — `logstream=` (no underscore) is **not** rewritten in docs to avoid corrupting env-var string values like `TRACELOOP_HEADERS="..., logstream=default, ..."`. `log_stream=` and `log_stream_name=` are still rewritten.
3. **Placeholder fix pass**: corrects `your-splunk_ao-*` (underscore, produced by the import rule) back to `your-splunk-ao-*` (hyphenated, correct prose form). Also corrects bare `splunk_ao` in prose position (not followed by `_` or `.`) to the brand name `Splunk AO`.

All other URLs (`https?://...`) are **not rewritten** — external links remain intact.

### Dependency files

- `galileo` → `splunk-ao`
- `galileo-adk` → `splunk-ao-adk`
- `galileo-a2a` → `splunk-ao-a2a`
- `galileo_a2a` → `splunk_ao_a2a` (Python package identifier in paths and config)
- `galileo_adk` → `splunk_ao_adk`
- `sources = { galileo = ...}` → `sources = { "splunk-ao" = ...}` (uv TOML source key, quoted because hyphen is not valid in a bare TOML key)
- `GALILEO_*` env-var strings in `pyproject.toml` pytest `env = [...]` blocks → `SPLUNK_AO_*`
- `requires-python` floor below `3.11` → `>=3.11` (e.g. `>=3.10,<3.14` → `>=3.11,<3.14`)
- `Galileo` brand name in prose fields (e.g. `description`, `authors`) → `Splunk AO`

### Environment files

- All `GALILEO_*` keys → `SPLUNK_AO_*` (e.g. `GALILEO_API_ENDPOINT`, `GALILEO_API_KEY`, `GALILEO_CONSOLE_URL`, `GALILEO_PROJECT`, etc.)
- `GALILEO_LOGSTREAM` / `GALILEO_LOG_STREAM` → `SPLUNK_AO_AGENT_STREAM`
- HTTP header strings: `Galileo-API-Key` → `Splunk-AO-API-Key`, `X-Galileo-Trace-ID` → `Splunk-AO-Trace-ID`
- `galileo` as a word in placeholder values (e.g. `your-galileo-key` → `your-splunk-ao-key`)
- `galileo` inside underscore-delimited placeholder tokens (e.g. `your_galileo_api_key_here` → `your_splunk_ao_api_key_here`)
- `Galileo` brand name in comments → `Splunk AO`

### Filesystem paths

Directories and files are renamed after file content is rewritten, deepest-first
so child paths are handled before their parents:

- `galileo-a2a/` → `splunk-ao-a2a/`
- `galileo-adk/` → `splunk-ao-adk/`
- `galileo_a2a/` → `splunk_ao_a2a/` (Python package dirs use underscore)
- `galileo_` prefix in any directory or filename → `splunk_ao_`
- bare `galileo` directory name → `splunk_ao`

The root directory passed as the CLI argument is included in the rename scan,
so `splunk-ao-migrate galileo-a2a/` will rename the directory itself to `splunk-ao-a2a/`.

## Warnings (flagged, not auto-fixed)

- **Protect feature usage** (`invoke_protect`, `ainvoke_protect`, etc.) — keep `galileo`
  as a dependency; Protect is not available in `splunk-ao`
- **`galileo_core` imports** — `galileo_core` is a low-level external dependency used
  internally by `splunk-ao`. It is **not** renamed to `splunk_ao_core` (no such package
  exists). When this warning fires, review any `galileo_core` types used in your code
  (e.g. `Metrics` from `galileo_core.schemas.logging.step`) — they are internal types
  and should not be renamed to the `splunk-ao` public API equivalents
- **Dynamic env-var construction** (`f"GALILEO_{key}"`) — cannot be auto-rewritten;
  update manually
- **`GALILEO_OBSERVE_KEY`** — OTel interop constant name in `splunk-ao-a2a`; the tool
  renames the Python constant to `SPLUNK_AO_OBSERVE_KEY` but flags it so you can verify
  the wire-level string value `"galileo_observe"` is intentionally preserved for
  cross-agent A2A metadata compatibility
- **Lowercase `galileo` in string literals** — may refer to the astronomer or other
  non-SDK usage (e.g. `"what moons did galileo discover"`); verify whether it should
  be renamed or left as-is

## Manual steps after migration

- **On-disk config directory**: the local config directory has moved from `~/.galileo/` to `~/.splunk/`.
  Delete or migrate any `~/.galileo/galileo-python-config.json` to `~/.splunk/splunk-ao-config.json`
  manually — the tool rewrites file content and names but does not touch directories outside the target path.

## Limitations

- Rules are applied to raw text, so occurrences in comments and docstrings are also
  rewritten.
- URLs are not rewritten in Python, dependency, and environment files. In doc files
  (`.md`, `.rst`), only the known Galileo documentation URLs listed above are rewritten;
  all other external links are preserved as-is.
- **`galileo_core` interop code**: files that import from `galileo_core` and use its
  internal types (e.g. `Metrics`, `_ADK_ROLE_TO_GALILEO`, `_map_adk_role_to_galileo`)
  may have some internal variable/function names over-fired. The `galileo_core` warning
  identifies these files for manual review. This only affects code that directly wraps or
  bridges `galileo_core` internals (e.g. `splunk-ao-adk` source itself) — typical user
  application code is not affected.

## See also

- `splunk-ao-migration-tool/README.md` — complete migration guide
