# Migration Tools Guide: galileo → splunk-ao

A detailed reference for every migration tool approach available in this repository,
covering what each tool does, its trade-offs, the files it uses, and the exact steps
a customer takes to use it.

---

## Table of Contents

1. [Python-Based Tools](#python-based-tools)
   - [1.1 Regex-Based CLI](#11-regex-based-cli)
   - [1.2 AST-Based CLI](#12-ast-based-cli)
   - [1.3 AI Agent Tool (LLM-Based)](#13-ai-agent-tool-llm-based)
   - [1.4 Semgrep (Structural Search & Replace)](#14-semgrep-structural-search--replace)
   - [1.5 Rope (Semantic Refactoring)](#15-rope-semantic-refactoring)
   - [1.6 Tokenize-Based](#16-tokenize-based)
   - [1.7 lib2to3 / Fixer Framework](#17-lib2to3--fixer-framework)
   - [1.8 ast.unparse (stdlib, no dependencies)](#18-astunparse-stdlib-no-dependencies)
   - [1.9 IDE Plugin — Shell-out](#19-ide-plugin--shell-out)
2. [IDE Plugin — Native TypeScript](#2-ide-plugin--native-typescript)
3. [Pre-commit Hook](#3-pre-commit-hook)
4. [Choosing the Right Tool](#4-choosing-the-right-tool)

---

## Python-Based Tools

---

### 1.1 Regex-Based CLI

#### What it is

A command-line tool that reads each file as plain text and applies ordered
regular-expression substitutions line by line. It is the simplest and broadest
tool: it works on every file type the migration touches — Python source files,
dependency files, environment variable files, and TOML configuration.

The rules are ordered deliberately (longest-match first, most-specific first)
to avoid partial substitutions. For example, `galileo.metric` is matched before
the shorter `galileo` so that `from galileo.metric import X` is rewritten to
`from splunk_ao.evaluator import X` rather than `from splunk_ao.metric import X`.

#### How it works

```
migrate.py
  │
  ├─ reads file as plain text
  ├─ runs each Rule (pattern → replacement) line by line
  ├─ collects Match objects (line number, original, replacement)
  └─ optionally writes result back atomically (temp file + os.replace)

splunk_ao_migrate/
  rules.py        ← all substitution rules as Rule dataclass instances
  transformer.py  ← compiles patterns, applies substitutions, returns TransformResult
  reporter.py     ← formats the summary report printed at the end
```

#### Example

Input (`my_agent.py`):
```python
from galileo import GalileoLogger, galileo_context
logger = GalileoLogger(project="proj", log_stream="prod")
os.environ["GALILEO_API_KEY"] = "key"
# This comment mentions GalileoLogger
```

Output after migration:
```python
from splunk_ao import SplunkAOLogger, splunk_ao_context
logger = SplunkAOLogger(project="proj", agent_stream="prod")
os.environ["SPLUNK_AO_API_KEY"] = "key"
# This comment mentions SplunkAOLogger   ← comment is also rewritten
```

Note: the comment is rewritten too because regex operates on raw text. If that is
undesirable, use the AST-based tool instead.

#### Pros

| Pro | Detail |
|-----|--------|
| Works on all file types | `.py`, `requirements*.txt`, `pyproject.toml`, `.env*` |
| Zero dependencies | Uses Python stdlib only — no `pip install` required |
| Fast | Linear scan, compiles each pattern once |
| Easy to extend | Add a new `Rule(...)` line to `rules.py` |
| Idempotent | Running on already-migrated code produces zero changes |
| Dry-run mode | `--dry-run` shows changes without writing |

#### Cons

| Con | Detail |
|-----|--------|
| Over-substitutes in comments | `# GalileoLogger` in a comment gets renamed |
| Over-substitutes in docstrings | `"""Uses GalileoLogger"""` gets renamed |
| Over-substitutes in unrelated strings | `"some galileo note"` gets renamed |
| Cannot understand syntax context | No awareness of whether a token is an identifier vs a string |

#### Files

| File | Contains |
|------|----------|
| `migrate.py` | CLI entry point; argument parsing, file collection, per-file orchestration, diff printer |
| `splunk_ao_migrate/rules.py` | All Rule objects: import rewrites, symbol renames, kwarg renames, env-var strings, HTTP headers, warning patterns |
| `splunk_ao_migrate/transformer.py` | `transform(content, rules, warning_rules)` → `TransformResult`; compiles patterns, applies substitutions |
| `splunk_ao_migrate/reporter.py` | `Reporter` class; collects `FileResult` objects, prints summary report with next steps |
| `splunk_ao_migrate/__init__.py` | Package marker |

#### Customer steps

```bash
# 1. Clone or copy the migration tool
git clone https://github.com/splunk/splunk-ao-python.git
cd splunk-ao-python/splunk-ao-migration-tool

# 2. Preview what will change (no files written)
python migrate.py --dry-run /path/to/customer/app

# 3. Apply migration
python migrate.py /path/to/customer/app

# 4. Review the diff
cd /path/to/customer/app
git diff

# 5. Run tests and commit if everything looks good
```

For individual file types:
```bash
# Python source only
python migrate.py src/

# Dependency files only
python migrate.py requirements.txt pyproject.toml

# Env file only
python migrate.py .env
```

---

### 1.2 AST-Based CLI

#### What it is

A command-line tool that parses Python source into a **Concrete Syntax Tree (CST)**
using the `libcst` library, applies targeted transformations to specific node types,
then serialises the tree back to source. It only processes `.py` files.

Because it operates on the syntax tree rather than raw text, it knows the difference
between an identifier in code (`GalileoLogger()`), a string literal (`"GalileoLogger"`),
a comment (`# GalileoLogger`), and a docstring (`"""GalileoLogger"""`). Only
identifiers and the specific string literals that are env-var keys or HTTP headers
are rewritten. Everything else is left exactly as-is.

#### How it works

```
migrate_ast.py
  │
  ├─ parses source with libcst.parse_module()
  ├─ applies GalileoToSplunkAO transformer (single tree walk)
  │     ├─ ImportRewriter    → rewrites ImportFrom / Import nodes
  │     ├─ NameRewriter      → rewrites Name / Attribute nodes
  │     ├─ KwargRewriter     → rewrites Arg(keyword=…) nodes
  │     └─ StringRewriter    → rewrites SimpleString nodes (env-vars / headers only)
  ├─ serialises back to source (preserving all whitespace and formatting)
  └─ resolves line numbers by diffing original vs new source

splunk_ao_migrate_ast/
  codemods.py   ← all four CSTTransformer classes + GalileoToSplunkAO composition
```

#### Example

Input (`my_agent.py`):
```python
from galileo import GalileoLogger, galileo_context
# This comment mentions GalileoLogger — do not rename
"""Docstring: GalileoLogger was the old class."""
logger = GalileoLogger(project="proj", log_stream="prod")
os.environ["GALILEO_API_KEY"] = "key"
```

Output after AST migration:
```python
from splunk_ao import SplunkAOLogger, splunk_ao_context
# This comment mentions GalileoLogger — do not rename   ← untouched
"""Docstring: GalileoLogger was the old class."""        ← untouched
logger = SplunkAOLogger(project="proj", agent_stream="prod")
os.environ["SPLUNK_AO_API_KEY"] = "key"
```

#### Pros

| Pro | Detail |
|-----|--------|
| Precise | Only renames identifiers in code; never touches comments or docstrings |
| Preserves formatting | Whitespace, blank lines, string quote style all preserved |
| Context-aware | Distinguishes Name vs String vs Comment at the node level |
| Composable | Four independent transformers, each targeting one node type |
| Safe | Syntax errors cause file to be skipped, never corrupted |

#### Cons

| Con | Detail |
|-----|--------|
| Python files only | Cannot handle `.txt`, `.toml`, `.env` files |
| Requires libcst | `pip install libcst>=1.1.0` — one extra dependency |
| Valid Python required | Files with syntax errors are skipped |
| Slightly slower | Full CST parse per file vs plain text scan |

#### Files

| File | Contains |
|------|----------|
| `migrate_ast.py` | CLI entry point; argument parsing, file collection, per-file orchestration, unified diff printer |
| `splunk_ao_migrate_ast/codemods.py` | `ImportRewriter`, `NameRewriter`, `KwargRewriter`, `StringRewriter`, `GalileoToSplunkAO` transformer; rename tables (`MODULE_RENAMES`, `NAME_RENAMES`, `KWARG_RENAMES`, `STRING_RENAMES`); `transform_python(source)` public API |
| `splunk_ao_migrate_ast/__init__.py` | Package marker |
| `splunk_ao_migrate_ast/README.md` | AST tool documentation and comparison with regex tool |

#### Customer steps

```bash
# 1. Install the dependency
pip install libcst>=1.1.0

# 2. Preview changes (no files written)
python migrate_ast.py --dry-run /path/to/customer/app/src

# 3. Preview with unified diff
python migrate_ast.py --diff /path/to/customer/app/src

# 4. Apply migration to Python files
python migrate_ast.py /path/to/customer/app/src

# 5. Also migrate non-Python files with the regex tool
python migrate.py requirements.txt pyproject.toml .env

# 6. Review and commit
git diff
```

#### Recommended combined workflow

For the cleanest migration, use both tools together:

```bash
# AST tool for .py files (precise — leaves comments untouched)
python migrate_ast.py src/

# Regex tool for everything else
python migrate.py requirements.txt pyproject.toml .env .env.example
```

---

### 1.3 AI Agent Tool (LLM-Based)

#### What it is

A structured Python API that exposes the migration capabilities as **callable tool
functions** returning plain dicts. It is designed to be given to an LLM (Claude,
GPT-4, etc.) as a tool set, so the AI can orchestrate the migration interactively —
scanning scope, explaining changes to the customer, handling warnings, and applying
fixes — rather than the customer running CLI commands manually.

The underlying transformation engine is the same regex-based tool (`splunk_ao_migrate`).
The agent layer adds structured JSON-serialisable return values, progress tracking,
and a workflow guide (`CLAUDE.md`) that tells the AI how to use the tools correctly.

#### How it works

```
LLM agent
  │
  ├─ calls scan_project(path)         → {files_needing_migration, counts}
  ├─ calls check_warnings(path)       → {warnings requiring manual review}
  ├─ calls inspect_file(path)         → {preview of changes, no writes}
  ├─ calls migrate_file(path)         → {applies changes, returns diff}
  ├─ calls migrate_project(path)      → {applies all, returns summary}
  └─ calls migration_status(path)     → {not_started / in_progress / complete}

agent_migrate/
  tools.py    ← all seven tool functions (thin wrappers over splunk_ao_migrate)
  CLAUDE.md   ← workflow instructions for the AI agent
```

#### Example agent session

```python
from agent_migrate.tools import scan_project, check_warnings, migrate_project, migration_status

# Step 1: understand scope
scan = scan_project("my_app/")
# → {"total_needing_migration": 5, "files_needing_migration": [...]}

# Step 2: check for items needing manual review
warnings = check_warnings("my_app/")
# → {"count": 1, "warnings": [{"path": "app.py", "line": 42,
#      "reason": "Protect feature usage — keep galileo as dependency"}]}

# Step 3: migrate
result = migrate_project("my_app/")
# → {"total_changed": 5, "total_substitutions": 23, ...}

# Step 4: confirm
status = migration_status("my_app/")
# → {"status": "complete", "remaining": 0, "percent_done": 100.0}
```

#### Pros

| Pro | Detail |
|-----|--------|
| Interactive | AI explains each change to the customer before applying |
| Handles grey areas | AI can reason about Protect usage, dynamic env-vars, manual steps |
| Structured output | All returns are plain dicts — easy to parse and display |
| Composable | Each tool function can be called independently |
| Guided workflow | `CLAUDE.md` ensures the AI follows the correct sequence |

#### Cons

| Con | Detail |
|-----|--------|
| Underlying engine is regex | Same over-substitution in comments as the regex CLI |
| Requires an LLM | Not a standalone tool — needs an AI runtime to drive it |
| Non-deterministic orchestration | The AI decides the order and scope; may vary per run |
| Not for unattended automation | Intended for interactive, guided sessions |

#### Files

| File | Contains |
|------|----------|
| `agent_migrate/tools.py` | `scan_project`, `inspect_file`, `migrate_file`, `migrate_project`, `check_warnings`, `migration_status`, `get_migration_rules` — all returning plain dicts |
| `agent_migrate/CLAUDE.md` | Six-step workflow guide for AI agents; lists all auto-fixed renames, manual-review items, and next steps to give the customer |
| `agent_migrate/__init__.py` | Package marker |

#### Customer steps

**Option A — Using Claude Code directly:**

```bash
# Open the customer's project in Claude Code
# Claude reads CLAUDE.md automatically and uses the tools

# The agent will:
# 1. Scan the project and report scope
# 2. Flag any Protect usage or dynamic env-vars
# 3. Ask permission before migrating
# 4. Apply changes file by file, explaining each one
# 5. Confirm completion and provide next steps
```

**Option B — Integrating into a custom agent:**

```python
# Install in any LLM agent framework (LangChain, LlamaIndex, etc.)
from agent_migrate.tools import (
    scan_project, check_warnings, migrate_file, migration_status
)

# Register as tools in your agent and let the LLM drive the workflow
```

---

### 1.4 Semgrep (Structural Search & Replace)

#### What it is

A YAML-driven rule engine that pattern-matches against the AST of Python (and many
other languages). Instead of writing Python code or TypeScript, migration rules are
expressed as **patterns that look like the code they match** — making them readable
and reviewable by non-engineers. Rules are stored in `.yaml` files, version-controlled
alongside the project, and can be shared across teams via a rule registry.

Semgrep is an external binary (not a Python library), so it is invoked as a CLI tool
or in CI/CD pipelines rather than being embedded in Python code.

#### How it works

```
semgrep --config semgrep-rules/ src/

semgrep-rules/
  galileo_imports.yaml      ← patterns for import rewrites
  galileo_symbols.yaml      ← patterns for class / symbol renames
  galileo_kwargs.yaml       ← patterns for keyword argument renames
  galileo_envvars.yaml      ← patterns for env-var string literals
```

Each rule matches a structural pattern and emits a finding with a suggested
replacement. Semgrep can apply fixes automatically with `--autofix`.

#### Example rules

```yaml
rules:
  - id: rename-galileo-logger
    pattern: GalileoLogger(...)
    fix: SplunkAOLogger(...)
    languages: [python]
    message: "GalileoLogger → SplunkAOLogger"
    severity: WARNING

  - id: rename-log-stream-kwarg
    pattern: $FUNC(log_stream=$X)
    fix: $FUNC(agent_stream=$X)
    languages: [python]
    message: "log_stream= kwarg → agent_stream="
    severity: WARNING

  - id: rename-galileo-import
    pattern: import galileo
    fix: import splunk_ao
    languages: [python]
    message: "galileo → splunk_ao"
    severity: WARNING
```

The `$FUNC` and `$X` are **metavariables** — wildcards that match any expression.
This means the `log_stream=` rule matches every function call that uses that keyword,
regardless of the function name — something regex cannot express cleanly.

#### Pros

| Pro | Detail |
|-----|--------|
| Declarative YAML rules | Non-engineers can read, review, and contribute rules |
| Metavariables | `$FUNC(log_stream=$X)` matches any call with that kwarg — more expressive than regex |
| Multi-language | Same rule format works for Python, JS, Go, Java, etc. |
| CI/CD native | `semgrep ci` integrates directly with GitHub Actions, GitLab CI, etc. |
| Shareable registry | Rules can be published to the Semgrep Registry for others to use |
| Autofix | `--autofix` applies fixes in place; `--dry-run` previews |
| No Python dependency | Semgrep is a standalone binary |

#### Cons

| Con | Detail |
|-----|--------|
| External binary | Requires `brew install semgrep` or `pip install semgrep` — not stdlib |
| Not embeddable | Cannot be imported as a Python library; always CLI/subprocess |
| Pattern language learning curve | Metavariable syntax (`$X`, `...`, `$...ARGS`) is specific to Semgrep |
| Python files only for code patterns | Env-var and TOML rewrites still need the regex tool |
| Heavier than regex | Slower startup (binary load) for small projects |

#### Files needed

| File | Contains |
|------|----------|
| `semgrep-rules/galileo_imports.yaml` | Rules for `import galileo`, `from galileo import …`, satellite packages |
| `semgrep-rules/galileo_symbols.yaml` | Rules for all `Galileo*` class and function renames |
| `semgrep-rules/galileo_kwargs.yaml` | Rules for `log_stream=` and `log_stream_name=` keyword arguments |
| `semgrep-rules/galileo_envvars.yaml` | Rules for `os.environ["GALILEO_*"]` string literal renames |
| `semgrep-rules/galileo_warnings.yaml` | Warning-only rules for Protect feature usage (no autofix) |

#### Customer steps

```bash
# 1. Install Semgrep
pip install semgrep
# or: brew install semgrep

# 2. Preview findings (no files written)
semgrep --config semgrep-rules/ src/

# 3. Apply autofixes
semgrep --config semgrep-rules/ --autofix src/

# 4. Review and commit
git diff

# 5. Add to CI/CD (GitHub Actions example)
# .github/workflows/semgrep.yml:
#   - uses: returntocorp/semgrep-action@v1
#     with:
#       config: semgrep-rules/
```

---

### 1.5 Rope (Semantic Refactoring)

#### What it is

A Python refactoring library that understands **semantics** rather than just syntax.
While the regex tool operates on raw text and the AST tool operates on the parse tree,
rope resolves names across module boundaries — it knows what a name *refers to*, not
just what it *looks like*.

The critical capability this adds: rope correctly renames symbols even when they are
**imported under an alias**, a case that the regex and AST tools both miss.

#### How it works

```
rope
  │
  ├─ builds a project model (indexes all .py files in the project)
  ├─ resolves every name to its definition (cross-file, cross-import)
  ├─ finds all usages of a symbol, including aliased usages
  └─ applies rename across all files that reference the symbol
```

#### Example — aliased import (regex and AST tools miss this)

```python
# customer code
from galileo import GalileoLogger as GL
x = GL()   # GL is an alias for GalileoLogger

# Regex tool: renames GalileoLogger in import but leaves GL() untouched
# AST tool:   same — renames the Name node "GalileoLogger" but not "GL"
# Rope:       knows GL resolves to GalileoLogger, renames the usage too
```

#### Pros

| Pro | Detail |
|-----|--------|
| Alias-aware | Renames usages even when imported under a different name |
| Semantic understanding | Resolves names across file and module boundaries |
| Project-wide | Finds every usage in the whole project, not just the current file |
| PyCharm uses it | Battle-tested in production IDE tooling |

#### Cons

| Con | Detail |
|-----|--------|
| External dependency | `pip install rope` |
| Slow on large projects | Full project indexing required before any rename |
| Overkill for most customers | Aliased imports of galileo SDK classes are rare in practice |
| Complex setup | Requires a `Project` object and per-rename API calls, not a simple CLI |
| Dynamic imports not covered | `getattr(module, name)` and `importlib` usages are not resolved |

#### Files needed

| File | Contains |
|------|----------|
| `migrate_rope.py` | CLI entry point; constructs a `rope.base.project.Project`, iterates `NAME_RENAMES`, calls `rope.refactor.rename.Rename` for each symbol, writes changes |

#### Customer steps

```bash
# 1. Install rope
pip install rope

# 2. Run the rope-based migrator
python migrate_rope.py /path/to/customer/app

# 3. Also run the regex tool for non-Python files
python migrate.py requirements.txt pyproject.toml .env

# 4. Review and commit
git diff
```

> **When to use rope instead of the AST tool:** Only when the codebase imports galileo
> symbols under aliases (`from galileo import X as Y`). For the vast majority of
> customers the AST tool is sufficient.

---

### 1.6 Tokenize-Based

#### What it is

A Python stdlib approach that splits source code into a flat stream of **tokens**
(`NAME`, `STRING`, `OP`, `COMMENT`, `NEWLINE`, etc.) without building a full parse
tree. It sits between the regex tool (raw text, no structure) and the AST tool (full
parse tree, requires valid Python).

The key property: it can distinguish the token type of every occurrence of the word
`GalileoLogger` — whether it is a `NAME` token in code, a `STRING` token inside
quotes, or a `COMMENT` token after `#` — without needing a valid parse tree.

```
Raw text (regex)     "GalileoLogger"  ← matches anywhere
Token stream         NAME: GalileoLogger   ← in code
                     STRING: "GalileoLogger"  ← in a string
                     COMMENT: # GalileoLogger ← in a comment
Full parse tree (AST/libcst)    ImportFrom.Name, Call.func.Name, etc.
```

#### How it works

```python
import tokenize, io

tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
# Each token: (type, string, start, end, line)
# Rewrite only NAME tokens matching galileo symbols
# Reconstruct source from modified token stream
```

#### Example

```python
# input
from galileo import GalileoLogger  # import GalileoLogger here
logger = GalileoLogger()

# tokenize output (simplified)
NAME     'from'
NAME     'galileo'       ← rename this (it's a NAME token)
NAME     'import'
NAME     'GalileoLogger' ← rename this (it's a NAME token)
COMMENT  '# import GalileoLogger here'  ← leave this (it's a COMMENT token)
NAME     'GalileoLogger' ← rename this (it's a NAME token)
OP       '('
OP       ')'
```

#### Pros

| Pro | Detail |
|-----|--------|
| Zero dependencies | `tokenize` is Python stdlib — no `pip install` |
| Handles invalid Python | Tokenizer is more tolerant than a full parser; works on partial/broken files that libcst rejects |
| Comment-aware | Can skip `COMMENT` tokens, unlike the regex tool |
| String-aware | Can target only `STRING` tokens for env-var renames |

#### Cons

| Con | Detail |
|-----|--------|
| No structural context | Cannot distinguish `import galileo` from `x = galileo` — both are `NAME` tokens |
| No keyword argument awareness | Cannot identify `log_stream=` as a keyword arg without tree context |
| Fiddly reconstruction | Source must be rebuilt from the token stream carefully to preserve whitespace |
| Worse than libcst for valid Python | libcst gives full structural context; tokenize is only useful when libcst fails |
| Niche use case | Only worth building if customers have syntactically invalid Python files |

#### Files needed

| File | Contains |
|------|----------|
| `migrate_tokenize.py` | CLI entry point; tokenizes each file, rewrites `NAME` tokens matching `NAME_RENAMES`, rewrites `STRING` tokens matching `STRING_RENAMES`, reconstructs and writes source |

#### Customer steps

```bash
# Use this tool only for files that migrate_ast.py rejects with a parse error

# 1. Run AST tool first (handles all valid Python files)
python migrate_ast.py src/

# 2. Run tokenize tool on any files that failed
python migrate_tokenize.py src/broken_file.py

# 3. Review and commit
git diff
```

> **When to use the tokenize tool:** Only as a fallback for files that contain
> Python syntax errors and are therefore rejected by libcst. For all valid Python
> files, the AST tool (`migrate_ast.py`) is the better choice.

### 1.7 lib2to3 / Fixer Framework

Python's own migration tool from the stdlib — you write `BaseFix` subclasses using
a pattern language. The reason it's worth mentioning: it requires **zero pip install**
(stdlib-only). For environments where adding `libcst` as a dependency is blocked, a
lib2to3-based tool would work out of the box. The downside is it's more verbose to
write and is **deprecated in Python 3.13+**.

---

### 1.8 ast.unparse (stdlib, no dependencies)

`ast.parse()` + `ast.NodeTransformer` + `ast.unparse()` — all stdlib, available from
Python 3.9+. The critical limitation is that `ast.unparse()` **discards all comments
and reformats everything**. This makes it unsuitable as a primary tool for user code
migration (users would lose their comments). But it's a viable option for generating
**test fixtures** or transforming **machine-generated code** where formatting doesn't
matter.

---

### 1.9 IDE Plugin — Shell-out

#### What it is

A VS Code extension written in TypeScript that **delegates all migration logic to
`migrate.py`** by spawning it as a child process. The TypeScript code handles only
the VS Code UI (commands, progress notifications, output panel, file reloading).
The actual transformation rules live exclusively in the Python tool.

This means there is a **single source of truth** for rules — `rules.py` — and the
IDE plugin always uses the latest rules without needing to be updated separately.

#### How it works

```
VS Code UI (TypeScript)
  │
  │  child_process.spawn(python3, [migrate.py, --dry-run?, path])
  ▼
migrate.py  (Python subprocess)
  │
  ├─ splunk_ao_migrate/rules.py
  ├─ splunk_ao_migrate/transformer.py
  └─ stdout → captured by extension → displayed in Output panel
```

#### What the customer sees

- Right-click a Python file → **"Splunk AO: Migrate Current File"**
- Right-click a folder → **"Splunk AO: Migrate Entire Project"**
- Command Palette → **"Splunk AO: Preview Migration (Dry Run)"**
- Progress notification while migration runs
- Output panel shows the migration report
- Open editors reload automatically after in-place rewrite

#### Pros

| Pro | Detail |
|-----|--------|
| Single source of truth | Rules only exist in `rules.py`; no TypeScript duplication |
| Always up to date | Update `rules.py` — extension automatically uses new rules |
| Simple TypeScript | Extension code is only UI glue, no migration logic |
| Full file type support | `migrate.py` handles `.py`, `.txt`, `.toml`, `.env` |

#### Cons

| Con | Detail |
|-----|--------|
| Python required | Customer must have Python 3.11+ and the migration tool on disk |
| No inline diagnostics | Cannot underline galileo references in the editor as you type |
| No quick-fix actions | No lightbulb / Ctrl+. fix per symbol |
| Output is plain text | Report displayed as text in Output panel, not structured diagnostics |

#### Files

| File | Contains |
|------|----------|
| `vscode-extension-shellout/src/extension.ts` | Extension activation, command registration, `child_process.spawn` call, output streaming, file reload after write |
| `vscode-extension-shellout/package.json` | Extension manifest: name, commands (`migrateFile`, `migrateFilePreview`, `migrateProject`, `migrateProjectPreview`, `setMigratePyPath`), settings (`migratePyPath`, `pythonPath`), context menu contributions |
| `vscode-extension-shellout/tsconfig.json` | TypeScript compiler config (target ES2020, commonjs) |
| `vscode-extension-shellout/README.md` | Setup guide, command reference, settings reference |

#### Customer steps

```bash
# 1. Build the extension
cd vscode-extension-shellout
npm install
npm run compile

# 2. Install in VS Code
# Press F5 to launch Extension Development Host, or:
# Package with: npx vsce package
# Install .vsix: code --install-extension splunk-ao-migrate-shellout-0.1.0.vsix

# 3. Configure the path to migrate.py (if not auto-detected)
# VS Code Settings → splunkAoMigrate.migratePyPath
# or: Command Palette → "Splunk AO: Set Path to migrate.py"

# 4. Use in editor
# Right-click any Python file → "Splunk AO: Migrate Current File"
# Or Command Palette → "Splunk AO: Migrate Entire Project"
```

---

## 2. IDE Plugin — Native TypeScript

#### What it is

A VS Code extension where **all migration rules are re-implemented in TypeScript**
with no Python runtime required. It provides features that the shell-out extension
cannot: inline diagnostics (squiggly underlines as you type) and quick-fix code
actions (one-click rename from the lightbulb or Ctrl+.).

The rules in `src/rules.ts` are a direct port of `splunk_ao_migrate/rules.py`,
following the same structure so the two files are easy to diff and keep in sync.

#### How it works

```
VS Code TypeScript extension
  │
  ├─ src/rules.ts        ← migration rules (port of rules.py)
  ├─ src/transformer.ts  ← regex engine (port of transformer.py)
  └─ src/extension.ts
        ├─ lintDocument()             → emits Diagnostic objects (squiggly lines)
        ├─ MigrationCodeActionProvider → offers quick-fix WorkspaceEdits
        ├─ migrateCurrentFile()       → applies all rules via WorkspaceEdit
        ├─ migrateProject()           → walks workspace, rewrites all files
        └─ previewCurrentFile()       → prints diff to Output panel
```

#### What the customer sees

- Squiggly underlines on every `galileo` SDK reference as they type
- Hover tooltip: `"galileo SDK: GalileoLogger → SplunkAOLogger"`
- Lightbulb / Ctrl+.: **"Apply migration: GalileoLogger → SplunkAOLogger"** (fixes one line)
- Lightbulb / Ctrl+.: **"Migrate entire file (splunk-ao)"** (fixes whole file)
- Problems panel lists all occurrences across the workspace
- Command Palette → **"Splunk AO: Preview Migration for Current File"** (diff in Output panel)
- Command Palette → **"Splunk AO: Migrate Entire Project"**

#### Pros

| Pro | Detail |
|-----|--------|
| No Python required | Runs entirely in the VS Code extension host (Node.js) |
| Inline diagnostics | Squiggly underlines on galileo references as you type |
| Quick-fix actions | One-click per-line fixes via lightbulb / Ctrl+. |
| Problems panel | All occurrences listed and navigable |
| Configurable severity | `error`, `warning`, `information`, or `hint` |
| Works offline | No subprocess, no network, no runtime dependency |

#### Cons

| Con | Detail |
|-----|--------|
| No `.env` / `.toml` support | VS Code extension only lints Python files |
| Regex only | No AST precision — same over-substitution in comments as the regex tool |
| TypeScript build step | Requires Node.js and `npm run compile` before use |

#### Files

| File | Contains |
|------|----------|
| `vscode-extension-typescript/src/rules.ts` | All Rule objects ported from `rules.py`: `IMPORT_RULES`, `SYMBOL_RULES`, `KWARG_RULES`, `ENV_VAR_RULES`, `HEADER_RULES`, `WARNING_RULES`, `PYTHON_RULES`, `DEP_RULES`, `ENV_FILE_RULES` |
| `vscode-extension-typescript/src/transformer.ts` | `transform(content, rules, warningRules)` → `TransformResult`; `classifyFile(fileName)` → file kind; `compileRule(rule)` → `RegExp` |
| `vscode-extension-typescript/src/extension.ts` | Extension activation, `lintDocument()`, `MigrationCodeActionProvider`, `migrateCurrentFile()`, `migrateProject()`, `previewCurrentFile()`, `collectFiles()` |
| `vscode-extension-typescript/package.json` | Extension manifest: name, commands (`migrateFile`, `migrateProject`, `previewFile`), settings (`enableDiagnostics`, `diagnosticSeverity`), context menu and editor contributions |
| `vscode-extension-typescript/tsconfig.json` | TypeScript compiler config (target ES2020, commonjs) |
| `vscode-extension-typescript/README.md` | Feature overview, setup guide, sync instructions for keeping `rules.ts` in sync with `rules.py` |

#### Customer steps

```bash
# 1. Build the extension
cd vscode-extension-typescript
npm install
npm run compile

# 2. Install in VS Code
# Press F5 to launch Extension Development Host, or:
# Package with: npx vsce package
# Install .vsix: code --install-extension splunk-ao-migrate-0.1.0.vsix

# 3. Open a Python project — diagnostics appear immediately
# No configuration needed; diagnostics are on by default.

# 4. Optional settings (VS Code Settings or .vscode/settings.json):
{
  "splunkAoMigrate.enableDiagnostics": true,
  "splunkAoMigrate.diagnosticSeverity": "warning"
}

# 5. Fix interactively
# Hover any squiggly → Ctrl+. → "Apply migration: ..."
# Or Command Palette → "Splunk AO: Migrate Entire Project"
```

#### Getting updated rules

When Splunk adds new renames to the extension, update to the latest published
version:

```bash
# If installed via .vsix
npx vsce package   # rebuild from latest source
code --install-extension splunk-ao-migrate-0.x.x.vsix

# If installed from VS Code Marketplace (once published)
# VS Code → Extensions → Splunk AO Migration → Update
```

---

## 3. Pre-commit Hook

#### What it is

A git pre-commit hook integration that **automatically scans staged files** for
galileo SDK references every time `git commit` is run. Unlike the CLI tools (which
the customer runs once during migration), the pre-commit hook provides **ongoing
enforcement** — it prevents galileo references from being re-introduced after the
migration is complete.

Two hooks are provided with different behaviours:

| Hook | Behaviour | Use case |
|------|-----------|----------|
| `splunk-ao-migrate-check` | Scan only; block commit if galileo found; never modify files | Recommended: developer sees what needs fixing and fixes it manually |
| `splunk-ao-migrate-fix` | Rewrite files in place; block commit so developer reviews diff | Aggressive: auto-fixes then forces a review before re-staging |

#### How it works

```
git commit
  │
  └─ .git/hooks/pre-commit  (installed by pre-commit)
        │
        └─ pre-commit runs hooks from .pre-commit-config.yaml
              │
              └─ splunk-ao-migrate-check  (or -fix)
                    │  (staged file paths passed as arguments)
                    ▼
              pre_commit_hooks.py
                    ├─ check()  → reads files, runs transform(), reports, exits 1 if found
                    └─ fix()    → reads files, runs transform(), writes in place, exits 1 if changed

pyproject.toml  ← registers entry points so pre-commit can find check() and fix()
.pre-commit-hooks.yaml  ← defines hook IDs, entry points, file patterns
.pre-commit-config.yaml ← template for customer projects (references the hook IDs)
```

#### What the customer sees

**Check hook (commit blocked):**
```
Splunk AO Migration: check for galileo SDK references......Failed
- hook id: splunk-ao-migrate-check
- exit code: 1

my_agent.py
  line    2: from galileo import GalileoLogger
         → from splunk_ao import SplunkAOLogger
  line   15: os.environ["GALILEO_API_KEY"] = "key"
         → os.environ["SPLUNK_AO_API_KEY"] = "key"

Galileo SDK references detected. Run the migration tool to fix them:
  python migrate.py <path>
```

**Fix hook (commit blocked after auto-fix):**
```
Splunk AO Migration: auto-fix galileo SDK references..........Failed
- hook id: splunk-ao-migrate-fix

Fixed: my_agent.py  (6 substitutions)

Files were rewritten. Review the changes and re-stage:
  git diff
  git add my_agent.py
```

#### Pros

| Pro | Detail |
|-----|--------|
| Ongoing enforcement | Prevents galileo from re-entering the codebase after migration |
| Runs automatically | No manual step — fires on every `git commit` |
| Only scans staged files | Fast — does not re-scan unchanged files |
| Two modes | Check-only (safe) or auto-fix (convenient) |
| Skippable | `SKIP=splunk-ao-migrate-check git commit` for emergencies |
| No extra dependencies | Uses the same stdlib-only regex engine as `migrate.py` |

#### Cons

| Con | Detail |
|-----|--------|
| Enforcer, not migrator | Does not migrate an existing codebase; only prevents regressions |
| Blocks commit | Can frustrate developers unfamiliar with the hook |
| Regex engine | Same over-substitution characteristics as the regex CLI |
| Requires pre-commit | Team must have `pip install pre-commit` and run `pre-commit install` |

#### Files

| File | Contains |
|------|----------|
| `pre_commit_hooks.py` | `check(argv)` — scans and reports; `fix(argv)` — rewrites in place; both are called with staged file paths as arguments |
| `.pre-commit-hooks.yaml` | Hook definitions: IDs (`splunk-ao-migrate-check`, `splunk-ao-migrate-fix`), entry points, file patterns, language (`python`) |
| `.pre-commit-config.yaml` | Customer-facing template with three options: check-only, auto-fix, local path; includes setup instructions as comments |
| `pyproject.toml` | Registers `splunk-ao-migrate-check` and `splunk-ao-migrate-fix` as `[project.scripts]` entry points so pre-commit can install and invoke them |

#### Customer steps

```bash
# 1. Install pre-commit (once per machine)
pip install pre-commit

# 2. Copy the config template to the project root
cp /path/to/splunk-ao-migration-tool/.pre-commit-config.yaml .

# 3. Edit .pre-commit-config.yaml
#    - Choose Option A (check-only) or Option B (auto-fix)
#    - Pin rev: to a specific release tag (e.g. rev: v0.2.1) for reproducibility

# 4. Install the git hook (once per repository clone)
pre-commit install

# 5. From this point, every git commit automatically scans staged files

# 6. To run manually against all files
pre-commit run --all-files

# 7. To run a specific hook
pre-commit run splunk-ao-migrate-check --all-files

# 8. To temporarily bypass (e.g. for a hotfix)
SKIP=splunk-ao-migrate-check git commit -m "emergency fix"
```

**Updating the hook** (when a new version is published):

```bash
# Update rev: in .pre-commit-config.yaml then:
pre-commit autoupdate
```

---

## 4. Choosing the Right Tool

| Scenario | Recommended tool |
|----------|-----------------|
| One-time bulk migration of an entire project | **Regex CLI** (`migrate.py`) — handles all file types, zero dependencies |
| Migration where comments must not be changed | **AST CLI** (`migrate_ast.py`) + regex for non-Python files |
| Guided interactive migration with explanations | **AI Agent tool** (`agent_migrate/`) with Claude or similar |
| Rules must be reviewable by non-engineers or shared across teams | **Semgrep** — declarative YAML rules, CI/CD native |
| Codebase uses aliased imports (`from galileo import X as Y`) | **Rope** — semantic rename that follows aliases across files |
| Files have syntax errors that the AST tool rejects | **Tokenize** — stdlib fallback for broken/partial Python files |
| Team uses VS Code, wants click-to-fix in editor | **Native TypeScript extension** (no Python needed) |
| Team uses VS Code, wants to reuse `migrate.py` | **Shell-out extension** (single source of truth for rules) |
| Prevent galileo from re-entering after migration | **Pre-commit hook** (ongoing enforcement) |
| CI/CD pipeline check | **Pre-commit hook**, `python migrate.py --dry-run`, or `semgrep --config semgrep-rules/` |
| `libcst` dependency is blocked by environment policy | **lib2to3 fixer** — stdlib-only, no pip install (avoid on Python 3.13+) |
| Migrating machine-generated code where comments don't exist | **ast.unparse** — stdlib-only, discards comments but sufficient for generated files |

### Typical sequence for a complete migration

```
Step 1  Run AST CLI or Regex CLI      → migrate the existing codebase once
Step 2  Run git diff                  → review every change
Step 3  Run tests                     → confirm nothing broke
Step 4  Commit                        → migration complete
Step 5  Install pre-commit hook       → prevent regressions going forward
Step 6  (Optional) Install VS Code extension → ongoing inline guidance for the team
```
