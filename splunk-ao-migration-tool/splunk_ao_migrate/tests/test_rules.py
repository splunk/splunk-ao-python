"""
Table-driven regression tests for splunk_ao_migrate rules and transformer.

Each test group covers one rule area and is structured as:
  # Given: source content
  # When: transform is applied
  # Then: expected output / warnings

Run with:  uv run pytest
"""

from __future__ import annotations

import pathlib
import py_compile
import tempfile
import os

import pytest

from splunk_ao_migrate.rules import (
    DEP_RULES,
    DOC_PLACEHOLDER_RULES,
    DOC_PROSE_RULES,
    DOC_URL_RULES,
    ENV_FILE_RULES,
    PYTHON_RULES,
    WARNING_RULES,
)
from splunk_ao_migrate.transformer import transform, transform_urls
from splunk_ao_migrate.migrate import collect_path_renames, migrate_file


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def py(src: str) -> str:
    """Apply PYTHON_RULES + WARNING_RULES to src and return the rewritten content."""
    return transform(src, PYTHON_RULES, WARNING_RULES, python_mode=True).content


def py_warnings(src: str) -> list[str]:
    """Return the warning descriptions produced for src."""
    return [w.rule_description for w in transform(src, PYTHON_RULES, WARNING_RULES, python_mode=True).warnings]


def doc(src: str) -> str:
    """Apply the three-pass doc pipeline to src and return rewritten content."""
    url_tr = transform_urls(src, DOC_URL_RULES)
    prose_tr = transform(url_tr.content, DOC_PROSE_RULES, WARNING_RULES)
    ph_tr = transform_urls(prose_tr.content, DOC_PLACEHOLDER_RULES)
    return ph_tr.content


def dep(src: str) -> str:
    """Apply DEP_RULES to src and return rewritten content."""
    return transform(src, DEP_RULES).content


def dep_warnings(src: str) -> list[str]:
    """Return warning descriptions for dep/toml content (no WARNING_RULES on this branch)."""
    return [w.rule_description for w in transform(src, DEP_RULES).warnings]


def compiles(src: str) -> bool:
    """Return True if src is valid Python."""
    fd, tmp = tempfile.mkstemp(suffix=".py")
    try:
        os.write(fd, src.encode())
        os.close(fd)
        py_compile.compile(tmp, doraise=True)
        return True
    except py_compile.PyCompileError:
        return False
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# 1. Import rules
# ---------------------------------------------------------------------------

class TestImportRules:
    def test_generic_galileo_module(self):
        # Given: a galileo module import
        # When: transformed
        # Then: module renamed to splunk_ao
        assert py("import galileo\n") == "import splunk_ao\n"

    def test_from_galileo_import(self):
        assert "from splunk_ao import" in py("from galileo import galileo_context\n")

    def test_galileo_metric_module(self):
        # galileo.metric must become splunk_ao.evaluator, not splunk_ao.metric
        assert "splunk_ao.evaluator" in py("from galileo.metric import LlmMetric\n")
        assert "splunk_ao.metric" not in py("from galileo.metric import LlmMetric\n")

    def test_galileo_a2a_hyphenated_literal(self):
        # "galileo-a2a" in a string must become "splunk-ao-a2a" (hyphenated)
        assert '"splunk-ao-a2a"' in py('pkg = "galileo-a2a"\n')

    def test_galileo_adk_identifier(self):
        assert "splunk_ao_adk" in py("from galileo_adk import plugin\n")

    def test_galileo_a2a_identifier(self):
        assert "splunk_ao_a2a" in py("from galileo_a2a import client\n")

    def test_config_file_rename_python_config(self):
        # galileo-python-config.json must become splunk-ao-config.json
        # (not splunk_ao-python-config.json which the generic rule would produce)
        result = py('path = "galileo-python-config.json"\n')
        assert "splunk-ao-config.json" in result
        assert "splunk_ao" not in result

    def test_config_file_rename_galileo_config(self):
        result = py('path = "galileo-config.json"\n')
        assert "splunk-ao-config.json" in result

    def test_domain_name_not_renamed(self):
        # galileo.ai as a domain (in a URL) must not be renamed
        result = py('url = "https://galileo.ai/login"\n')
        assert "galileo.ai" in result

    def test_protect_import_line_left_intact(self):
        # Given: a line importing a Protect symbol
        # When: transformed
        # Then: the entire line is left unchanged and a warning is emitted
        src = "from galileo import invoke_protect\n"
        assert "galileo import invoke_protect" in py(src)
        assert any("Protect" in w for w in py_warnings(src))

    def test_protect_mixed_with_normal_import_on_same_line(self):
        # A line with both a Protect symbol and galileo_context: whole line left intact
        src = "from galileo import invoke_protect, galileo_context\n"
        assert "galileo import invoke_protect" in py(src)

    def test_normal_import_on_separate_line_still_renamed(self):
        src = "from galileo import galileo_context\nfrom galileo import invoke_protect\n"
        result = py(src)
        assert "from splunk_ao import splunk_ao_context" in result
        assert "galileo import invoke_protect" in result


