# Contributing to the Splunk Agent Observability Python SDK

## Local Installation

### Pre-Requisites

1. Clone this repo locally.
2. Install [pyenv](https://github.com/pyenv/pyenv).
3. Install [`poetry`](https://python-poetry.org/): `curl -sSL https://install.python-poetry.org | python3 -`

### Setup

1. Setup a virtual environment:

   ```sh
   pyenv install 3.13
   pyenv local 3.13
   ```

   `poetry` will create a virtual environment using that Python version when it installs dependencies.

   > **_NOTE:_** In Poetry 2.x, the `shell` command was moved to a separate plugin: [poetry-plugin-shell](https://github.com/python-poetry/poetry-plugin-shell). Install it via Poetry's `self add`:
   >
   > ```sh
   > poetry self add poetry-plugin-shell
   > ```

   You can validate the Python version with:

   ```sh
   poetry run python --version
   ```

   which should print out `Python 3.13.x`. To activate the virtual environment in your shell, run `poetry shell`.

2. Install dependencies and setup pre-commit hooks:

   ```sh
   pip3 install --upgrade invoke
   inv setup
   ```

3. Run unit tests

   ```sh
   poetry run pytest
   ```

   Dev dependencies (including `fastapi ^0.135.0`) resolve against **Pydantic v2** (`>=2.9.0`). Use `poetry install --sync` after pulling lockfile changes so your local environment matches CI.

## Auto-generating the API client

1. Run `./scripts/import-openapi-yaml.sh https://api.galileo.ai/client` to update the openapi.yml file with the latest client spec
2. Run `./scripts/auto-generate-api-client.sh` to generate the API client
