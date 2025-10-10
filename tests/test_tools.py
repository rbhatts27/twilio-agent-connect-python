"""Tests for TAF tools."""

import json
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from taf.core.config import TAFConfig
from taf.core.context import ConversationSession
from taf.tools.base import (
    TAFTool,
    _extract_schema_from_function,
    _is_optional,
    _type_to_json_schema,
    create_tool,
    function_tool,
)
from taf.tools.memory import create_memory_tools


class TestTAFTool:
    """Test TAFTool class."""

    def test_taf_tool_creation(self):
        """Test TAFTool can be created with required fields."""

        def dummy_func(x: str) -> str:
            return x

        tool = TAFTool(
            name="test_tool",
            description="A test tool",
            params_json_schema={
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": ["x"],
            },
            implementation=dummy_func,
        )

        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.implementation == dummy_func

    def test_to_openai_format(self):
        """Test conversion to OpenAI function format."""

        def dummy_func(x: str) -> str:
            return x

        tool = TAFTool(
            name="test_tool",
            description="A test tool",
            params_json_schema={
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": ["x"],
            },
            implementation=dummy_func,
        )

        openai_format = tool.to_openai_format()

        assert openai_format["type"] == "function"
        assert openai_format["function"]["name"] == "test_tool"
        assert openai_format["function"]["description"] == "A test tool"
        assert openai_format["function"]["parameters"]["type"] == "object"
        assert "x" in openai_format["function"]["parameters"]["properties"]

    def test_to_anthropic_format(self):
        """Test conversion to Anthropic tool format."""

        def dummy_func(x: str) -> str:
            return x

        tool = TAFTool(
            name="test_tool",
            description="A test tool",
            params_json_schema={
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": ["x"],
            },
            implementation=dummy_func,
        )

        anthropic_format = tool.to_anthropic_format()

        assert anthropic_format["name"] == "test_tool"
        assert anthropic_format["description"] == "A test tool"
        assert anthropic_format["input_schema"]["type"] == "object"
        assert "x" in anthropic_format["input_schema"]["properties"]

    def test_to_json(self):
        """Test conversion to JSON string."""

        def dummy_func(x: str) -> str:
            return x

        tool = TAFTool(
            name="test_tool",
            description="A test tool",
            params_json_schema={
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": ["x"],
            },
            implementation=dummy_func,
        )

        json_str = tool.to_json()
        parsed = json.loads(json_str)

        assert parsed["type"] == "function"
        assert parsed["function"]["name"] == "test_tool"