# ---------------------------------------------------------------------------
# 2. Symbol rules
# ---------------------------------------------------------------------------

class TestSymbolRules:
    @pytest.mark.parametrize("old,new", [
        ("GalileoLogger", "SplunkAOLogger"),
        ("GalileoCallback", "SplunkAOCallback"),
        ("GalileoAsyncCallback", "SplunkAOAsyncCallback"),
        ("GalileoSpanProcessor", "SplunkAOSpanProcessor"),
        ("add_galileo_span_processor", "add_splunk_ao_span_processor"),
        ("start_galileo_span", "start_splunk_ao_span"),
        ("GalileoPythonConfig", "SplunkAOConfig"),
        ("GalileoMiddleware", "SplunkAOMiddleware"),
        ("GalileoADKPlugin", "SplunkAOADKPlugin"),
        ("GalileoEventListener", "CrewAIEventListener"),
        ("GalileoMetric", "SplunkAOEvaluator"),
        ("GalileoMetrics", "SplunkAOEvaluators"),
        ("galileo_context", "splunk_ao_context"),
        ("LogStream", "AgentStream"),
        ("LogStreams", "AgentStreams"),
        ("create_log_stream", "create_agent_stream"),
        ("list_log_streams", "list_agent_streams"),
        ("enable_metrics", "enable_evaluators"),
        ("delete_metric", "delete_evaluator"),
        ("create_custom_llm_metric", "create_custom_llm_evaluator"),
        ("BuiltInMetrics", "BuiltInEvaluators"),
        ("LlmMetric", "LlmEvaluator"),
        ("LocalMetric", "LocalEvaluator"),
        ("CodeMetric", "CodeEvaluator"),
    ])
    def test_symbol_renamed(self, old, new):
        assert new in py(f"x = {old}\n")

    def test_metric_renamed(self):
        assert "Evaluator" in py("result: Metric = ...\n")

    def test_metrics_renamed(self):
        assert "Evaluators" in py("scorers: Metrics = []\n")

    def test_galileo_core_metrics_not_renamed(self):
        # Given: Metrics imported from galileo_core
        # When: transformed
        # Then: Metrics is preserved on that line (galileo_core types must not be renamed)
        src = "from galileo_core.schemas.metrics import Metrics\n"
        result = py(src)
        assert "Metrics" in result
        assert "Evaluators" not in result

    def test_galileo_core_metric_not_renamed(self):
        src = "from galileo_core.schemas.metrics import Metric\n"
        result = py(src)
        assert "Metric" in result
        assert "Evaluator" not in result

    def test_galileo_core_warning_emitted(self):
        src = "from galileo_core.schemas.metrics import Metrics\n"
        assert any("galileo_core" in w for w in py_warnings(src))

    def test_galileo_core_suppression_is_file_scoped(self):
        # The suppression is FILE-scoped: any Metric/Evaluator rename is suppressed
        # across the entire file if the file imports from galileo_core, even on
        # lines that do not themselves contain 'galileo_core'.
        # This prevents `metrics=Metrics(...)` call sites (different lines from the
        # import) from being incorrectly renamed to `metrics=Evaluators(...)`.
        src = "from galileo_core.schemas.logging.step import Metrics\nmetrics=Metrics(duration_ns=0)\n"
        result = py(src)
        lines = result.splitlines()
        assert "Metrics" in lines[0]     # import line: galileo_core kept, Metrics not renamed
        assert "Metrics" in lines[1]     # call site: Metrics NOT renamed (file-scoped suppression)
        assert "Evaluators" not in result

    def test_galileo_observe_key_constant_renamed(self):
        assert "SPLUNK_AO_OBSERVE_KEY" in py("key = GALILEO_OBSERVE_KEY\n")

    def test_galileo_observe_wire_value_renamed(self):
        # Given: the A2A wire value string
        # When: transformed
        # Then: wire value updated to match splunk-ao-a2a
        assert '"splunk_ao_observe"' in py('k = "galileo_observe"\n')

    def test_galileo_embedded_in_identifier(self):
        assert "_splunk_ao_logger" in py("self._galileo_logger\n")

    def test_log_stream_bare_identifier(self):
        assert "agent_stream" in py("log_stream: str = None\n")

    def test_log_stream_name_identifier(self):
        # log_stream_name is caught by the \blog_stream_name\b SYMBOL_RULE (not a kwarg rule)
        assert "agent_stream_name=" in py("foo(log_stream_name=x)\n")

    def test_log_stream_name_typed_param(self):
        # \blog_stream_name\b catches typed parameter declarations too
        assert "agent_stream_name: str" in py("def fn(log_stream_name: str = ''):\n")

    def test_log_stream_kwarg_via_symbol_rule(self):
        # log_stream= is caught by the \blog_stream\b SYMBOL_RULE (not a kwarg rule)
        assert "agent_stream=" in py("foo(log_stream=x)\n")

    def test_logstreams_attribute(self):
        assert ".agent_streams" in py("p.logstreams\n")


