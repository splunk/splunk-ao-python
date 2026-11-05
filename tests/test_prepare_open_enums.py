"""Schema preparation for extensible generated enums."""

import importlib
import json
import sys
from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from openapi_python_client import generate
from openapi_python_client.config import Config, ConfigFile, MetaType

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


@pytest.fixture(scope="module")
def generated_models(tmp_path_factory: pytest.TempPathFactory) -> Iterator[ModuleType]:
    """Generate and import a small client that exercises the schema boundaries."""
    root = tmp_path_factory.mktemp("open-enum-client")
    schema = {
        "openapi": "3.1.0",
        "info": {"title": "Enum fixture", "version": "1"},
        "paths": {},
        "components": {
            "schemas": {
                "Role": {"type": "string", "enum": ["user", "admin"]},
                "InferredRole": {"enum": ["user", "admin"]},
                "NullableRole": {"type": ["string", "null"], "enum": ["user", "admin", None]},
                "ClosedRole": {"type": "string", "enum": ["user", "admin"], "x-ms-enum": {"modelAsString": False}},
                "Label": {"type": "string", "enum": ["sample"]},
                "NumericMethod": {"type": "string", "enum": ["mean", "sum"]},
                "CategoricalMethod": {"type": "string", "enum": ["category_count"]},
                "User": {
                    "type": "object",
                    "properties": {
                        "role": {"type": "string", "enum": ["user", "admin"]},
                        "wrapped_role": {"allOf": [{"$ref": "#/components/schemas/Role"}], "default": "user"},
                        "nullable_wrapped_role": {
                            "anyOf": [{"allOf": [{"$ref": "#/components/schemas/Role"}]}, {"type": "null"}]
                        },
                        "inferred_role": {"$ref": "#/components/schemas/InferredRole"},
                        "nullable_role": {"$ref": "#/components/schemas/NullableRole"},
                        "closed_role": {"$ref": "#/components/schemas/ClosedRole"},
                        "labels": {"type": "array", "items": {"$ref": "#/components/schemas/Label"}},
                        "role_groups": {
                            "type": "array",
                            "items": {"type": "array", "items": {"$ref": "#/components/schemas/Role"}},
                        },
                        "nullable_roles": {
                            "anyOf": [
                                {"type": "array", "items": {"type": "string", "enum": ["user", "admin"]}},
                                {"type": "null"},
                            ]
                        },
                        "methods": {
                            "anyOf": [
                                {"type": "array", "items": {"$ref": "#/components/schemas/NumericMethod"}},
                                {"type": "array", "items": {"$ref": "#/components/schemas/CategoricalMethod"}},
                                {"type": "null"},
                            ]
                        },
                    },
                },
                "Cat": {"type": "object", "properties": {"kind": {"type": "string", "enum": ["cat"]}}},
                "RoleMap": {"type": "object", "additionalProperties": {"type": "string", "enum": ["reader", "writer"]}},
                "Dog": {"type": "object", "properties": {"kind": {"type": "string", "enum": ["dog"]}}},
                "Animal": {
                    "oneOf": [{"$ref": "#/components/schemas/Cat"}, {"$ref": "#/components/schemas/Dog"}],
                    "discriminator": {"propertyName": "kind"},
                },
            }
        },
    }
    original = deepcopy(schema)
    prepared = prepare_open_enums(schema)
    assert schema == original
    assert prepare_open_enums(prepared) == prepared
    assert prepared["components"]["schemas"]["Cat"] == schema["components"]["schemas"]["Cat"]
    spec = root / "openapi.json"
    spec.write_text(json.dumps(prepared))
    config = Config.from_sources(ConfigFile(post_hooks=[]), MetaType.NONE, spec, "utf-8", False, root / "enum_fixture")
    assert not generate(config=config, custom_template_path=Path(__file__).parent.parent / "codegen_templates")
    sys.path.insert(0, str(root))
    try:
        yield importlib.import_module("enum_fixture.models")
    finally:
        sys.path.remove(str(root))
        for name in list(sys.modules):
            if name == "enum_fixture" or name.startswith("enum_fixture."):
                del sys.modules[name]


