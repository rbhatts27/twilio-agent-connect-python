"""Tests for TAF tools."""

import json
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from taf.core.config import TAFConfig, TwilioMemoryConfig
from taf.core.context import ConversationSession
from taf.models.knowledge import Knowledge
from taf.tools.base import (
    TAFTool,
    _extract_schema_from_function,
    _is_optional,
    _type_to_json_schema,
    create_tool,
    function_tool,
)
from taf.tools.knowledge import (
    KnowledgeToolConfig,
    create_knowledge_tool,
    create_knowledge_tools,
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
            twilio_memory_config=TwilioMemoryConfig(memory_store_id="MGtest"),
            environment="prod",
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
            twilio_memory_config=TwilioMemoryConfig(memory_store_id="MGtest"),
            environment="prod",
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
            twilio_memory_config=TwilioMemoryConfig(memory_store_id="MGtest"),
            environment="prod",
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
            twilio_memory_config=TwilioMemoryConfig(memory_store_id="MGtest1"),
            environment="prod",
            conversation_service_sid="IStest1",
            twilio_phone_number="+15551234567",
        )
        session1 = ConversationSession(profile_id="prof_1", conversation_id="conv_1", channel="sms")

        config2 = TAFConfig(
            twilio_account_sid="ACtest2",
            twilio_auth_token="token2",
            twilio_memory_config=TwilioMemoryConfig(memory_store_id="MGtest2"),
            environment="prod",
            conversation_service_sid="IStest2",
            twilio_phone_number="+15551234567",
        )
        session2 = ConversationSession(profile_id="prof_2", conversation_id="conv_2", channel="sms")

        tools1 = create_memory_tools(config1, session1)
        tools2 = create_memory_tools(config2, session2)

        # Tools should have different implementations based on injected config
        assert tools1[0].name == tools2[0].name  # Same tool name
        assert tools1[0].implementation != tools2[0].implementation  # Different closures


