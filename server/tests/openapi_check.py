"""Checks API responses against the OpenAPI document.

A small validator for the part of JSON Schema the document uses. It fails loudly
on any keyword it does not know, so it can never pass a schema it did not check.
"""

import re

_CHECKED = {"$ref", "anyOf", "type", "enum", "properties", "required", "additionalProperties", "items"}
# Documentation-only keywords, or ones that only constrain requests.
_IGNORED = {"description", "example", "format", "minItems", "maxItems"}

_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def find_operation(spec: dict, method: str, path: str) -> dict | None:
    """The documented operation for a concrete request path, e.g. /abc/draw -> /{sessionId}/draw."""
    candidates = []
    for template, operations in spec["paths"].items():
        pattern = "^" + re.sub(r"\{[^}]+\}", "[^/]+", template) + "$"
        if re.match(pattern, path) and method.lower() in operations:
            candidates.append((template.count("{"), operations[method.lower()]))
    # A literal path (/squads) wins over a templated one.
    return min(candidates, key=lambda c: c[0])[1] if candidates else None


def response_problems(spec: dict, method: str, path: str, status: int, body) -> list[str]:
    """Why a response does not match the document; empty when it does or the route is undocumented."""
    operation = find_operation(spec, method, path)
    if operation is None:
        return []
    response = operation["responses"].get(str(status))
    if response is None:
        return [f"{method} {path}: status {status} is not documented"]
    schema = response["content"]["application/json"]["schema"]
    return [f"{method} {path} -> {status}: {p}" for p in schema_problems(spec, body, schema)]


def schema_problems(spec: dict, value, schema: dict, at: str = "$") -> list[str]:
    unknown = set(schema) - _CHECKED - _IGNORED
    if unknown:
        raise AssertionError(f"{at}: openapi_check does not support {sorted(unknown)}")
    if "$ref" in schema:
        return schema_problems(spec, value, resolve(spec, schema["$ref"]), at)
    if "anyOf" in schema:
        attempts = [schema_problems(spec, value, option, at) for option in schema["anyOf"]]
        return [] if any(not attempt for attempt in attempts) else [f"{at}: matches no option of anyOf {attempts}"]

    types = schema.get("type")
    if types is not None:
        types = [types] if isinstance(types, str) else types
        if not any(_TYPES[t](value) for t in types):
            return [f"{at}: expected {'/'.join(types)}, got {type(value).__name__} {value!r:.60}"]
    if "enum" in schema and value not in schema["enum"]:
        return [f"{at}: {value!r} is not one of {schema['enum']}"]

    problems = []
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        problems += [f"{at}: missing '{key}'" for key in schema.get("required", []) if key not in value]
        extra = schema.get("additionalProperties")
        if extra is False:
            problems += [f"{at}: undocumented field '{key}'" for key in value if key not in properties]
        elif isinstance(extra, dict):  # a map: every other key's value must match this schema
            for key in value:
                if key not in properties:
                    problems += schema_problems(spec, value[key], extra, f"{at}.{key}")
        for key, subschema in properties.items():
            if key in value:
                problems += schema_problems(spec, value[key], subschema, f"{at}.{key}")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            problems += schema_problems(spec, item, schema["items"], f"{at}[{index}]")
    return problems


def resolve(spec: dict, ref: str) -> dict:
    node = spec
    for part in ref.removeprefix("#/").split("/"):
        node = node[part]
    return node