@pytest.mark.parametrize("field", ["role", "wrapped_role", "nullable_wrapped_role", "inferred_role", "nullable_role"])
def test_generated_enum_shapes_preserve_known_and_future_values(generated_models: ModuleType, field: str) -> None:
    """Supported enum schema shapes all produce scalar fields with lossless fallback."""
    for value in ["user", "future_role"]:
        user = generated_models.User.from_dict({field: value})
        parsed = getattr(user, field)
        assert parsed == value
        if value == "future_role":
            assert type(parsed) is str
        else:
            assert parsed.value == "user"
        assert user.to_dict()[field] == value
    assert generated_models.User().wrapped_role.value == "user"
    assert generated_models.User.from_dict({"nullable_role": None}).nullable_role is None


def test_generated_inline_enum_keeps_its_original_class_name(generated_models: ModuleType) -> None:
    """The wrapper must not add Type0 to the original inline enum class name."""
    assert generated_models.User.from_dict({"role": "user"}).role is generated_models.UserRole.USER
    user = generated_models.User.from_dict({"nullable_roles": ["user", "future_role"]})
    assert user.nullable_roles[0] is generated_models.UserNullableRolesType0Item.USER
    assert type(user.nullable_roles[1]) is str
    mapping = generated_models.RoleMap.from_dict({"x": "reader", "y": "future_role"})
    assert mapping["x"] is generated_models.RoleMapAdditionalProperty.READER
    assert mapping.to_dict() == {"x": "reader", "y": "future_role"}


def test_generated_enum_arrays_try_all_known_item_types(generated_models: ModuleType) -> None:
    """A known later enum member must beat a primitive fallback in an earlier array."""
    user = generated_models.User.from_dict({"methods": ["category_count", "mean", "future_method"], "labels": ["new"]})
    assert user.methods[0] is generated_models.CategoricalMethod.CATEGORY_COUNT
    assert user.methods[1] is generated_models.NumericMethod.MEAN
    assert type(user.methods[2]) is str
    assert user.to_dict()["methods"] == ["category_count", "mean", "future_method"]
    assert user.labels == ["new"]
    assert generated_models.User.from_dict({"labels": ["sample"]}).labels[0] is generated_models.Label.SAMPLE
    assert generated_models.User.from_dict({"methods": None}).to_dict()["methods"] is None


@pytest.mark.parametrize("field", ["labels", "methods", "role_groups"])
@pytest.mark.parametrize("value", ["future_value", {"future_value": True}, 1])
def test_generated_enum_arrays_reject_non_arrays(generated_models: ModuleType, field: str, value: object) -> None:
    """Opening array items must not relax the enclosing container's shape."""
    with pytest.raises(TypeError):
        generated_models.User.from_dict({field: value})
    with pytest.raises(TypeError):
        generated_models.User(**{field: value}).to_dict()


@pytest.mark.parametrize("value", ["future_value", {"future_value": True}])
def test_generated_nested_enum_arrays_reject_non_arrays(generated_models: ModuleType, value: object) -> None:
    """Both outer and nested enum-array containers must retain their shape."""
    with pytest.raises(TypeError):
        generated_models.User.from_dict({"role_groups": [value]})
    with pytest.raises(TypeError):
        generated_models.User(role_groups=[value]).to_dict()


def test_generated_discriminator_enum_stays_closed(generated_models: ModuleType) -> None:
    """A singleton discriminator is a tag, rather than an extensible data enum."""
    assert generated_models.Cat.from_dict({"kind": "cat"}).kind.value == "cat"
    with pytest.raises(ValueError):
        generated_models.Cat.from_dict({"kind": "future_animal"})
    with pytest.raises(ValueError):
        generated_models.User.from_dict({"closed_role": "future_role"})