class TestKnowledgeTools:
    """Test create_knowledge_tool function."""

    def test_create_knowledge_tool_returns_taf_tool(self):
        """Test that create_knowledge_tool returns a TAFTool."""
        config = TAFConfig(
            twilio_account_sid="ACtest",
            twilio_auth_token="test_token",
            twilio_memory_config=TwilioMemoryConfig(memory_store_id="MGtest"),
            environment="prod",
            conversation_service_sid="IStest",
            twilio_phone_number="+15551234567",
        )
        knowledge = Knowledge(
            id="KN123",
            name="Product FAQ",
            description="Frequently asked questions about products",
            type="Web",
        )

        tool = create_knowledge_tool(config, knowledge)

        assert isinstance(tool, TAFTool)

    def test_knowledge_tool_default_name_and_description(self):
        """Test that knowledge tool has correct default name and description."""
        config = TAFConfig(
            twilio_account_sid="ACtest",
            twilio_auth_token="test_token",
            twilio_memory_config=TwilioMemoryConfig(memory_store_id="MGtest"),
            environment="prod",
            conversation_service_sid="IStest",
            twilio_phone_number="+15551234567",
        )
        knowledge = Knowledge(
            id="KN123",
            name="Product FAQ",
            description="Frequently asked questions about products",
            type="Web",
        )

        tool = create_knowledge_tool(config, knowledge)

        assert tool.name == "Knowledge: Product FAQ"
        assert "Frequently asked questions about products" in tool.description
        assert "The input MUST be a question in the form of a string." in tool.description

    def test_knowledge_tool_custom_name_and_description(self):
        """Test that knowledge tool respects custom name and description."""
        config = TAFConfig(
            twilio_account_sid="ACtest",
            twilio_auth_token="test_token",
            twilio_memory_config=TwilioMemoryConfig(memory_store_id="MGtest"),
            environment="prod",
            conversation_service_sid="IStest",
            twilio_phone_number="+15551234567",
        )
        knowledge = Knowledge(
            id="KN123",
            name="Product FAQ",
            description="Frequently asked questions about products",
            type="Web",
        )
        tool_config = KnowledgeToolConfig(
            name="custom_product_search", description="Search product documentation"
        )

        tool = create_knowledge_tool(config, knowledge, tool_config)

        assert tool.name == "custom_product_search"
        assert tool.description == "Search product documentation"

    def test_knowledge_tool_custom_top_k(self):
        """Test that knowledge tool respects custom top-K value."""
        config = TAFConfig(
            twilio_account_sid="ACtest",
            twilio_auth_token="test_token",
            twilio_memory_config=TwilioMemoryConfig(memory_store_id="MGtest"),
            environment="prod",
            conversation_service_sid="IStest",
            twilio_phone_number="+15551234567",
        )
        knowledge = Knowledge(
            id="KN123",
            name="Product FAQ",
            description="Frequently asked questions about products",
            type="Web",
        )
        tool_config = KnowledgeToolConfig(top_k=10)

        tool = create_knowledge_tool(config, knowledge, tool_config)

        # We can't directly access tool_config.top_k from outside,
        # but we can verify it's used in the API call via mocking
        assert isinstance(tool, TAFTool)

    def test_knowledge_tool_has_correct_schema(self):
        """Test that knowledge tool has correct parameter schema."""
        config = TAFConfig(
            twilio_account_sid="ACtest",
            twilio_auth_token="test_token",
            twilio_memory_config=TwilioMemoryConfig(memory_store_id="MGtest"),
            environment="prod",
            conversation_service_sid="IStest",
            twilio_phone_number="+15551234567",
        )
        knowledge = Knowledge(
            id="KN123",
            name="Product FAQ",
            description="Frequently asked questions about products",
            type="Web",
        )

        tool = create_knowledge_tool(config, knowledge)

        assert "query" in tool.params_json_schema["properties"]
        assert tool.params_json_schema["properties"]["query"]["type"] == "string"
        assert "query" in tool.params_json_schema["required"]

    @patch("taf.tools.knowledge.requests.post")
    def test_knowledge_tool_makes_api_call(self, mock_post):
        """Test that knowledge tool makes correct API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "chunks": [
                {"content": "Answer 1", "score": 0.95},
                {"content": "Answer 2", "score": 0.87},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        config = TAFConfig(
            twilio_account_sid="ACtest",
            twilio_auth_token="test_token",
            twilio_memory_config=TwilioMemoryConfig(memory_store_id="MGtest"),
            environment="prod",
            conversation_service_sid="IStest",
            twilio_phone_number="+15551234567",
        )
        knowledge = Knowledge(
            id="KN123",
            name="Product FAQ",
            description="Frequently asked questions about products",
            type="Web",
        )

        tool = create_knowledge_tool(config, knowledge)
        result = tool.implementation(query="What is the return policy?")

        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://knowledge.twilio.com/v1/Knowledge/Search"
        assert call_args[1]["json"]["query"] == "What is the return policy?"
        assert call_args[1]["json"]["knowledge_ids"] == ["KN123"]
        assert call_args[1]["json"]["top"] == 5  # Default value
        assert call_args[1]["auth"] == ("ACtest", "test_token")  # HTTP Basic Auth
        assert call_args[1]["headers"]["Content-Type"] == "application/json"

        # Verify result
        assert result == [
            {"content": "Answer 1", "score": 0.95},
            {"content": "Answer 2", "score": 0.87},
        ]

    @patch("taf.tools.knowledge.requests.post")
    def test_knowledge_tool_uses_custom_top_k(self, mock_post):
        """Test that knowledge tool uses custom top-K value in API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"chunks": []}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        config = TAFConfig(
            twilio_account_sid="ACtest",
            twilio_auth_token="test_token",
            twilio_memory_config=TwilioMemoryConfig(memory_store_id="MGtest"),
            environment="prod",
            conversation_service_sid="IStest",
            twilio_phone_number="+15551234567",
        )
        knowledge = Knowledge(
            id="KN123",
            name="Product FAQ",
            description="Frequently asked questions about products",
            type="Web",
        )
        tool_config = KnowledgeToolConfig(top_k=10)

        tool = create_knowledge_tool(config, knowledge, tool_config)
        tool.implementation(query="test query")

        # Verify top-K value
        call_args = mock_post.call_args
        assert call_args[1]["json"]["top"] == 10

    def test_knowledge_tool_uses_injected_config(self):
        """Test that knowledge tools use injected config."""
        config1 = TAFConfig(
            twilio_account_sid="ACtest1",
            twilio_auth_token="token1",
            twilio_memory_config=TwilioMemoryConfig(memory_store_id="MGtest1"),
            environment="prod",
            conversation_service_sid="IStest1",
            twilio_phone_number="+15551234567",
        )
        knowledge1 = Knowledge(id="KN123", name="FAQ 1", description="First FAQ", type="Web")

        config2 = TAFConfig(
            twilio_account_sid="ACtest2",
            twilio_auth_token="token2",
            twilio_memory_config=TwilioMemoryConfig(memory_store_id="MGtest2"),
            environment="prod",
            conversation_service_sid="IStest2",
            twilio_phone_number="+15551234567",
        )
        knowledge2 = Knowledge(id="KN456", name="FAQ 2", description="Second FAQ", type="Web")

        tool1 = create_knowledge_tool(config1, knowledge1)
        tool2 = create_knowledge_tool(config2, knowledge2)

        # Tools should have different implementations based on injected config
        assert tool1.implementation != tool2.implementation  # Different closures

    def test_knowledge_types(self):
        """Test that all knowledge types are supported."""
        config = TAFConfig(
            twilio_account_sid="ACtest",
            twilio_auth_token="test_token",
            twilio_memory_config=TwilioMemoryConfig(memory_store_id="MGtest"),
            environment="prod",
            conversation_service_sid="IStest",
            twilio_phone_number="+15551234567",
        )

        for knowledge_type in ["Web", "File", "Text", "DB"]:
            knowledge = Knowledge(
                id=f"KN{knowledge_type}",
                name=f"{knowledge_type} Knowledge",
                description=f"Knowledge of type {knowledge_type}",
                type=knowledge_type,
            )
            tool = create_knowledge_tool(config, knowledge)
            assert isinstance(tool, TAFTool)

    def test_create_knowledge_tools_returns_list(self):
        """Test that create_knowledge_tools returns a list of tools."""
        config = TAFConfig(
            twilio_account_sid="ACtest",
            twilio_auth_token="test_token",
            twilio_memory_config=TwilioMemoryConfig(memory_store_id="MGtest"),
            environment="prod",
            conversation_service_sid="IStest",
            twilio_phone_number="+15551234567",
        )
        knowledge_list = [
            Knowledge(id="KN1", name="FAQ", description="FAQs", type="Web"),
            Knowledge(id="KN2", name="Docs", description="Documentation", type="Text"),
            Knowledge(id="KN3", name="Policies", description="Policies", type="File"),
        ]

        tools = create_knowledge_tools(config, knowledge_list)

        assert isinstance(tools, list)
        assert len(tools) == 3
        assert all(isinstance(tool, TAFTool) for tool in tools)

    def test_create_knowledge_tools_with_configs(self):
        """Test create_knowledge_tools with custom configurations."""
        config = TAFConfig(
            twilio_account_sid="ACtest",
            twilio_auth_token="test_token",
            twilio_memory_config=TwilioMemoryConfig(memory_store_id="MGtest"),
            environment="prod",
            conversation_service_sid="IStest",
            twilio_phone_number="+15551234567",
        )
        knowledge_list = [
            Knowledge(id="KN1", name="FAQ", description="FAQs", type="Web"),
            Knowledge(id="KN2", name="Docs", description="Documentation", type="Text"),
        ]
        tool_configs = {
            "KN1": KnowledgeToolConfig(name="search_faq", top_k=3),
            "KN2": KnowledgeToolConfig(description="Custom docs description"),
        }

        tools = create_knowledge_tools(config, knowledge_list, tool_configs)

        assert len(tools) == 2
        assert tools[0].name == "search_faq"
        assert tools[1].description == "Custom docs description"

    def test_create_knowledge_tools_empty_list(self):
        """Test create_knowledge_tools with empty list."""
        config = TAFConfig(
            twilio_account_sid="ACtest",
            twilio_auth_token="test_token",
            twilio_memory_config=TwilioMemoryConfig(memory_store_id="MGtest"),
            environment="prod",
            conversation_service_sid="IStest",
            twilio_phone_number="+15551234567",
        )

        tools = create_knowledge_tools(config, [])

        assert isinstance(tools, list)
        assert len(tools) == 0

    def test_create_knowledge_tools_partial_configs(self):
        """Test create_knowledge_tools with partial tool_configs."""
        config = TAFConfig(
            twilio_account_sid="ACtest",
            twilio_auth_token="test_token",
            twilio_memory_config=TwilioMemoryConfig(memory_store_id="MGtest"),
            environment="prod",
            conversation_service_sid="IStest",
            twilio_phone_number="+15551234567",
        )
        knowledge_list = [
            Knowledge(id="KN1", name="FAQ", description="FAQs", type="Web"),
            Knowledge(id="KN2", name="Docs", description="Documentation", type="Text"),
            Knowledge(id="KN3", name="Policies", description="Policies", type="File"),
        ]
        # Only configure the first knowledge
        tool_configs = {"KN1": KnowledgeToolConfig(name="custom_faq")}

        tools = create_knowledge_tools(config, knowledge_list, tool_configs)

        assert len(tools) == 3
        assert tools[0].name == "custom_faq"  # Custom config
        assert tools[1].name == "Knowledge: Docs"  # Default
        assert tools[2].name == "Knowledge: Policies"  # Default

    @patch("taf.tools.knowledge.requests.post")
    @patch.dict("os.environ", {"KNOWLEDGE_BASE_URL": "http://localhost:8080"})
    def test_knowledge_tool_respects_env_variable(self, mock_post):
        """Test that knowledge tool respects KNOWLEDGE_BASE_URL environment variable."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"chunks": []}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        config = TAFConfig(
            twilio_account_sid="ACtest",
            twilio_auth_token="test_token",
            twilio_memory_config=TwilioMemoryConfig(memory_store_id="MGtest"),
            environment="prod",
            conversation_service_sid="IStest",
            twilio_phone_number="+15551234567",
        )
        knowledge = Knowledge(
            id="KN123",
            name="Product FAQ",
            description="Frequently asked questions about products",
            type="Web",
        )

        tool = create_knowledge_tool(config, knowledge)
        tool.implementation(query="test query")

        # Verify that custom base URL from environment variable is used
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:8080/v1/Knowledge/Search"
