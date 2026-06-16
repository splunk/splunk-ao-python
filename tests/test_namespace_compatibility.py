import importlib
import importlib.util
import sys
from collections.abc import Generator

import pytest


def _clear_legacy_modules() -> None:
    for module_name in list(sys.modules):
        if module_name == "galileo" or module_name.startswith("galileo."):
            sys.modules.pop(module_name)


@pytest.fixture(autouse=True)
def restore_legacy_modules() -> Generator[None, None, None]:
    previous_modules = {
        module_name: module
        for module_name, module in sys.modules.items()
        if module_name == "galileo" or module_name.startswith("galileo.")
    }

    yield

    _clear_legacy_modules()
    sys.modules.update(previous_modules)


def test_splunk_ao_import_smoke() -> None:
    module = importlib.import_module("splunk_ao")

    assert module.__version__
    assert hasattr(module, "splunk_ao_context")
    assert importlib.import_module("splunk_ao.openai")
    assert importlib.import_module("splunk_ao.logger")


def test_legacy_galileo_import_shim_warns() -> None:
    _clear_legacy_modules()

    with pytest.warns(DeprecationWarning, match="use 'splunk_ao' instead"):
        module = importlib.import_module("galileo")

    assert hasattr(module, "splunk_ao_context")


def test_protected_generated_resource_imports_remain_available() -> None:
    _clear_legacy_modules()

    with pytest.warns(DeprecationWarning, match="use 'splunk_ao' instead"):
        resources = importlib.import_module("galileo.resources")

    assert resources is not None


def test_generated_resource_dependency_shims_remain_available() -> None:
    _clear_legacy_modules()

    with pytest.warns(DeprecationWarning, match="use 'splunk_ao' instead"):
        exceptions = importlib.import_module("galileo.exceptions")
    headers_data = importlib.import_module("galileo.utils.headers_data")

    assert hasattr(exceptions, "NotFoundError")
    assert hasattr(headers_data, "get_sdk_header")


def test_namespace_package_discovery_paths() -> None:
    assert importlib.util.find_spec("splunk_ao") is not None
    assert importlib.util.find_spec("galileo") is not None
    assert importlib.util.find_spec("galileo.resources") is not None
