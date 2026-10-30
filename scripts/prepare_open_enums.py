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
    constants keep their names. Single-value enums remain constants. An API
    contract can explicitly close an enum with x-ms-enum.modelAsString=false.
    """
    schemas = document.get("components", {}).get("schemas", {})

    def enum_type(schema: dict[str, Any]) -> str | None:
        """Return the primitive type when a schema declares an open enum."""
        if not isinstance(schema, dict):
            return None
        if schema.get("x-ms-enum", {}).get("modelAsString") is False:
            return None
        values = [value for value in schema.get("enum", []) if value is not None]
        kind = schema.get("type")
        if len(values) > 1 and kind in ("string", "integer"):
            return kind
        return None

    references = {
        f"#/components/schemas/{name}": kind
        for name, schema in schemas.items()
        if (kind := enum_type(schema)) is not None
    }

    def open_type(schema: dict[str, Any]) -> str | None:
        """Resolve inline enum schemas and local enum references."""
        if not isinstance(schema, dict):
            return None
        return references.get(schema.get("$ref")) or enum_type(schema)

    def expand(value: Any, expand_enum: bool = True) -> Any:
        """Add primitive alternatives after known alternatives in each union."""
        if isinstance(value, list):
            return [expand(item) for item in value]
        if not isinstance(value, dict):
            return value

        kind = open_type(value) if expand_enum else None
        if kind is not None:
            annotations = {key: deepcopy(item) for key, item in value.items() if key not in ("$ref", "enum", "type")}
            # The generator ignores defaults beside a direct reference. Keep
            # that existing constructor behavior when wrapping the reference.
            if "$ref" in value:
                annotations.pop("default", None)
            return {**annotations, "anyOf": [deepcopy(value), {"type": kind}]}

        result = {}
        for key, item in value.items():
            if key not in ("anyOf", "oneOf"):
                result[key] = expand(item)
                continue

            alternatives = []
            kinds = []
            for alternative in item:
                alternative_kind = open_type(alternative)
                alternatives.append(expand(alternative, expand_enum=alternative_kind is None))
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
