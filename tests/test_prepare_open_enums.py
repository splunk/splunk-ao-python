"""Schema preparation for extensible generated enums."""

import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from prepare_open_enums import prepare_open_enums


@pytest.fixture
def document() -> dict[str, Any]:
    """Return a small schema containing named enums and their common uses."""
    return {
        "components": {
            "schemas": {
                "Role": {"title": "Role", "type": "string", "enum": ["user", "admin"]},
                "TaskType": {"title": "TaskType", "type": "integer", "enum": [7, 9]},
                "User": {
                    "type": "object",
                    "properties": {
                        "role": {
                            "$ref": "#/components/schemas/Role",
                            "description": "Organization role",
                            "default": "user",
                        },
                        "roles": {"type": "array", "items": {"$ref": "#/components/schemas/Role"}},
                        "task": {"anyOf": [{"$ref": "#/components/schemas/TaskType"}, {"type": "null"}]},
                    },
                },
            }
        }
    }


def test_enum_uses_expand_without_changing_definitions_or_input(document: dict[str, Any]) -> None:
    """Named classes retain their identity while field types gain raw alternatives."""
    original = deepcopy(document)
    prepared = prepare_open_enums(document)
    schemas = prepared["components"]["schemas"]
    fields = schemas["User"]["properties"]

    assert document == original
    assert schemas["Role"] == original["components"]["schemas"]["Role"]
    assert schemas["TaskType"] == original["components"]["schemas"]["TaskType"]
    assert fields["role"]["description"] == "Organization role"
    assert "default" not in fields["role"]
    assert fields["role"]["anyOf"][-1] == {"type": "string"}
    assert fields["roles"]["items"]["anyOf"][-1] == {"type": "string"}
    assert fields["task"]["anyOf"] == [{"$ref": "#/components/schemas/TaskType"}, {"type": "null"}, {"type": "integer"}]


def test_preparation_is_idempotent(document: dict[str, Any]) -> None:
    # When: preparing an already expanded schema
    prepared = prepare_open_enums(document)

    # Then: repeated preparation does not nest or duplicate alternatives
    assert prepare_open_enums(prepared) == prepared


def test_inline_enum_keeps_name_default_and_known_values(document: dict[str, Any]) -> None:
    # Given: an inline enum with the title used for its generated class name
    enum = {"title": "Operator", "type": "string", "enum": ["eq", "ne"], "default": "eq"}
    document["components"]["schemas"]["User"]["properties"]["operator"] = enum

    # When: expanding the inline enum
    prepared = prepare_open_enums(document)
    operator = prepared["components"]["schemas"]["User"]["properties"]["operator"]

    # Then: the generator can preserve its existing enum class and default
    assert operator["title"] == "Operator"
    assert operator["default"] == "eq"
    assert operator["anyOf"] == [enum, {"type": "string"}]


@pytest.mark.parametrize(
    "enum",
    [
        {"type": "string", "enum": ["fixed"]},
        {"type": "string", "const": "fixed"},
        {"type": "string", "enum": ["a", "b"], "x-ms-enum": {"modelAsString": False}},
    ],
)
def test_constants_and_explicitly_closed_enums_are_unchanged(document: dict[str, Any], enum: dict[str, Any]) -> None:
    # Given: a value whose contract explicitly limits its alternatives
    document["components"]["schemas"]["Closed"] = enum
    document["components"]["schemas"]["User"]["properties"]["closed"] = {"$ref": "#/components/schemas/Closed"}

    # When: preparing the spec
    schemas = prepare_open_enums(document)["components"]["schemas"]

    # Then: closed values retain their original schema and references
    assert schemas["Closed"] == enum
    assert schemas["User"]["properties"]["closed"] == {"$ref": "#/components/schemas/Closed"}