# ---------------------------------------------------------------------------
# 3. Kwarg rules
# ---------------------------------------------------------------------------

class TestKwargRules:
    def test_logstream_kwarg_in_python(self):
        # logstream= (no underscore) has no SYMBOL_RULE counterpart — caught by KWARG_RULES
        assert "agentstream=" in py("foo(logstream=x)\n")


# ---------------------------------------------------------------------------
# 4. Env-var rules
# ---------------------------------------------------------------------------

class TestEnvVarRules:
    @pytest.mark.parametrize("old,new", [
        ("GALILEO_API_KEY", "SPLUNK_AO_API_KEY"),
        ("GALILEO_API_ENDPOINT", "SPLUNK_AO_API_ENDPOINT"),
        ("GALILEO_PROJECT", "SPLUNK_AO_PROJECT"),
        ("GALILEO_LOG_STREAM", "SPLUNK_AO_AGENT_STREAM"),
        ("GALILEO_LOGSTREAM", "SPLUNK_AO_AGENT_STREAM"),
        ("GALILEO_LOG_STREAM_ID", "SPLUNK_AO_AGENT_STREAM_ID"),
        ("GALILEO_CONSOLE_URL", "SPLUNK_AO_CONSOLE_URL"),
        ("GALILEO_API_URL", "SPLUNK_AO_API_URL"),
        ("GALILEO_HOME_DIR", "SPLUNK_AO_HOME_DIR"),
    ])
    def test_env_var_renamed(self, old, new):
        assert new in py(f'os.environ.get("{old}")\n')


