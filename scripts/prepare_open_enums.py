"""Expand extensible enum uses for SDK generation without changing their classes."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


def prepare_open_enums(document: dict[str, Any]) -> dict[str, Any]:
    """Allow raw values alongside known string and integer enum members.

    Named enum definitions remain unchanged, so existing enum classes and
    constants keep their names. Constants and discriminator fields remain
    closed. Other enums, including singleton enums, accept future values.
    A contract can explicitly close an enum with x-ms-enum.modelAsString=false.
    """
    schemas = document.get("components", {}).get("schemas", {})

    def enum_type(schema: dict[str, Any]) -> str | None:
        """Return the primitive type when a schema declares an open enum."""
        if not isinstance(schema, dict):
            return None
        if "const" in schema or schema.get("x-ms-enum", {}).get("modelAsString") is False:
            return None
        values = [value for value in schema.get("enum", []) if value is not None]
        value_types = {type(value) for value in values}
        kind = "string" if value_types == {str} else "integer" if value_types == {int} else None
        declared = schema.get("type")
        if kind is not None and (
            declared is None or declared == kind or (isinstance(declared, list) and kind in declared)
        ):
            return kind
        return None

    references = {
        f"#/components/schemas/{name}": kind
        for name, schema in schemas.items()
        if (kind := enum_type(schema)) is not None
    }

    closed_fields: set[int] = set()

    def find_discriminators(value: Any) -> None:
        """Keep discriminator fields strict even when they use enum references."""
        if isinstance(value, list):
            for item in value:
                find_discriminators(item)
        elif isinstance(value, dict):
            discriminator = value.get("discriminator", {})
            name = discriminator.get("propertyName")
            if isinstance(name, str):
                variants = value.get("oneOf", []) + value.get("anyOf", [])
                variants += [{"$ref": ref} for ref in discriminator.get("mapping", {}).values()]
                for variant in variants:
                    target = schemas.get(variant.get("$ref", "").removeprefix("#/components/schemas/"), variant)
                    field = target.get("properties", {}).get(name)
                    if field is not None:
                        closed_fields.add(id(field))
            for item in value.values():
                find_discriminators(item)

    find_discriminators(document)

    def open_type(schema: dict[str, Any]) -> str | None:
        """Resolve inline enum schemas and local enum references."""
        if not isinstance(schema, dict) or id(schema) in closed_fields:
            return None
        if "const" in schema or schema.get("x-ms-enum", {}).get("modelAsString") is False:
            return None
        if len(schema.get("allOf", [])) == 1:
            return open_type(schema["allOf"][0])
        return references.get(schema.get("$ref")) or enum_type(schema)

    def merge_enum_arrays(alternatives: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Try all known item enums before a primitive can accept the array."""
        result: list[dict[str, Any]] = []
        for alternative in alternatives:
            item = alternative.get("items", {})
            if alternative.get("type") != "array" or item.get("$ref") not in references:
                result.append(alternative)
                continue
            shape = {key: item for key, item in alternative.items() if key != "items"}
            for index, existing in enumerate(result):
                if shape != {key: item for key, item in existing.items() if key != "items"}:
                    continue
                existing_items = existing.get("items", {})
                choices = existing_items.get("anyOf", [existing_items])
                if all(choice.get("$ref") in references for choice in choices):
                    result[index] = {**shape, "items": {"anyOf": [*choices, item]}}
                    break
            else:
                result.append(alternative)
        return result

    def expand(value: Any, expand_enum: bool = True, field_name: str | None = None) -> Any:
        """Add primitive alternatives after known alternatives in each union."""
        if isinstance(value, list):
            return [expand(item) for item in value]
        if not isinstance(value, dict):
            return value
        if id(value) in closed_fields:
            return deepcopy(value)

        kind = open_type(value)
        if kind is not None:
            known = deepcopy(value["allOf"][0] if "allOf" in value else value)
            if "enum" in known and "title" not in known and field_name is not None:
                known["title"] = field_name
            if not expand_enum:
                return deepcopy(value) if "allOf" in value else known
            annotations = {
                key: deepcopy(item) for key, item in value.items() if key not in ("$ref", "enum", "type", "allOf")
            }
            # The generator ignores defaults beside a direct reference. Keep
            # that existing constructor behavior when wrapping the reference.
            if "$ref" in value:
                annotations.pop("default", None)
            return {**annotations, "anyOf": [known, {"type": kind}]}

        result = {}
        for key, item in value.items():
            if key in ("properties", "schemas"):
                result[key] = {name: expand(schema, field_name=name) for name, schema in item.items()}
                continue
            if key == "additionalProperties":
                result[key] = expand(item, field_name="AdditionalProperty")
                continue
            if key not in ("anyOf", "oneOf"):
                result[key] = expand(item, field_name=f"{field_name}_item" if key == "items" and field_name else None)
                continue

            alternatives = []
            kinds = []
            indices = {id(alternative): index for index, alternative in enumerate(item)}
            for index, alternative in enumerate(merge_enum_arrays(item)):
                alternative_kind = open_type(alternative)
                title = alternative.get("title")
                suffix = (
                    title
                    if title is not None and title != value.get("title")
                    else f"type_{indices.get(id(alternative), index)}"
                )
                alternative_name = f"{field_name}_{suffix}" if field_name else None
                alternatives.append(
                    expand(alternative, expand_enum=alternative_kind is None, field_name=alternative_name)
                )
                if alternative_kind is not None and alternative_kind not in kinds:
                    kinds.append(alternative_kind)
            for alternative_kind in kinds:
                primitive = {"type": alternative_kind}
                if primitive not in alternatives:
                    alternatives.append(primitive)
            # The enum and its primitive overlap, which requires anyOf.
            result["anyOf" if kinds else key] = alternatives
        return result

    prepared = expand(document)
    for name, schema in schemas.items():
        if enum_type(schema) is not None:
            prepared["components"]["schemas"][name] = deepcopy(schema)
    return prepared


def main() -> None:
    """Write a temporary generation spec with extensible enum uses."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    document = yaml.safe_load(args.source.read_text())
    args.destination.write_text(json.dumps(prepare_open_enums(document)))


if __name__ == "__main__":
    main()
