"""
All substitution rules for the galileo → splunk-ao migration.

Rules are grouped and ordered deliberately:
  1. Import rewrites  (must run first — change module paths)
  2. Class / symbol renames  (longest names first to avoid partial matches)
  3. Keyword argument renames
  4. Env-var string literals
  5. HTTP header string literals
  6. Configuration attribute renames

Warning rules are never applied; they only trigger a report entry.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Rule:
    pattern: str
    replacement: str
    description: str
    is_warning: bool = False


# ---------------------------------------------------------------------------
# 1. Import rewrites
# ---------------------------------------------------------------------------
# galileo.metric  →  splunk_ao.evaluator  (must come before generic galileo.X rule)
IMPORT_RULES: list[Rule] = [
    Rule(
        pattern=r"\bgalileo\.metric\b",
        replacement="splunk_ao.evaluator",
        description="galileo.metric → splunk_ao.evaluator",
    ),
    Rule(
        pattern=r"\bgalileo_adk\b",
        replacement="splunk_ao_adk",
        description="galileo_adk → splunk_ao_adk",
    ),
    Rule(
        pattern=r"\bgalileo_a2a\b",
        replacement="splunk_ao_a2a",
        description="galileo_a2a → splunk_ao_a2a",
    ),
    # Package name as a hyphenated string literal (e.g. "galileo-a2a", pip install galileo-a2a).
    # Must come before the generic galileo rule which would produce "splunk_ao-a2a" (underscore).
    Rule(
        pattern=r"\bgalileo-a2a\b",
        replacement="splunk-ao-a2a",
        description="galileo-a2a → splunk-ao-a2a (package name in string literals and prose)",
    ),
    Rule(
        # Exclude domain names: skip when followed by a short TLD (.ai, .com, .io, .org etc. — 2-3 chars).
        # Longer suffixes like .otel, .metric, .python are Python module paths and must be matched.
        # Full URL skipping is handled in transformer.py._sub_outside_urls.
        pattern=r"\bgalileo(?!\.[a-z]{2,3}\b)\b",
        replacement="splunk_ao",
        description="galileo → splunk_ao (imports and module refs)",
    ),
]

# ---------------------------------------------------------------------------
# 2. Class / symbol renames  (ordered longest-first within each group)
# ---------------------------------------------------------------------------
SYMBOL_RULES: list[Rule] = [
    # --- Handlers & middleware ---
    Rule("GalileoAsyncBaseHandler", "SplunkAOAsyncBaseHandler", "GalileoAsyncBaseHandler → SplunkAOAsyncBaseHandler"),
    Rule("GalileoAsyncCallback", "SplunkAOAsyncCallback", "GalileoAsyncCallback → SplunkAOAsyncCallback"),
    Rule("GalileoAgentControlBridge", "SplunkAOAgentControlBridge", "GalileoAgentControlBridge → SplunkAOAgentControlBridge"),
    Rule("GalileoTracingProcessor", "SplunkAOTracingProcessor", "GalileoTracingProcessor → SplunkAOTracingProcessor"),
    Rule("GalileoLoggerSingleton", "SplunkAOLoggerSingleton", "GalileoLoggerSingleton → SplunkAOLoggerSingleton"),
    Rule("GalileoLoggerException", "SplunkAOLoggerException", "GalileoLoggerException → SplunkAOLoggerException"),
    Rule("GalileoOTLPExporter", "SplunkAOOTLPExporter", "GalileoOTLPExporter → SplunkAOOTLPExporter"),
    Rule("GalileoSpanProcessor", "SplunkAOSpanProcessor", "GalileoSpanProcessor → SplunkAOSpanProcessor"),
    Rule("add_galileo_span_processor", "add_splunk_ao_span_processor", "add_galileo_span_processor → add_splunk_ao_span_processor"),
    Rule("start_galileo_span", "start_splunk_ao_span", "start_galileo_span → start_splunk_ao_span"),
    Rule("GalileoPythonConfig", "SplunkAOConfig", "GalileoPythonConfig → SplunkAOConfig"),
    Rule("GalileoMiddleware", "SplunkAOMiddleware", "GalileoMiddleware → SplunkAOMiddleware"),
    Rule("GalileoDecorator", "SplunkAODecorator", "GalileoDecorator → SplunkAODecorator"),
    Rule("GalileoCallback", "SplunkAOCallback", "GalileoCallback → SplunkAOCallback"),
    Rule("GalileoFutureError", "SplunkAOFutureError", "GalileoFutureError → SplunkAOFutureError"),
    Rule("GalileoCustomSpan", "SplunkAOCustomSpan", "GalileoCustomSpan → SplunkAOCustomSpan"),
    Rule("GalileoBaseHandler", "SplunkAOBaseHandler", "GalileoBaseHandler → SplunkAOBaseHandler"),
    Rule("GalileoAPIError", "SplunkAOAPIError", "GalileoAPIError → SplunkAOAPIError"),
    Rule("GalileoLogger", "SplunkAOLogger", "GalileoLogger → SplunkAOLogger"),
    # --- CrewAI handler ---
    Rule("GalileoEventListener", "CrewAIEventListener", "GalileoEventListener → CrewAIEventListener"),
    # --- ADK ---
    Rule("GalileoObserver", "SplunkAOObserver", "GalileoObserver → SplunkAOObserver"),
    Rule("GalileoADKCallback", "SplunkAOADKCallback", "GalileoADKCallback → SplunkAOADKCallback"),
    Rule("GalileoADKPlugin", "SplunkAOADKPlugin", "GalileoADKPlugin → SplunkAOADKPlugin"),
    Rule("galileo_retriever", "splunk_ao_retriever", "galileo_retriever → splunk_ao_retriever"),
    # --- Metrics / evaluators (GalileoScorers before GalileoMetrics) ---
    Rule("GalileoScorers", "SplunkAOEvaluators", "GalileoScorers → SplunkAOEvaluators"),
    Rule("GalileoMetrics", "SplunkAOEvaluators", "GalileoMetrics → SplunkAOEvaluators"),
    Rule("GalileoMetric", "SplunkAOEvaluator", "GalileoMetric → SplunkAOEvaluator"),
    # SplunkAOMetric* renames (doc: SplunkAOMetric → SplunkAOEvaluator, SplunkAOMetrics → SplunkAOEvaluators)
    Rule("SplunkAOMetrics", "SplunkAOEvaluators", "SplunkAOMetrics → SplunkAOEvaluators"),
    Rule("SplunkAOMetric", "SplunkAOEvaluator", "SplunkAOMetric → SplunkAOEvaluator"),
    # --- Context / config ---
    Rule("galileo_context", "splunk_ao_context", "galileo_context → splunk_ao_context"),
    Rule("convert_to_galileo_message", "convert_to_splunk_ao_message", "convert_to_galileo_message → convert_to_splunk_ao_message"),
    # --- Domain: Metrics → Evaluators (bare names, word-boundary guarded) ---
    # MetricSpec and LocalMetricConfig are NOT renamed — the repo keeps them as live names in splunk-ao.
    # The rename proposal (EvaluatorSpec, LocalEvaluatorConfig) was NOT implemented in the final codebase.
    Rule(r"\bBuiltInMetrics\b", "BuiltInEvaluators", "BuiltInMetrics → BuiltInEvaluators"),
    Rule(r"\bLocalMetric\b", "LocalEvaluator", "LocalMetric → LocalEvaluator"),
    Rule(r"\bCodeMetric\b", "CodeEvaluator", "CodeMetric → CodeEvaluator"),
    Rule(r"\bLlmMetric\b", "LlmEvaluator", "LlmMetric → LlmEvaluator"),
    Rule(r"\bMetrics\b", "Evaluators", "Metrics → Evaluators"),
    Rule(r"\bMetric\b", "Evaluator", "Metric → Evaluator"),
    # --- Domain: LogStream → AgentStream (bare names) ---
    Rule(r"\bLogStreams\b", "AgentStreams", "LogStreams → AgentStreams"),
    Rule(r"\bLogStream\b", "AgentStream", "LogStream → AgentStream"),
    # --- Methods / functions: LogStream → AgentStream ---
    Rule(r"\bcreate_log_stream\b", "create_agent_stream", "create_log_stream → create_agent_stream"),
    Rule(r"\blist_log_streams\b", "list_agent_streams", "list_log_streams → list_agent_streams"),
    Rule(r"\bget_log_stream\b", "get_agent_stream", "get_log_stream → get_agent_stream"),
    Rule(r"\.logstreams\b", ".agent_streams", ".logstreams → .agent_streams"),
    # --- Parameter / variable name: log_stream (bare identifier, not as a kwarg) ---
    # Catches parameter declarations like `log_stream: str | None = None` and local
    # variables like `effective_log_stream = ...` which the KWARG_RULES miss because
    # the pattern `log_stream\s*=` requires `=` immediately after and skips `:` type annotations.
    # log_streams (plural) is already covered by list_log_streams above; this handles singular.
    Rule(r"\blog_stream\b", "agent_stream", "log_stream identifier → agent_stream"),
    # --- Methods / functions: Metrics → Evaluators ---
    Rule(r"\benable_metrics\b", "enable_evaluators", "enable_metrics → enable_evaluators"),
    # NOTE: get_metrics() and set_metrics() are NOT renamed — they remain as live method names
    # on the AgentStream object. Only the module-level get_evaluators() function is the new API.
    Rule(r"\bcreate_custom_llm_metric\b", "create_custom_llm_evaluator", "create_custom_llm_metric → create_custom_llm_evaluator"),
    Rule(r"\bdelete_metric\b", "delete_evaluator", "delete_metric → delete_evaluator"),
    # --- Configuration attribute ---
    Rule(r"\bgalileo_api_key\b", "splunk_ao_api_key", "galileo_api_key → splunk_ao_api_key"),
    # Config file renames
    # galileo-python-config.json must come before galileo-config.json to avoid a partial match
    Rule("galileo-python-config.json", "splunk-ao-config.json", "galileo-python-config.json → splunk-ao-config.json"),
    Rule("galileo-config.json", "splunk-ao-config.json", "galileo-config.json → splunk-ao-config.json"),
    # --- OTel interop observe-key constant (splunk-ao-a2a package) ---
    # GALILEO_OBSERVE_KEY is the Python constant *name* defined in splunk-ao-a2a/_constants.py.
    # It should be renamed to SPLUNK_AO_OBSERVE_KEY.  This is distinct from the string *value*
    # "galileo_observe" (the A2A metadata key) which must stay unchanged for wire compatibility.
    Rule(r"\bGALILEO_OBSERVE_KEY\b", "SPLUNK_AO_OBSERVE_KEY", "GALILEO_OBSERVE_KEY → SPLUNK_AO_OBSERVE_KEY"),
    # --- galileo embedded inside an identifier, including attribute access patterns ---
    # Handles: create_galileo_session, func._galileo_is_retriever, self._handler._galileo_logger,
    # and docstring references like "sets _galileo_is_retriever on func".
    # No lookbehind — matches _galileo_ after any non-word char (dot, space, quote, start-of-line)
    # as well as mid-word (e.g. create_galileo_session where 'e' precedes '_').
    # Must come before the galileo_ prefix rule to avoid a partial match.
    Rule(r"_galileo_", "_splunk_ao_", "_galileo_ in identifier or attribute → _splunk_ao_"),
    # --- galileo at the END of a Python identifier after an underscore (e.g. _execute_without_galileo) ---
    # \b fires between the final 'o' and a non-word char; (?<=_) ensures the preceding char is '_'.
    Rule(r"(?<=_)galileo\b", "splunk_ao", "_galileo at end of identifier → _splunk_ao"),
    # --- Generic galileo_ prefix on any Python identifier not already matched above ---
    # Excludes galileo_core: galileo_core is a third-party dependency (not the galileo SDK)
    # and must NOT be renamed. See WARNING_RULES for a galileo_core usage notice.
    Rule(r"\bgalileo(?!_core)_", "splunk_ao_", "galileo_* identifier → splunk_ao_* (excludes galileo_core)"),
]

# ---------------------------------------------------------------------------
# 3. Keyword argument renames
# ---------------------------------------------------------------------------
KWARG_RULES: list[Rule] = [
    # log_stream_name= must come before log_stream= to avoid a partial match
    Rule(
        pattern=r"\blog_stream_name\s*=",
        replacement="agent_stream_name=",
        description="log_stream_name= kwarg → agent_stream_name=",
    ),
    Rule(
        pattern=r"\blog_stream\s*=",
        replacement="agent_stream=",
        description="log_stream= kwarg → agent_stream=",
    ),
    # logstream= (no underscore) variant used in some SDK versions.
    # NOTE: applied only to Python files (PYTHON_RULES), not doc files (DOC_PROSE_RULES),
    # to avoid rewriting logstream= inside string values like TRACELOOP_HEADERS="...".
    Rule(
        pattern=r"\blogstream\s*=",
        replacement="agentstream=",
        description="logstream= kwarg → agentstream=",
    ),
]

# ---------------------------------------------------------------------------
# 4. Environment variable string literals
#    Matches the bare name inside any quote style, also in .env files.
#    LOG_STREAM must come before the shorter PROJECT / API_KEY etc.
# ---------------------------------------------------------------------------
ENV_VAR_RULES: list[Rule] = [
    Rule("GALILEO_LOG_STREAM_ID", "SPLUNK_AO_AGENT_STREAM_ID", "GALILEO_LOG_STREAM_ID → SPLUNK_AO_AGENT_STREAM_ID"),
    # GALILEO_LOGSTREAM (no underscore) must come before GALILEO_LOG_STREAM to avoid a partial match
    Rule("GALILEO_LOGSTREAM", "SPLUNK_AO_AGENT_STREAM", "GALILEO_LOGSTREAM → SPLUNK_AO_AGENT_STREAM"),
    Rule("GALILEO_LOG_STREAM", "SPLUNK_AO_AGENT_STREAM", "GALILEO_LOG_STREAM → SPLUNK_AO_AGENT_STREAM"),
    Rule("GALILEO_INGEST_BETA_DISABLED", "SPLUNK_AO_INGEST_BETA_DISABLED", "GALILEO_INGEST_BETA_DISABLED → SPLUNK_AO_INGEST_BETA_DISABLED"),
    Rule("GALILEO_LOGGING_DISABLED", "SPLUNK_AO_LOGGING_DISABLED", "GALILEO_LOGGING_DISABLED → SPLUNK_AO_LOGGING_DISABLED"),
    Rule("GALILEO_DEFAULT_SCORER_JUDGES", "SPLUNK_AO_DEFAULT_SCORER_JUDGES", "GALILEO_DEFAULT_SCORER_JUDGES → SPLUNK_AO_DEFAULT_SCORER_JUDGES"),
    Rule("GALILEO_DEFAULT_SCORER_MODEL", "SPLUNK_AO_DEFAULT_SCORER_MODEL", "GALILEO_DEFAULT_SCORER_MODEL → SPLUNK_AO_DEFAULT_SCORER_MODEL"),
    Rule("GALILEO_CODE_VALIDATION_", "SPLUNK_AO_CODE_VALIDATION_", "GALILEO_CODE_VALIDATION_* → SPLUNK_AO_CODE_VALIDATION_*"),
    Rule("GALILEO_CONSOLE_URL", "SPLUNK_AO_CONSOLE_URL", "GALILEO_CONSOLE_URL → SPLUNK_AO_CONSOLE_URL"),
    Rule("GALILEO_SSO_ID_TOKEN", "SPLUNK_AO_SSO_ID_TOKEN", "GALILEO_SSO_ID_TOKEN → SPLUNK_AO_SSO_ID_TOKEN"),
    Rule("GALILEO_SSO_PROVIDER", "SPLUNK_AO_SSO_PROVIDER", "GALILEO_SSO_PROVIDER → SPLUNK_AO_SSO_PROVIDER"),
    Rule("GALILEO_PROJECT_ID", "SPLUNK_AO_PROJECT_ID", "GALILEO_PROJECT_ID → SPLUNK_AO_PROJECT_ID"),
    Rule("GALILEO_JWT_TOKEN", "SPLUNK_AO_JWT_TOKEN", "GALILEO_JWT_TOKEN → SPLUNK_AO_JWT_TOKEN"),
    Rule("GALILEO_API_ENDPOINT", "SPLUNK_AO_API_ENDPOINT", "GALILEO_API_ENDPOINT → SPLUNK_AO_API_ENDPOINT"),
    Rule("GALILEO_API_KEY", "SPLUNK_AO_API_KEY", "GALILEO_API_KEY → SPLUNK_AO_API_KEY"),
    Rule("GALILEO_API_URL", "SPLUNK_AO_API_URL", "GALILEO_API_URL → SPLUNK_AO_API_URL"),
    Rule("GALILEO_USERNAME", "SPLUNK_AO_USERNAME", "GALILEO_USERNAME → SPLUNK_AO_USERNAME"),
    Rule("GALILEO_PASSWORD", "SPLUNK_AO_PASSWORD", "GALILEO_PASSWORD → SPLUNK_AO_PASSWORD"),
    Rule("GALILEO_PROJECT", "SPLUNK_AO_PROJECT", "GALILEO_PROJECT → SPLUNK_AO_PROJECT"),
    Rule("GALILEO_LOG_LEVEL", "SPLUNK_AO_LOG_LEVEL", "GALILEO_LOG_LEVEL → SPLUNK_AO_LOG_LEVEL"),
    Rule("GALILEO_MODE", "SPLUNK_AO_MODE", "GALILEO_MODE → SPLUNK_AO_MODE"),
    Rule("GALILEO_HOME_DIR", "SPLUNK_AO_HOME_DIR", "GALILEO_HOME_DIR → SPLUNK_AO_HOME_DIR"),
]

# ---------------------------------------------------------------------------
# 5. HTTP tracing header string literals
# ---------------------------------------------------------------------------
HEADER_RULES: list[Rule] = [
    Rule("X-Galileo-Trace-ID", "Splunk-AO-Trace-ID", "X-Galileo-Trace-ID → Splunk-AO-Trace-ID"),
    Rule("X-Galileo-Parent-ID", "Splunk-AO-Parent-ID", "X-Galileo-Parent-ID → Splunk-AO-Parent-ID"),
    # API key header — must come before BRAND_RULES so "Galileo-API-Key" → "Splunk-AO-API-Key"
    # (hyphenated) rather than "Splunk AO-API-Key" (with space) which BRAND_RULES would produce.
    Rule("Galileo-API-Key", "Splunk-AO-API-Key", "Galileo-API-Key → Splunk-AO-API-Key"),
]

# ---------------------------------------------------------------------------
# 6. Documentation URL rewrites
#    Must run before BRAND_RULES so full URLs are rewritten as atomic units
#    rather than having their path fragments partially matched by symbol rules.
#    The transformer's _sub_outside_urls guard does NOT apply here — these rules
#    match the full URL and replace it with another URL, so they are applied via
#    a separate pass that operates directly on URLs.
# ---------------------------------------------------------------------------
DOC_URL_RULES: list[Rule] = [
    Rule(
        pattern=r"https://docs\.galileo\.ai/",
        replacement="https://agent-observability-docs.splunk.com/",
        description="docs.galileo.ai → agent-observability-docs.splunk.com",
    ),
    Rule(
        pattern=r"/add-galileo-to-crewai/add-galileo-to-crewai\b",
        replacement="/add-splunk-ao-to-crewai/add-splunk-ao-to-crewai",
        description="add-galileo-to-crewai URL path → add-splunk-ao-to-crewai",
    ),
    # Filename references in docs: -galileo.md → -splunk-ao.md
    # The generic galileo import rule excludes galileo.md (treats .md as a TLD),
    # so this handles the case explicitly.
    Rule(
        pattern=r"-galileo\.md\b",
        replacement="-splunk-ao.md",
        description="-galileo.md filename reference → -splunk-ao.md",
    ),
    # Filename references in docs: -galileo.txt → -splunk-ao.txt
    # (e.g. requirements-galileo.txt in code-fence install instructions)
    Rule(
        pattern=r"-galileo\.txt\b",
        replacement="-splunk-ao.txt",
        description="-galileo.txt filename reference → -splunk-ao.txt",
    ),
    # Specific doc page path: what-is-galileo → what-is-splunk-agent-observability
    Rule(
        pattern=r"/what-is-galileo\b",
        replacement="/what-is-splunk-agent-observability",
        description="what-is-galileo doc path → what-is-splunk-agent-observability",
    ),
    # Doc path restructure: getting-started/logging → concepts/logging/overview
    Rule(
        pattern=r"/getting-started/logging\b",
        replacement="/concepts/logging/overview",
        description="getting-started/logging doc path → concepts/logging/overview",
    ),
    # Doc path restructure: concepts/experiments/overview → sdk-api/experiments/experiments
    Rule(
        pattern=r"/concepts/experiments/overview\b",
        replacement="/sdk-api/experiments/experiments",
        description="concepts/experiments/overview → sdk-api/experiments/experiments",
    ),
]

# Placeholder string fix for doc files.
# The generic galileo → splunk_ao import rule (IMPORT_RULES) rewrites
# placeholder values like "your-galileo-api-key" → "your-splunk_ao-api-key"
# (underscore). In prose and code-fence examples the hyphenated form
# "your-splunk-ao-*" is correct. This pass corrects the over-rewrite.
# Must run AFTER PYTHON_RULES so it fixes what the import rule produced.
DOC_PLACEHOLDER_RULES: list[Rule] = [
    Rule(
        pattern=r"\byour-splunk_ao-",
        replacement="your-splunk-ao-",
        description="your-splunk_ao-* placeholder → your-splunk-ao-* (hyphenated form in prose)",
    ),
    # Lowercase 'galileo' in prose (e.g. table cells, sentences) gets rewritten by the
    # import rule to 'splunk_ao' (underscore) instead of 'Splunk AO' (brand name).
    # Correct it here: match splunk_ao only when surrounded by non-identifier chars
    # (spaces, punctuation, end-of-line) so Python identifiers like splunk_ao_context
    # are not affected.
    # Exclusions:
    #   (?<!`) — skip backtick-quoted identifiers (`splunk_ao`)
    #   (?<!from ) — skip Python import statements (from splunk_ao import ...)
    #   (?<!import ) — skip bare import statements (import splunk_ao)
    #   (?![_\w]) — skip when followed by identifier chars (splunk_ao_context etc.)
    #   (?!\.) — skip when followed by a dot (splunk_ao.handlers module paths)
    Rule(
        pattern=r"(?<![_\w`])(?<!from )(?<!import )splunk_ao(?![_\w.])",
        replacement="Splunk AO",
        description="splunk_ao in prose position → Splunk AO (brand name, not a Python identifier)",
    ),
]

# ---------------------------------------------------------------------------
# 7. Human-readable brand name in comments and docstrings
#    Must come after all code-level rules so "Galileo" as a bare word in
#    comments ("# Galileo CrewAI integration") is renamed to "Splunk AO".
#    Word-boundary guards prevent matching inside compound identifiers like
#    GalileoLogger (already handled above) or X-Galileo-* (handled above).
# ---------------------------------------------------------------------------
BRAND_RULES: list[Rule] = [
    # "Galileo.ai" used as a product/brand name in prose (not inside a URL).
    # Must come before the general Galileo rule whose TLD guard would skip it.
    # The URL guard in _sub_outside_urls still prevents rewriting inside https://... links.
    Rule(r"\bGalileo\.ai\b", "Splunk AO", "Galileo.ai → Splunk AO (brand name in prose)"),
    # Exclude domain names: skip when followed by a short TLD (.ai, .com, .io etc. — 2-3 chars).
    # Full URL skipping is handled in transformer.py._sub_outside_urls.
    Rule(r"\bGalileo(?!\.[a-z]{2,3}\b)\b", "Splunk AO", "Galileo → Splunk AO (brand name in comments/text)"),
    # ALL-CAPS brand name in comments (e.g. # 👀 GALILEO API KEY CHECK).
    # Must not match GALILEO_* env-var names (handled by ENV_VAR_RULES) — exclude when
    # followed by underscore or uppercase letter continuing an identifier.
    Rule(r"\bGALILEO(?![_A-Z])\b", "SPLUNK AO", "GALILEO → SPLUNK AO (all-caps brand in comments)"),
]

# ---------------------------------------------------------------------------
# 8. Warning-only rules (detected but not auto-fixed)
# ---------------------------------------------------------------------------
WARNING_RULES: list[Rule] = [
    Rule(
        pattern=r"\binvoke_protect\b|\bainvoke_protect\b|\bcreate_protect_stage\b"
                r"|\bget_protect_stage\b|\bpause_protect_stage\b"
                r"|\bresume_protect_stage\b|\bupdate_protect_stage\b",
        replacement="",
        description="Protect feature usage — keep 'galileo' as a dependency; "
                    "Protect is not available in splunk-ao",
        is_warning=True,
    ),
    Rule(
        pattern=r"\bgalileo_core\b",
        replacement="",
        description="galileo_core import detected — galileo_core is a low-level internal "
                    "dependency that is NOT renamed to splunk_ao_core. Keep these imports as-is. "
                    "Review any galileo_core types (e.g. Metrics) used in your code; they are "
                    "internal types and should not be renamed to the splunk-ao public API names.",
        is_warning=True,
    ),
    Rule(
        pattern=r"\bGALILEO_OBSERVE_KEY\b",
        replacement="",
        description="GALILEO_OBSERVE_KEY is an OTel interop constant shared with external "
                    "systems — do not rename; verify manually whether it should stay as-is",
        is_warning=True,
    ),
    Rule(
        pattern=r'["\']GALILEO_["\']?\s*\+|f["\'].*GALILEO_\{',
        replacement="",
        description="Dynamic GALILEO_* env-var construction — cannot be auto-rewritten; "
                    "review manually",
        is_warning=True,
    ),
    Rule(
        pattern=r'(["\'])(?:(?!\1).)*\bgalileo\b(?:(?!\1).)*\1',
        replacement="",
        description="Lowercase 'galileo' inside a string literal — may refer to the astronomer "
                    "or other non-SDK usage; verify whether it should be renamed or left as-is",
        is_warning=True,
    ),
]

# ---------------------------------------------------------------------------
# Ordered rule sets for Python files
# ---------------------------------------------------------------------------
PYTHON_RULES: list[Rule] = (
    IMPORT_RULES
    + SYMBOL_RULES
    + KWARG_RULES
    + ENV_VAR_RULES
    + HEADER_RULES
    + BRAND_RULES
)

# Kwarg rules that are safe to apply in doc files (code-fence examples).
# log_stream_name= and log_stream= only appear as Python kwargs — never as
# bare string-value keys — so they can be rewritten in docs without risk.
# logstream= (no underscore) is excluded because it appears inside env-var
# string values like TRACELOOP_HEADERS="..., logstream=default, ..." and
# would be incorrectly rewritten there.
_DOC_KWARG_RULES: list[Rule] = [r for r in KWARG_RULES if "log_stream" in r.pattern]

# Rules for doc file prose pass (same as PYTHON_RULES but without logstream=).
# logstream= must not run on .md/.rst files because it appears inside string
# values (e.g. TRACELOOP_HEADERS="..., logstream=default") and would be
# incorrectly rewritten as a Python kwarg. log_stream= is safe — see above.
DOC_PROSE_RULES: list[Rule] = (
    IMPORT_RULES
    + SYMBOL_RULES
    + _DOC_KWARG_RULES
    + ENV_VAR_RULES
    + HEADER_RULES
    + BRAND_RULES
)

# Rules for Markdown / RST documentation files.
# DOC_URL_RULES run first so full URLs are rewritten atomically before the
# remaining PYTHON_RULES touch brand names and symbol fragments inside prose.
# Note: DOC_URL_RULES are applied via a dedicated URL-aware pass in migrate.py
# (transform_doc) that does NOT skip URL tokens, allowing full URL replacement.
DOC_RULES: list[Rule] = DOC_URL_RULES + PYTHON_RULES

# Rules for .env files: env-var key renames + galileo in placeholder values (e.g. your-galileo-key)
_ENV_VALUE_RULES: list[Rule] = [
    # galileo surrounded by underscores in placeholder tokens (e.g. your_galileo_api_key_here)
    Rule(
        pattern=r"(?<=_)galileo(?=_)",
        replacement="splunk_ao",
        description="galileo → splunk_ao inside underscore-delimited placeholder tokens",
    ),
    Rule(
        pattern=r"\bgalileo(?!\.[a-z]{2,3}\b)\b",
        replacement="splunk-ao",
        description="galileo → splunk-ao in .env placeholder values",
    ),
]
# HEADER_RULES must come before BRAND_RULES so "Galileo-API-Key" → "Splunk-AO-API-Key"
# (hyphenated) rather than "Splunk AO-API-Key" (with space) which BRAND_RULES would produce.
ENV_FILE_RULES: list[Rule] = ENV_VAR_RULES + HEADER_RULES + _ENV_VALUE_RULES + BRAND_RULES

# Rules for requirements*.txt / pyproject.toml
DEP_RULES: list[Rule] = [
    Rule(r"\bgalileo-adk\b", "splunk-ao-adk", "galileo-adk → splunk-ao-adk"),
    Rule(r"\bgalileo-a2a\b", "splunk-ao-a2a", "galileo-a2a → splunk-ao-a2a"),
    # galileo_a2a Python package/module identifier → splunk_ao_a2a
    Rule(r"\bgalileo_a2a\b", "splunk_ao_a2a", "galileo_a2a → splunk_ao_a2a"),
    # galileo_adk Python package/module identifier → splunk_ao_adk
    Rule(r"\bgalileo_adk\b", "splunk_ao_adk", "galileo_adk → splunk_ao_adk"),
    # uv sources key: { galileo = ... } → { "splunk-ao" = ... }
    # hyphen makes "splunk-ao" an invalid bare TOML key, so it must be quoted.
    Rule(
        pattern=r"\bgalileo(\s*=\s*\{)",
        replacement=r'"splunk-ao"\1',
        description='sources = { galileo = ... } → sources = { "splunk-ao" = ... }',
    ),
    # pyproject.toml project name: name = "galileo-*" → name = "splunk-ao-*"
    # Must come before the bare galileo rule whose lookahead excludes hyphen-prefixed names.
    Rule(
        pattern=r'(name\s*=\s*["\'])galileo-',
        replacement=r'\1splunk-ao-',
        description='name = "galileo-*" → name = "splunk-ao-*" (pyproject.toml project name)',
    ),
    # bare 'galileo' package name (not as part of galileo-adk/galileo_a2a etc.)
    # Exclusions:
    #   (?<![a-z\-@])  — skip email addresses (team@galileo.ai) and hyphen-prefixed names
    #   (?![-a-z_.])   — skip galileo-adk, galileo_a2a, galileo.ai etc.
    Rule(r"(?<![a-z\-@])galileo(?![-a-z_.])", "splunk-ao", "galileo → splunk-ao (package name)"),
    # GALILEO_* env-var strings inside pyproject.toml pytest env = [...] blocks
    # (same substitutions as ENV_VAR_RULES but applied in the TOML context)
] + ENV_VAR_RULES + [
    # splunk-ao requires Python >=3.11; bump any lower floor in requires-python.
    # Captures the opening quote so the replacement preserves the original quote style.
    Rule(
        pattern=r'(requires-python\s*=\s*)(["\'])>=3\.(?:8|9|10)',
        replacement=r'\1\2>=3.11',
        description="requires-python floor < 3.11 → >=3.11 (splunk-ao minimum)",
    ),
] + BRAND_RULES