# ---------------------------------------------------------------------------
# 5. Header rules
# ---------------------------------------------------------------------------

class TestHeaderRules:
    @pytest.mark.parametrize("old,new", [
        ("X-Galileo-Trace-ID", "Splunk-AO-Trace-ID"),
        ("X-Galileo-Parent-ID", "Splunk-AO-Parent-ID"),
        ("X-Galileo-SDK", "Splunk-AO-SDK"),
        ("Galileo-API-Key", "Splunk-AO-API-Key"),
    ])
    def test_header_renamed(self, old, new):
        assert new in py(f'headers = {{"{old}": value}}\n')

    def test_unknown_x_galileo_header_not_mangled(self):
        # Unknown X-Galileo-* headers must not produce "X-Splunk AO-*" (space = invalid)
        result = py('h = {"X-Galileo-Custom": x}\n')
        assert "X-Splunk AO" not in result
        assert "Splunk AO" not in result


# ---------------------------------------------------------------------------
# 6. Brand rules — position-aware (Python files)
# ---------------------------------------------------------------------------

class TestBrandRulesPython:
    def test_galileo_in_comment_renamed(self):
        assert "# Splunk AO logger" in py("# Galileo logger\n")

    def test_galileo_all_caps_in_comment_renamed(self):
        assert "SPLUNK AO" in py("# GALILEO API KEY CHECK\n")

    def test_galileo_in_inline_comment_renamed(self):
        result = py("x = foo()  # Galileo integration\n")
        assert "Splunk AO integration" in result

    def test_galileo_in_docstring_renamed(self):
        assert "Splunk AO" in py('"""Initialize the Galileo logger."""\n')

    def test_galileo_in_indented_docstring_renamed(self):
        assert "Splunk AO" in py('    """Initialize the Galileo logger."""\n')

    def test_galileo_code_position_not_renamed(self):
        # Given: Galileo as a code token (identifier, class name, constant)
        # When: transformed
        # Then: not renamed — would produce SyntaxError
        assert "Splunk AO" not in py("GALILEO = 1\n")
        assert "Splunk AO" not in py("class Galileo:\n    pass\n")
        assert "Splunk AO" not in py("x = Galileo()\n")

    def test_code_position_output_still_compiles(self):
        # Given: various Galileo identifiers in code positions
        src = "GALILEO = 1\nclass Galileo:\n    pass\nx = Galileo()\n"
        result = py(src)
        assert compiles(result)

    def test_inline_comment_code_part_untouched(self):
        # Code before # must not be renamed; comment after # must be renamed
        result = py("result = Galileo()  # returns Galileo instance\n")
        assert "Galileo()" in result          # code token preserved
        assert "Splunk AO instance" in result  # comment renamed

    def test_galileo_ai_brand_in_comment(self):
        assert "Splunk AO" in py("# Visit Galileo.ai for docs\n")


# ---------------------------------------------------------------------------
# 7. Brand rules — doc files (all positions safe)
# ---------------------------------------------------------------------------

class TestBrandRulesDoc:
    def test_galileo_in_prose_renamed(self):
        assert "Splunk AO" in doc("Galileo provides observability.\n")

    def test_galileo_in_heading_renamed(self):
        assert "Splunk AO" in doc("# Galileo Integration\n")

    def test_galileo_url_not_renamed(self):
        result = doc("See https://docs.galileo.ai/overview for details.\n")
        assert "galileo.ai" not in result  # URL rewritten by DOC_URL_RULES
        assert "agent-observability-docs.splunk.com" in result


# ---------------------------------------------------------------------------
# 8. Doc pipeline
# ---------------------------------------------------------------------------