class TestFunctionTool:
    """Test function_tool decorator."""

    def test_basic_function_tool(self):
        """Test basic function_tool decoration."""

        @function_tool()
        def simple_tool(message: str) -> str:
            """Send a simple message."""
            return f"Sent: {message}"

        assert isinstance(simple_tool, TAFTool)
        assert simple_tool.name == "simple_tool"
        assert simple_tool.description == "Send a simple message."
        assert simple_tool.params_json_schema["type"] == "object"
        assert "message" in simple_tool.params_json_schema["properties"]
        assert simple_tool.params_json_schema["properties"]["message"]["type"] == "string"
        assert simple_tool.params_json_schema["required"] == ["message"]

    def test_function_tool_with_name_override(self):
        """Test function_tool with custom name."""

        @function_tool(name="custom_name")
        def simple_tool(message: str) -> str:
            """Send a simple message."""
            return f"Sent: {message}"

        assert simple_tool.name == "custom_name"

    def test_function_tool_with_description_override(self):
        """Test function_tool with custom description."""

        @function_tool(description="Custom description")
        def simple_tool(message: str) -> str:
            """Send a simple message."""
            return f"Sent: {message}"

        assert simple_tool.description == "Custom description"

    def test_function_tool_without_docstring_fails(self):
        """Test function_tool without docstring raises error."""
        with pytest.raises(ValueError, match="must have a docstring or description"):

            @function_tool()
            def no_docstring(message: str) -> str:
                return message

    def test_function_tool_with_optional_params(self):
        """Test function_tool with optional parameters."""

        @function_tool()
        def optional_tool(required: str, optional: Optional[str] = None) -> str:
            """Tool with optional parameters."""
            return f"{required} - {optional}"

        assert "required" in optional_tool.params_json_schema["required"]
        assert "optional" not in optional_tool.params_json_schema["required"]

    def test_function_tool_with_default_values(self):
        """Test function_tool with default values."""

        @function_tool()
        def default_tool(message: str, priority: int = 1) -> str:
            """Tool with default values."""
            return f"{message} (priority: {priority})"

        assert "message" in default_tool.params_json_schema["required"]
        assert "priority" not in default_tool.params_json_schema["required"]

    def test_function_tool_execution(self):
        """Test that decorated function can still be executed."""

        @function_tool()
        def add_numbers(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        result = add_numbers.implementation(5, 3)
        assert result == 8

    def test_function_tool_with_list_params(self):
        """Test function_tool with list parameters."""

        @function_tool()
        def list_tool(items: list[str]) -> str:
            """Process a list of items."""
            return ", ".join(items)

        schema = list_tool.params_json_schema
        assert schema["properties"]["items"]["type"] == "array"
        assert schema["properties"]["items"]["items"]["type"] == "string"

    def test_function_tool_with_multiple_types(self):
        """Test function_tool with various parameter types."""

        @function_tool()
        def multi_type_tool(
            text: str, number: int, decimal: float, flag: bool, items: list[str]
        ) -> dict:
            """Tool with multiple parameter types."""
            return {
                "text": text,
                "number": number,
                "decimal": decimal,
                "flag": flag,
                "items": items,
            }

        props = multi_type_tool.params_json_schema["properties"]
        assert props["text"]["type"] == "string"
        assert props["number"]["type"] == "integer"
        assert props["decimal"]["type"] == "number"
        assert props["flag"]["type"] == "boolean"
        assert props["items"]["type"] == "array"

    def test_function_tool_with_literal_and_enum(self):
        """Test function_tool with Literal types (enhanced capability)."""
        from enum import Enum
        from typing import Literal

        class Priority(str, Enum):
            LOW = "low"
            MEDIUM = "medium"
            HIGH = "high"

        @function_tool()
        def send_notification(
            channel: Literal["sms", "voice", "email"],
            message: str,
            priority: Priority = Priority.LOW,
        ) -> dict:
            """Send a notification through specified channel."""
            return {"channel": channel, "message": message, "priority": priority.value}

        # Verify channel parameter has enum constraint
        channel_schema = send_notification.params_json_schema["properties"]["channel"]
        assert channel_schema["type"] == "string"
        assert set(channel_schema["enum"]) == {"sms", "voice", "email"}

        # Verify priority parameter has enum constraint
        priority_schema = send_notification.params_json_schema["properties"]["priority"]
        assert priority_schema["type"] == "string"
        assert set(priority_schema["enum"]) == {"low", "medium", "high"}

        # Verify required fields
        assert "channel" in send_notification.params_json_schema["required"]
        assert "message" in send_notification.params_json_schema["required"]
        assert "priority" not in send_notification.params_json_schema["required"]


class TestCreateTool:
    """Test create_tool function."""

    def test_create_tool_manually(self):
        """Test manual tool creation with explicit schema."""

        def custom_impl(x: str) -> str:
            return x.upper()

        tool = create_tool(
            name="manual_tool",
            description="Manually created tool",
            params_json_schema={
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": ["x"],
            },
            implementation=custom_impl,
        )

        assert isinstance(tool, TAFTool)
        assert tool.name == "manual_tool"
        assert tool.description == "Manually created tool"
        assert tool.implementation(x="test") == "TEST"


class TestTypeToJsonSchema:
    """Test _type_to_json_schema function."""

    def test_basic_types(self):
        """Test conversion of basic Python types."""
        assert _type_to_json_schema(str) == {"type": "string"}
        assert _type_to_json_schema(int) == {"type": "integer"}
        assert _type_to_json_schema(float) == {"type": "number"}
        assert _type_to_json_schema(bool) == {"type": "boolean"}

    def test_optional_type(self):
        """Test conversion of Optional types."""
        schema = _type_to_json_schema(Optional[str])
        assert schema == {"type": "string"}

    def test_list_type(self):
        """Test conversion of List types."""
        schema = _type_to_json_schema(list[str])
        assert schema == {"type": "array", "items": {"type": "string"}}

    def test_dict_type(self):
        """Test conversion of dict type."""
        schema = _type_to_json_schema(dict)
        # TypeAdapter generates more complete schema with additionalProperties
        assert schema == {"type": "object", "additionalProperties": True}

    def test_plain_list_type(self):
        """Test conversion of plain list without type parameter."""
        schema = _type_to_json_schema(list)
        # TypeAdapter generates more complete schema with items field
        assert schema == {"type": "array", "items": {}}

    def test_literal_type(self):
        """Test conversion of Literal types (new capability with TypeAdapter)."""
        from typing import Literal

        schema = _type_to_json_schema(Literal["sms", "voice", "email"])
        assert schema["type"] == "string"
        assert set(schema["enum"]) == {"sms", "voice", "email"}

    def test_literal_int_type(self):
        """Test conversion of Literal with integers."""
        from typing import Literal

        schema = _type_to_json_schema(Literal[1, 2, 3])
        assert "enum" in schema
        assert set(schema["enum"]) == {1, 2, 3}

    def test_complex_union_type(self):
        """Test conversion of complex Union types (new capability)."""
        from typing import Union

        schema = _type_to_json_schema(Union[str, int])
        # TypeAdapter handles complex unions with anyOf
        assert "anyOf" in schema
        types = [item.get("type") for item in schema["anyOf"]]
        assert "string" in types
        assert "integer" in types

    def test_enum_type(self):
        """Test conversion of Enum types (new capability with TypeAdapter)."""
        from enum import Enum

        class Channel(str, Enum):
            SMS = "sms"
            VOICE = "voice"
            EMAIL = "email"

        schema = _type_to_json_schema(Channel)
        assert schema["type"] == "string"
        assert set(schema["enum"]) == {"sms", "voice", "email"}


class TestIsOptional:
    """Test _is_optional function."""

    def test_optional_type_returns_true(self):
        """Test that Optional[T] is detected as optional."""
        assert _is_optional(Optional[str]) is True

    def test_non_optional_type_returns_false(self):
        """Test that non-Optional types are not detected as optional."""
        assert _is_optional(str) is False
        assert _is_optional(int) is False


class TestExtractSchemaFromFunction:
    """Test _extract_schema_from_function."""

    def test_extract_simple_function_schema(self):
        """Test schema extraction from simple function."""

        def simple_func(name: str, age: int) -> str:
            return f"{name} is {age}"

        schema = _extract_schema_from_function(simple_func)

        assert schema["type"] == "object"
        assert "name" in schema["properties"]
        assert "age" in schema["properties"]
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["age"]["type"] == "integer"
        assert set(schema["required"]) == {"name", "age"}

    def test_extract_schema_with_optional(self):
        """Test schema extraction with optional parameters."""

        def optional_func(required: str, optional: Optional[str] = None) -> str:
            return required

        schema = _extract_schema_from_function(optional_func)

        assert "required" in schema["required"]
        assert "optional" not in schema["required"]

    def test_extract_schema_with_defaults(self):
        """Test schema extraction with default values."""

        def default_func(name: str, count: int = 10) -> str:
            return name

        schema = _extract_schema_from_function(default_func)

        assert "name" in schema["required"]
        assert "count" not in schema["required"]

    def test_extract_schema_ignores_self(self):
        """Test that schema extraction ignores 'self' parameter."""

        class TestClass:
            def method(self, value: str) -> str:
                return value

        schema = _extract_schema_from_function(TestClass.method)

        assert "self" not in schema["properties"]
        assert "value" in schema["properties"]


class TestMemoryTools:
    """Test create_memory_tools function."""

    def test_create_memory_tools_returns_list(self):
        """Test that create_memory_tools returns a list of tools."""
        config = TAFConfig(
            twilio_account_sid="ACtest",
            twilio_auth_token="test_token",
            memora_base_url="https://memory.twilio.com/v1",
            memory_service_sid="MGtest",
            maestro_base_url="https://maestro.twilio.com/v1",
            conversation_service_sid="IStest",
            twilio_phone_number="+15551234567",
        )
        session = ConversationSession(
            profile_id="prof_123", conversation_id="conv_123", channel="sms"
        )

        tools = create_memory_tools(config, session)

        assert isinstance(tools, list)
        assert len(tools) > 0
        assert all(isinstance(tool, TAFTool) for tool in tools)

    def test_memory_tool_has_correct_schema(self):
        """Test that memory tool has correct schema."""
        config = TAFConfig(
            twilio_account_sid="ACtest",
            twilio_auth_token="test_token",
            memora_base_url="https://memory.twilio.com/v1",
            memory_service_sid="MGtest",
            maestro_base_url="https://maestro.twilio.com/v1",
            conversation_service_sid="IStest",
            twilio_phone_number="+15551234567",
        )
        session = ConversationSession(
            profile_id="prof_123", conversation_id="conv_123", channel="sms"
        )

        tools = create_memory_tools(config, session)
        memory_tool = tools[0]

        assert memory_tool.name == "retrieve_profile_memory"
        assert "query" in memory_tool.params_json_schema["properties"]
        assert memory_tool.params_json_schema["properties"]["query"]["type"] == "string"

    @patch("taf.tools.memory.requests.post")
    def test_memory_tool_makes_api_call(self, mock_post):
        """Test that memory tool makes correct API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"memories": []}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        config = TAFConfig(
            twilio_account_sid="ACtest",
            twilio_auth_token="test_token",
            memora_base_url="https://memory.twilio.com/v1",
            memory_service_sid="MGtest",
            maestro_base_url="https://maestro.twilio.com/v1",
            conversation_service_sid="IStest",
            twilio_phone_number="+15551234567",
        )
        session = ConversationSession(
            profile_id="prof_123", conversation_id="conv_123", channel="sms"
        )

        tools = create_memory_tools(config, session)
        memory_tool = tools[0]

        result = memory_tool.implementation(query="test query")

        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "MGtest" in call_args[0][0]  # URL contains service SID
        assert "prof_123" in call_args[0][0]  # URL contains profile ID
        assert call_args[1]["json"]["query"] == "test query"
        assert result == {"memories": []}

    def test_memory_tool_uses_injected_config(self):
        """Test that memory tool uses injected config and session."""
        config1 = TAFConfig(
            twilio_account_sid="ACtest1",
            twilio_auth_token="token1",
            memora_base_url="https://memory1.twilio.com/v1",
            memory_service_sid="MGtest1",
            maestro_base_url="https://maestro.twilio.com/v1",
            conversation_service_sid="IStest1",
            twilio_phone_number="+15551234567",
        )
        session1 = ConversationSession(profile_id="prof_1", conversation_id="conv_1", channel="sms")

        config2 = TAFConfig(
            twilio_account_sid="ACtest2",
            twilio_auth_token="token2",
            memora_base_url="https://memory2.twilio.com/v1",
            memory_service_sid="MGtest2",
            maestro_base_url="https://maestro.twilio.com/v1",
            conversation_service_sid="IStest2",
            twilio_phone_number="+15551234567",
        )
        session2 = ConversationSession(profile_id="prof_2", conversation_id="conv_2", channel="sms")

        tools1 = create_memory_tools(config1, session1)
        tools2 = create_memory_tools(config2, session2)

        # Tools should have different implementations based on injected config
        assert tools1[0].name == tools2[0].name  # Same tool name
        assert tools1[0].implementation != tools2[0].implementation  # Different closures
