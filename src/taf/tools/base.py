"""
Tool representation for the Twilio Agentic Framework.

Inspired by OpenAI's function_schema approach from openai-agents-python (MIT License).
"""

import inspect
import json
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Optional,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)


@dataclass
class TAFTool:
    """
    Represents a tool/function that can be used with LLMs.

    Similar to OpenAI's FuncSchema, this captures function metadata
    for LLM tool integration.
    """

    name: str
    description: str
    params_json_schema: dict[str, Any]
    implementation: Callable

    def to_openai_format(self) -> dict[str, Any]:
        """
        Get tool schema in OpenAI function calling format.

        Returns:
            Dictionary in OpenAI function format
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.params_json_schema,
            },
        }

    def to_anthropic_format(self) -> dict[str, Any]:
        """
        Get tool schema in Anthropic tool calling format.

        Returns:
            Dictionary in Anthropic tool format
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.params_json_schema,
        }

    def to_json(self) -> str:
        """Convert tool to JSON string (OpenAI format by default)."""
        return json.dumps(self.to_openai_format(), indent=2)


def _extract_schema_from_function(func: Callable) -> dict[str, Any]:
    """
    Extract JSON schema from function signature and type hints.

    Inspired by OpenAI's function_schema approach.

    Args:
        func: Function to extract schema from

    Returns:
        JSON schema dictionary
    """
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue

        param_type = type_hints.get(param_name, str)
        prop_schema = _type_to_json_schema(param_type)

        properties[param_name] = prop_schema

        # Add to required if no default value and not Optional
        if param.default == inspect.Parameter.empty and not _is_optional(param_type):
            required.append(param_name)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def _type_to_json_schema(param_type: Any) -> dict[str, Any]:
    """Convert Python type to JSON schema."""
    origin = get_origin(param_type)
    args = get_args(param_type)

    # Handle Optional[T] (Union[T, None])
    if origin is Union:
        if len(args) == 2 and type(None) in args:
            # Optional type - get the non-None type
            non_none_type = args[0] if args[1] is type(None) else args[1]
            return _type_to_json_schema(non_none_type)

    # Handle List[T]
    if origin is list or param_type is list:
        if args:
            item_type = args[0]
            return {"type": "array", "items": _type_to_json_schema(item_type)}
        else:
            return {"type": "array"}

    # Handle Dict[str, T]
    if origin is dict or param_type is dict:
        return {"type": "object"}

    # Basic types
    if param_type is str:
        return {"type": "string"}
    elif param_type is int:
        return {"type": "integer"}
    elif param_type is float:
        return {"type": "number"}
    elif param_type is bool:
        return {"type": "boolean"}

    # Default fallback
    return {"type": "string"}


def _is_optional(param_type: Any) -> bool:
    """Check if a type is Optional (Union with None)."""
    origin = get_origin(param_type)
    if origin is Union:
        args = get_args(param_type)
        return type(None) in args
    return False


def function_tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Callable:
    """
    Decorator to create a TAF tool from a function.

    Similar to OpenAI's function_tool decorator approach.

    Args:
        name: Optional name override (defaults to function name)
        description: Optional description override (defaults to docstring)

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> TAFTool:
        tool_name = name or func.__name__
        tool_description = description or (func.__doc__ or "").strip()

        if not tool_description:
            raise ValueError(f"Function {func.__name__} must have a docstring or description")

        schema = _extract_schema_from_function(func)

        return TAFTool(
            name=tool_name,
            description=tool_description,
            params_json_schema=schema,
            implementation=func,
        )

    return decorator


def create_tool(
    name: str,
    description: str,
    params_json_schema: dict[str, Any],
    implementation: Callable,
) -> TAFTool:
    """
    Create a TAF tool manually with explicit schema.

    Args:
        name: The name of the tool/function
        description: Description of what the tool does
        params_json_schema: JSON Schema for the tool's parameters
        implementation: Function that implements the tool's logic

    Returns:
        TAFTool instance
    """
    return TAFTool(
        name=name,
        description=description,
        params_json_schema=params_json_schema,
        implementation=implementation,
    )