class TestDocPipeline:
    def test_url_rewritten(self):
        result = doc("See https://docs.galileo.ai/getting-started.\n")
        assert "agent-observability-docs.splunk.com" in result

    def test_pip_install_operand(self):
        # Given: pip install galileo in docs
        # When: doc pipeline applied
        # Then: pip install splunk-ao (hyphenated, not "Splunk AO")
        result = doc("pip install galileo\n")
        assert "pip install splunk-ao" in result
        assert "Splunk AO" not in result

    def test_pip_install_with_extra(self):
        result = doc("pip install galileo[langchain]\n")
        assert "pip install splunk-ao[langchain]" in result

    def test_uv_add_operand(self):
        result = doc("uv add galileo\n")
        assert "uv add splunk-ao" in result

    def test_poetry_add_operand(self):
        result = doc("poetry add galileo\n")
        assert "poetry add splunk-ao" in result

    def test_idempotency_pip_install(self):
        # Given: already-migrated pip install line
        # When: doc pipeline applied again
        # Then: output is unchanged (idempotent)
        already_migrated = "pip install splunk-ao\n"
        assert doc(already_migrated) == already_migrated

    def test_idempotency_prose(self):
        # Given: already-migrated prose
        # When: doc pipeline applied again
        # Then: output is unchanged
        already_migrated = "Splunk AO provides observability.\n"
        assert doc(already_migrated) == already_migrated

    def test_logstream_in_env_var_string_not_renamed(self):
        # logstream= inside a TRACELOOP_HEADERS value must not be renamed
        src = 'TRACELOOP_HEADERS="..., logstream=default, ..."\n'
        result = doc(src)
        assert "logstream=default" in result
        assert "agentstream=" not in result

    def test_your_galileo_placeholder_hyphenated(self):
        # your-galileo-api-key placeholder must become your-splunk-ao-api-key (hyphen)
        result = doc("your-galileo-api-key\n")
        assert "your-splunk-ao-api-key" in result
        assert "your-splunk_ao-api-key" not in result

    def test_hyphenated_package_name_in_prose_not_mangled(self):
        # galileo-adk → splunk_ao-adk (by IMPORT_RULES) → splunk-ao-adk (by placeholder rule)
        # Must NOT become "Splunk AO-adk"
        result = doc("Contributing to galileo-adk\n")
        assert "splunk-ao-adk" in result
        assert "Splunk AO-adk" not in result
        assert "splunk_ao-adk" not in result

    def test_hyphenated_package_python_in_prose(self):
        # galileo-python → splunk-ao-python in prose
        result = doc("part of the galileo-python monorepo\n")
        assert "splunk-ao-python" in result
        assert "Splunk AO-python" not in result

    def test_path_token_not_renamed_to_brand(self):
        # src/galileo/ → src/splunk_ao/ — path token must keep underscore form, not become prose
        result = doc("├── src/galileo/        ← Main SDK\n")
        assert "src/splunk_ao/" in result
        assert "src/Splunk AO/" not in result


# ---------------------------------------------------------------------------
# 9. Dep/toml rules
# ---------------------------------------------------------------------------

class TestDepRules:
    def test_galileo_package_renamed(self):
        assert "splunk-ao" in dep('dependencies = ["galileo>=1.32"]\n')

    def test_galileo_adk_dep_renamed(self):
        assert "splunk-ao-adk" in dep('dependencies = ["galileo-adk>=1.0"]\n')

    def test_galileo_a2a_dep_renamed(self):
        assert "splunk-ao-a2a" in dep('dependencies = ["galileo-a2a>=1.0"]\n')

    def test_requires_python_floor_bumped(self):
        assert '>=3.11"' in dep('requires-python = ">=3.10"\n')

    def test_requires_python_floor_with_patch_not_mangled(self):
        # >=3.10.1 should become >=3.11, not >=3.11.1
        result = dep('requires-python = ">=3.10.1"\n')
        assert ">=3.11" in result
        assert "3.11.1" not in result

    def test_poetry_python_floor_bumped_caret(self):
        assert "^3.11" in dep('python = "^3.10"\n')

    def test_poetry_python_floor_bumped_gte(self):
        assert ">=3.11" in dep('python = ">=3.10"\n')

    def test_no_spurious_string_literal_warning(self):
        # Given: galileo as a dep string in pyproject.toml
        # When: dep rules applied (no WARNING_RULES on this branch)
        # Then: no "astronomer" warning emitted
        warnings = dep_warnings('dependencies = ["galileo>=1.32"]\n')
        assert not any("astronomer" in w for w in warnings)

    def test_uv_sources_key_renamed(self):
        result = dep("galileo = {git = ...}\n")
        assert "splunk-ao" in result


