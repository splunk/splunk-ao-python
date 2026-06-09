from platform import system

from invoke.context import Context
from invoke.tasks import task

# Disable `pty` on Windows to avoid issues with subprocesses.
# https://github.com/pyinvoke/invoke/issues/561
COMMON_PARAMS = {"echo": True, "pty": not system().lower().startswith("win")}


@task
def install(ctx: Context) -> None:
    ctx.run("poetry install --all-extras --no-root", **COMMON_PARAMS)


@task
def setup(ctx: Context) -> None:
    install(ctx)
    ctx.run("poetry run pre-commit install --hook-type pre-commit", **COMMON_PARAMS)


@task
def test_report_xml(ctx: Context) -> None:
    ctx.run("poetry run pytest -vvv --cov=splunk_ao --cov-report=xml", **COMMON_PARAMS)


@task
def test(ctx: Context) -> None:
    ctx.run("poetry run pytest --cov=splunk_ao --cov-report=term-missing", **COMMON_PARAMS)


@task
def type_check(ctx: Context) -> None:
    ctx.run(
        "poetry run mypy --package splunk_ao "
        # TODO: remove as soon as mypy errors fixed
        "--exclude galileo.resources "
        "--exclude splunk_ao.openai "
        "--exclude splunk_ao.decorator "
        "--exclude splunk_ao.handlers.langchain "
        "--exclude splunk_ao.log_streams "
        "--exclude splunk_ao.logger "
        "--exclude splunk_ao.api_client "
        "--namespace-packages",
        **COMMON_PARAMS,
    )


@task
def poetry_lock(ctx: Context) -> None:
    """
    Update poetry.lock file.

    Parameters
    ----------
    ctx : Context
        Invoke context.
    """
    ctx.run("poetry lock", **COMMON_PARAMS)
