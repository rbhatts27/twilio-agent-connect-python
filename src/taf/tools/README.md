# TAF Tools

A generic tool framework for LLM function calling that works with both OpenAI and Anthropic APIs.

## How it Works

The `@function_tool` decorator automatically extracts function metadata to create LLM-compatible tool schemas:

1. **Name**: Uses function name (or override with `name=` parameter)
2. **Description**: Uses docstring first line (or override with `description=` parameter)
3. **Parameters**: Extracts from function signature and type hints:
   - Parameter names become JSON schema property names
   - Type hints map to JSON schema types:
     * `str` → `"string"`
     * `int` → `"integer"`
     * `float` → `"number"`
     * `bool` → `"boolean"`
     * `List[T]` → `"array"` with items of type T
     * `Optional[T]` → same as T but not required
   - Default values make parameters optional
   - No default = required parameter

## Basic Usage

### Simple Tools

```python
from taf.tools import function_tool

@function_tool()
def calculate_tip(bill_amount: float, tip_percentage: float = 15.0) -> dict:
    """Calculate tip amount and total bill."""
    tip_amount = bill_amount * (tip_percentage / 100)
    return {"tip": tip_amount, "total": bill_amount + tip_amount}

# Generate schemas for different LLM providers
openai_schema = calculate_tip.to_openai_format()
anthropic_schema = calculate_tip.to_anthropic_format()
```

### Tools with Configuration Injection

For tools that need access to TAF configuration (API keys, service IDs, etc.) without exposing them to the LLM:

```python
from taf.tools.memory import create_memory_tools
from taf.core.config import TAFConfig, TwilioMemoryConfig
from taf.core.context import ConversationSession

# Configuration and session context (not exposed to LLM)
config = TAFConfig(
    environment="prod",
    twilio_account_sid="AC...",
    twilio_auth_token="your_token",
    twilio_memory_config=TwilioMemoryConfig(memory_store_id="MG..."),
    conversation_service_sid="IS...",
    twilio_phone_number="+1234567890"
)
session = ConversationSession(
    profile_id="profile_456...",
    conversation_id="conversation_789...",
    channel="sms"
)

# Create tools with injected config
memory_tools = create_memory_tools(config, session)

# LLM only sees the query parameter
tool_schemas = [tool.to_openai_format() for tool in memory_tools]

# Execute tool (config/auth handled automatically)
result = memory_tools[0].implementation(query="user preferences about food")
```

## Integration Examples

### OpenAI Chat Completions API

See: [`examples/openai_chat.py`](../../../examples/openai_chat_with_tools.py)

### OpenAI Agents SDK

See: [`examples/openai_agents.py`](../../../examples/openai_agents_with_tools.py)

## Creating Custom Tools

### Method 1: Decorator (Recommended)

```python
@function_tool()
def search_contacts(query: str, limit: int = 10) -> List[dict]:
    """Search contacts by name or phone number."""
    # Your implementation here
    return [{"name": "John", "phone": "+1234567890"}]
```

### Method 2: Manual Creation

```python
from taf.tools import create_tool

def my_function(param1: str, param2: int = 5) -> str:
    return f"Got {param1} and {param2}"

tool = create_tool(
    name="my_tool",
    description="Does something useful",
    params_json_schema={
        "type": "object",
        "properties": {
            "param1": {"type": "string"},
            "param2": {"type": "integer"}
        },
        "required": ["param1"]
    },
    implementation=my_function
)
```

## JSON Schema Output

A function like this:

```python
@function_tool()
def send_message(to: str, message: str, priority: int = 1) -> dict:
    """Send a message to a recipient."""
    pass
```

Becomes this OpenAI schema:

```json
{
  "type": "function",
  "function": {
    "name": "send_message",
    "description": "Send a message to a recipient.",
    "parameters": {
      "type": "object",
      "properties": {
        "to": {"type": "string"},
        "message": {"type": "string"},
        "priority": {"type": "integer"}
      },
      "required": ["to", "message"]
    }
  }
}
```

And this Anthropic schema:

```json
{
  "name": "send_message",
  "description": "Send a message to a recipient.",
  "input_schema": {
    "type": "object",
    "properties": {
      "to": {"type": "string"},
      "message": {"type": "string"},
      "priority": {"type": "integer"}
    },
    "required": ["to", "message"]
  }
}
```