# ---------------------------------------------------------------------------
# 10. Env file rules
# ---------------------------------------------------------------------------

class TestEnvFileRules:
    def test_env_var_renamed(self):
        result = transform("GALILEO_API_KEY=abc\n", ENV_FILE_RULES).content
        assert "SPLUNK_AO_API_KEY=abc" in result

    def test_galileo_api_key_header_renamed(self):
        result = transform('TRACELOOP_HEADERS="Galileo-API-Key=key"\n', ENV_FILE_RULES).content
        assert "Splunk-AO-API-Key" in result

    def test_placeholder_value_hyphenated(self):
        result = transform("SPLUNK_AO_API_KEY=your-galileo-api-key\n", ENV_FILE_RULES).content
        assert "your-splunk-ao-api-key" in result


# ---------------------------------------------------------------------------
# 11. Warning rules
# ---------------------------------------------------------------------------

class TestWarningRules:
    def test_protect_symbol_emits_warning(self):
        src = "from galileo import invoke_protect\n"
        assert any("Protect" in w for w in py_warnings(src))

    def test_galileo_core_emits_warning(self):
        src = "from galileo_core.schemas.metrics import Metrics\n"
        assert any("galileo_core" in w for w in py_warnings(src))

    def test_lowercase_galileo_string_literal_emits_warning(self):
        src = 'question = "what moons did galileo discover"\n'
        assert any("astronomer" in w for w in py_warnings(src))

    def test_dynamic_env_var_emits_warning(self):
        src = 'key = "GALILEO_" + suffix\n'
        assert any("Dynamic" in w for w in py_warnings(src))


# ---------------------------------------------------------------------------
# 12. collect_path_renames
# ---------------------------------------------------------------------------

class TestCollectPathRenames:
    def test_file_arg_only_renames_that_file(self, tmp_path):
        # Given: a file arg plus an unrelated sibling containing "galileo"
        # When: collect_path_renames called with just the file
        # Then: only the target file is in the rename list, not the sibling
        target = tmp_path / "galileo_helper.py"
        sibling = tmp_path / "unrelated_galileo_notes.md"
        target.write_text("x")
        sibling.write_text("y")

        renames = collect_path_renames([str(target)])
        renamed_names = [new.name for _, new in renames]

        assert "splunk_ao_helper.py" in renamed_names
        assert not any("unrelated" in n for n in renamed_names)

    def test_nonexistent_path_skipped(self, tmp_path):
        # Given: a nonexistent path
        # When: collect_path_renames called
        # Then: no renames produced, no crash
        renames = collect_path_renames([str(tmp_path / "does_not_exist")])
        assert renames == []

    def test_directory_arg_renames_children(self, tmp_path):
        # Given: a directory containing galileo-named files
        # When: collect_path_renames called with the directory
        # Then: all galileo-named entries are in the rename list
        (tmp_path / "galileo_agent.py").write_text("x")
        (tmp_path / "no_match.py").write_text("y")

        renames = collect_path_renames([str(tmp_path)])
        renamed_names = [new.name for _, new in renames]

        assert "splunk_ao_agent.py" in renamed_names
        assert "no_match.py" not in renamed_names

    def test_deepest_first_ordering(self, tmp_path):
        # Given: nested galileo directories
        # When: collect_path_renames called
        # Then: deepest paths come first (so child renames happen before parent)
        nested = tmp_path / "galileo_pkg" / "galileo_sub"
        nested.mkdir(parents=True)
        (nested / "galileo_file.py").write_text("x")

        renames = collect_path_renames([str(tmp_path)])
        paths = [str(old) for old, _ in renames]

        # The deepest path must appear before shallower ones
        file_idx = next(i for i, p in enumerate(paths) if "galileo_file" in p)
        sub_idx = next(i for i, p in enumerate(paths) if p.endswith("galileo_sub"))
        pkg_idx = next(i for i, p in enumerate(paths) if p.endswith("galileo_pkg"))

        assert file_idx < sub_idx < pkg_idx


