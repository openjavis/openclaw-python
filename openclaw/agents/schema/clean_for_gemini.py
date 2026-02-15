"""
Clean JSON Schema for Gemini Cloud Code Assist API

Cloud Code Assist API rejects a subset of JSON Schema keywords.
This module scrubs/normalizes tool schemas to keep Gemini happy.

Based on openclaw/src/agents/schema/clean-for-gemini.ts
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


# Keywords that Cloud Code Assist API rejects
GEMINI_UNSUPPORTED_SCHEMA_KEYWORDS = {
    "patternProperties",
    "additionalProperties",
    "$schema",
    "$id",
    "$ref",
    "$defs",
    "definitions",
    # Non-standard (OpenAPI) keyword
    "examples",
    # Cloud Code Assist validates tool schemas more strictly
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
    "multipleOf",
    "pattern",
    "format",
    "minItems",
    "maxItems",
    "uniqueItems",
    "minProperties",
    "maxProperties",
}


def try_flatten_literal_any_of(variants: list[Any]) -> dict[str, Any] | None:
    """
    Check if an anyOf/oneOf array contains only literal values that can be flattened.
    
    TypeBox Type.Literal generates { const: "value", type: "string" }.
    Some schemas may use { enum: ["value"], type: "string" }.
    Both patterns are flattened to { type: "string", enum: ["a", "b", ...] }.
    """
    if not variants:
        return None
    
    all_values = []
    common_type = None
    
    for variant in variants:
        if not isinstance(variant, dict):
            return None
        
        # Extract literal value
        if "const" in variant:
            literal_value = variant["const"]
        elif "enum" in variant and isinstance(variant["enum"], list) and len(variant["enum"]) == 1:
            literal_value = variant["enum"][0]
        else:
            return None
        
        # Check type consistency
        variant_type = variant.get("type") if isinstance(variant.get("type"), str) else None
        if not variant_type:
            return None
        
        if common_type is None:
            common_type = variant_type
        elif common_type != variant_type:
            return None
        
        all_values.append(literal_value)
    
    if common_type and all_values:
        return {"type": common_type, "enum": all_values}
    return None


def is_null_schema(variant: Any) -> bool:
    """Check if a variant represents null schema"""
    if not isinstance(variant, dict):
        return False
    
    # { const: null }
    if "const" in variant and variant["const"] is None:
        return True
    
    # { enum: [null] }
    if "enum" in variant and isinstance(variant["enum"], list) and len(variant["enum"]) == 1:
        return variant["enum"][0] is None
    
    # { type: "null" }
    type_value = variant.get("type")
    if type_value == "null":
        return True
    
    # { type: ["null"] }
    if isinstance(type_value, list) and len(type_value) == 1 and type_value[0] == "null":
        return True
    
    return False


def strip_null_variants(variants: list[Any]) -> tuple[list[Any], bool]:
    """Strip null variants from list"""
    if not variants:
        return variants, False
    
    non_null = [v for v in variants if not is_null_schema(v)]
    return non_null, len(non_null) != len(variants)


def extend_schema_defs(
    defs: dict[str, Any] | None,
    schema: dict[str, Any]
) -> dict[str, Any] | None:
    """Extract and merge $defs and definitions"""
    defs_entry = schema.get("$defs") if isinstance(schema.get("$defs"), dict) else None
    legacy_defs_entry = schema.get("definitions") if isinstance(schema.get("definitions"), dict) else None
    
    if not defs_entry and not legacy_defs_entry:
        return defs
    
    next_defs = dict(defs) if defs else {}
    
    if defs_entry:
        next_defs.update(defs_entry)
    if legacy_defs_entry:
        next_defs.update(legacy_defs_entry)
    
    return next_defs


def decode_json_pointer_segment(segment: str) -> str:
    """Decode JSON pointer segment"""
    return segment.replace("~1", "/").replace("~0", "~")


def try_resolve_local_ref(ref: str, defs: dict[str, Any] | None) -> Any:
    """Try to resolve local $ref"""
    if not defs:
        return None
    
    # Match #/$defs/name or #/definitions/name
    if ref.startswith("#/$defs/"):
        name = decode_json_pointer_segment(ref[8:])
        return defs.get(name)
    elif ref.startswith("#/definitions/"):
        name = decode_json_pointer_segment(ref[14:])
        return defs.get(name)
    
    return None


def clean_schema_for_gemini_with_defs(
    schema: Any,
    defs: dict[str, Any] | None = None,
    ref_stack: set[str] | None = None,
) -> Any:
    """Clean schema for Gemini (internal recursive function)"""
    
    # Base cases
    if schema is None or not isinstance(schema, (dict, list)):
        return schema
    
    if isinstance(schema, list):
        return [clean_schema_for_gemini_with_defs(item, defs, ref_stack) for item in schema]
    
    obj = schema
    next_defs = extend_schema_defs(defs, obj)
    
    # Handle $ref
    ref_value = obj.get("$ref") if isinstance(obj.get("$ref"), str) else None
    if ref_value:
        # Circular reference detection
        if ref_stack and ref_value in ref_stack:
            return {}
        
        # Try to resolve
        resolved = try_resolve_local_ref(ref_value, next_defs)
        if resolved:
            next_ref_stack = set(ref_stack) if ref_stack else set()
            next_ref_stack.add(ref_value)
            
            cleaned = clean_schema_for_gemini_with_defs(resolved, next_defs, next_ref_stack)
            if isinstance(cleaned, dict):
                # Preserve description, title, default from original
                result = dict(cleaned)
                for key in ["description", "title", "default"]:
                    if key in obj and obj[key] is not None:
                        result[key] = obj[key]
                return result
            return cleaned
        
        # Unresolvable ref - keep metadata
        result = {}
        for key in ["description", "title", "default"]:
            if key in obj and obj[key] is not None:
                result[key] = obj[key]
        return result
    
    # Handle anyOf/oneOf
    has_any_of = "anyOf" in obj and isinstance(obj["anyOf"], list)
    has_one_of = "oneOf" in obj and isinstance(obj["oneOf"], list)
    
    cleaned_any_of = None
    cleaned_one_of = None
    
    if has_any_of:
        cleaned_any_of = [
            clean_schema_for_gemini_with_defs(variant, next_defs, ref_stack)
            for variant in obj["anyOf"]
        ]
        
        # Strip null variants
        non_null_variants, stripped = strip_null_variants(cleaned_any_of)
        if stripped:
            cleaned_any_of = non_null_variants
        
        # Try to flatten literals
        flattened = try_flatten_literal_any_of(non_null_variants)
        if flattened:
            result = dict(flattened)
            for key in ["description", "title", "default"]:
                if key in obj and obj[key] is not None:
                    result[key] = obj[key]
            return result
        
        # If stripped to single variant, unwrap
        if stripped and len(non_null_variants) == 1:
            lone = non_null_variants[0]
            if isinstance(lone, dict):
                result = dict(lone)
                for key in ["description", "title", "default"]:
                    if key in obj and obj[key] is not None:
                        result[key] = obj[key]
                return result
            return lone
    
    if has_one_of:
        cleaned_one_of = [
            clean_schema_for_gemini_with_defs(variant, next_defs, ref_stack)
            for variant in obj["oneOf"]
        ]
        
        # Strip null variants
        non_null_variants, stripped = strip_null_variants(cleaned_one_of)
        if stripped:
            cleaned_one_of = non_null_variants
        
        # Try to flatten literals
        flattened = try_flatten_literal_any_of(non_null_variants)
        if flattened:
            result = dict(flattened)
            for key in ["description", "title", "default"]:
                if key in obj and obj[key] is not None:
                    result[key] = obj[key]
            return result
        
        # If stripped to single variant, unwrap
        if stripped and len(non_null_variants) == 1:
            lone = non_null_variants[0]
            if isinstance(lone, dict):
                result = dict(lone)
                for key in ["description", "title", "default"]:
                    if key in obj and obj[key] is not None:
                        result[key] = obj[key]
                return result
            return lone
    
    # Build cleaned object
    cleaned = {}
    
    for key, value in obj.items():
        # Skip unsupported keywords
        if key in GEMINI_UNSUPPORTED_SCHEMA_KEYWORDS:
            continue
        
        # Convert const to enum
        if key == "const":
            cleaned["enum"] = [value]
            continue
        
        # Skip type if anyOf/oneOf present
        if key == "type" and (has_any_of or has_one_of):
            continue
        
        # Filter null from type array
        if key == "type" and isinstance(value, list):
            types = [t for t in value if t != "null"]
            cleaned["type"] = types[0] if len(types) == 1 else types
            continue
        
        # Recursively clean properties
        if key == "properties" and isinstance(value, dict):
            cleaned[key] = {
                k: clean_schema_for_gemini_with_defs(v, next_defs, ref_stack)
                for k, v in value.items()
            }
        # Recursively clean items
        elif key == "items":
            if isinstance(value, list):
                cleaned[key] = [
                    clean_schema_for_gemini_with_defs(item, next_defs, ref_stack)
                    for item in value
                ]
            elif isinstance(value, dict):
                cleaned[key] = clean_schema_for_gemini_with_defs(value, next_defs, ref_stack)
            else:
                cleaned[key] = value
        # Use pre-cleaned anyOf/oneOf if available
        elif key == "anyOf" and isinstance(value, list):
            cleaned[key] = cleaned_any_of or [
                clean_schema_for_gemini_with_defs(variant, next_defs, ref_stack)
                for variant in value
            ]
        elif key == "oneOf" and isinstance(value, list):
            cleaned[key] = cleaned_one_of or [
                clean_schema_for_gemini_with_defs(variant, next_defs, ref_stack)
                for variant in value
            ]
        # Recursively clean allOf
        elif key == "allOf" and isinstance(value, list):
            cleaned[key] = [
                clean_schema_for_gemini_with_defs(variant, next_defs, ref_stack)
                for variant in value
            ]
        else:
            cleaned[key] = value
    
    return cleaned


def clean_schema_for_gemini(schema: Any) -> Any:
    """
    Clean JSON Schema for Gemini Cloud Code Assist API.
    
    Removes unsupported keywords and normalizes schema structure:
    - Removes: patternProperties, additionalProperties, $ref, $defs, etc.
    - Converts: const → enum, type array → single type (filtering null)
    - Flattens: anyOf/oneOf with literals → enum
    - Strips: null variants from anyOf/oneOf
    
    Args:
        schema: Input JSON Schema (dict or any JSON-serializable type)
    
    Returns:
        Cleaned schema compatible with Gemini API
    
    Example:
        >>> schema = {
        ...     "type": "object",
        ...     "properties": {
        ...         "name": {
        ...             "type": "string",
        ...             "minLength": 1,  # Will be removed
        ...             "pattern": "^[a-z]+$"  # Will be removed
        ...         }
        ...     }
        ... }
        >>> clean_schema_for_gemini(schema)
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            }
        }
    """
    if schema is None or not isinstance(schema, (dict, list)):
        return schema
    
    if isinstance(schema, list):
        return [clean_schema_for_gemini(item) for item in schema]
    
    defs = extend_schema_defs(None, schema)
    return clean_schema_for_gemini_with_defs(schema, defs, None)


__all__ = ["clean_schema_for_gemini", "GEMINI_UNSUPPORTED_SCHEMA_KEYWORDS"]
