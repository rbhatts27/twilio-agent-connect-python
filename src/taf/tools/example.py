"""
Example tool implementation showing how TAF tools work.

This module demonstrates how the @function_tool decorator automatically extracts
function metadata to create LLM-compatible tool schemas.

## How @function_tool Works

The decorator analyzes your function to create a tool schema:

1. **Name**: Uses function name (or override with name= parameter)
2. **Description**: Uses docstring first line (or override with description= parameter)
3. **Parameters**: Extracts from function signature and type hints:
   - Parameter names become JSON schema property names
   - Type hints map to JSON schema types:
     * str -> "string"
     * int -> "integer"
     * float -> "number"
     * bool -> "boolean"
     * List[T] -> "array" with items of type T
     * Optional[T] -> same as T but not required
   - Default values make parameters optional
   - No default = required parameter

## Example Mapping

```python
@function_tool()
def send_message(to: str, message: str, priority: int = 1) -> dict:
    \"\"\"Send a message to a recipient.\"\"\"
    pass
```

Becomes this JSON schema:
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

## Usage Examples

### Simple Tool Creation
```python
from taf.tools import function_tool

@function_tool()
def calculate_tip(bill_amount: float, tip_percentage: float = 15.0) -> dict:
    \"\"\"Calculate tip amount and total bill.\"\"\"
    tip_amount = bill_amount * (tip_percentage / 100)
    return {"tip": tip_amount, "total": bill_amount + tip_amount}

# Generate schemas for LLM
openai_schema = calculate_tip.to_openai_format()
anthropic_schema = calculate_tip.to_anthropic_format()
```

### Tools with Configuration Injection
```python
from taf.tools.memory import create_memory_tools
from taf.core.config import TAFConfig
from taf.core.context import SessionIdentity

# Configuration and session context (not exposed to LLM)
config = TAFConfig(
    memora_base_url="https://memora.twilio.com/v1",
    memora_auth_token="your_token",
    memory_service_sid="mem_service_123...",
    # ... other config
)
session = SessionIdentity(
    profile_id="profile_456...",
    conversation_id="conversation_789..."
)

# Create tools with injected config
memory_tools = create_memory_tools(config, session)

# LLM only sees the query parameter
tool_schemas = [tool.to_openai_format() for tool in memory_tools]
# Result: [{"type": "function", "function": {"name": "retrieve_profile_memory", "parameters": {"query": {...}}}}]

# Execute tool (config/auth handled automatically)
result = memory_tools[0].implementation(query="user preferences about food")
```
"""

from typing import List, Optional

from taf.tools.base import function_tool


@function_tool()
def example_tool(
    required_text: str,
    optional_number: Optional[int] = None,
    default_boolean: bool = True,
    items_list: Optional[List[str]] = None,
) -> dict:
    """
    Example function showing parameter mapping.

    This demonstrates how different Python types and default values
    map to JSON schema properties and required fields.

    Args:
        required_text: This becomes a required string parameter
        optional_number: This becomes an optional integer parameter
        default_boolean: This becomes optional boolean (default: True)
        items_list: This becomes optional array of strings

    Returns:
        Dictionary with processed parameters
    """
    # Replace this stub with your actual implementation
    return {
        "processed": True,
        "required_text": required_text,
        "optional_number": optional_number,
        "default_boolean": default_boolean,
        "items_list": items_list or [],
    }