# ---------------------------------------------------------------------------
# 13. migrate_file — protect_in_scope skips dep/toml files
# ---------------------------------------------------------------------------

class TestMigrateFileProtect:
    def test_dep_file_skipped_when_protect_in_scope(self, tmp_path):
        # Given: a requirements.txt that would normally be migrated
        # When: migrate_file called with protect_in_scope=True
        # Then: file is skipped and galileo dependency is preserved
        req = tmp_path / "requirements.txt"
        req.write_text("galileo>=1.32\n")

        result = migrate_file(req, dry_run=False, protect_in_scope=True)

        assert result.skipped
        assert "Protect" in result.skip_reason
        assert req.read_text() == "galileo>=1.32\n"  # file untouched

    def test_toml_file_skipped_when_protect_in_scope(self, tmp_path):
        # Given: a pyproject.toml with galileo dependency
        # When: migrate_file called with protect_in_scope=True
        # Then: file is skipped and content unchanged
        toml = tmp_path / "pyproject.toml"
        toml.write_text('dependencies = ["galileo>=1.32"]\n')

        result = migrate_file(toml, dry_run=False, protect_in_scope=True)

        assert result.skipped
        assert toml.read_text() == 'dependencies = ["galileo>=1.32"]\n'

    def test_dep_file_migrated_when_protect_not_in_scope(self, tmp_path):
        # Given: a requirements.txt with galileo dependency
        # When: migrate_file called with protect_in_scope=False (default)
        # Then: galileo is renamed to splunk-ao
        req = tmp_path / "requirements.txt"
        req.write_text("galileo>=1.32\n")

        result = migrate_file(req, dry_run=False, protect_in_scope=False)

        assert not result.skipped
        assert req.read_text() == "splunk-ao>=1.32\n"

    def test_python_file_not_affected_by_protect_in_scope(self, tmp_path):
        # Given: a Python file with galileo import
        # When: migrate_file called with protect_in_scope=True
        # Then: Python file is still migrated normally (protect only gates dep/toml)
        py_file = tmp_path / "main.py"
        py_file.write_text("from galileo import galileo_context\n")

        result = migrate_file(py_file, dry_run=False, protect_in_scope=True)

        assert not result.skipped
        assert "splunk_ao_context" in py_file.read_text()


# ---------------------------------------------------------------------------
# 14. Python output always compiles
# ---------------------------------------------------------------------------

class TestPythonOutputCompiles:
    @pytest.mark.parametrize("src", [
        "GALILEO = 1\n",
        "class Galileo:\n    pass\n",
        "x = Galileo()\n",
        "from galileo import galileo_context\n",
        "from galileo_core.schemas.metrics import Metrics\nresult: Metrics = ...\n",
        "# Galileo logger\nGALILEO = 1\n",
        'TRACELOOP_HEADERS="Galileo-API-Key=key, logstream=default"\n',
    ])
    def test_output_is_valid_python(self, src):
        # Given: any source input
        # When: PYTHON_RULES applied
        # Then: output is valid Python (never produces SyntaxError)
        result = py(src)
        assert compiles(result), f"Output does not compile:\n{result}"
