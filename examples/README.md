# TAF Examples

This directory contains examples for the Twilio Agentic Framework (TAF).

## Quick Start

Copy `.env.example` to `.env` and fill in your Twilio and OpenAI credentials.

## Available Examples

### `openai_chat_with_tools.py` - OpenAI Chat Completions with TAF Tools
Demonstrates integrating TAF memory tools with OpenAI's Chat Completions API.

**Features:**
- ✅ TAF memory tools in OpenAI function calling format
- ✅ Automatic tool execution and result handling
- ✅ Memory retrieval using `twilio.memory.search` tool
- ✅ Async/await pattern for OpenAI API

**Usage:**
```bash
# Install OpenAI SDK
uv pip install openai-agents

# Run example
uv run python examples/openai_chat_with_tools.py
```

**Key Code Pattern:**
```python
from taf.tools.memory import create_memory_tools

# Create TAF tools with config and session context
memory_tools = create_memory_tools(config, session)

# Convert to OpenAI format
openai_tools = [tool.to_openai_format() for tool in memory_tools]

# Use in chat completions
response = await client.chat.completions.create(
    model="gpt-4",
    messages=messages,
    tools=openai_tools,
    tool_choice="auto"
)
```

### `openai_agents_with_tools.py` - OpenAI Agents SDK with TAF Tools
Shows how to use TAF tools with the OpenAI Agents SDK for autonomous agent workflows.

**Features:**
- ✅ TAF tools integrated as OpenAI Agent FunctionTools
- ✅ Agent automatically invokes tools as needed
- ✅ Memory search capabilities in agent context
- ✅ Converter function for TAF → OpenAI Agents format

**Usage:**
```bash
# Install OpenAI Agents SDK
uv pip install openai-agents

# Run example
uv run python examples/openai_agents_with_tools.py
```

**Key Code Pattern:**
```python
from agents import Agent, FunctionTool, Runner
from taf.tools.memory import create_memory_tools

# Create TAF tools
memory_tools = create_memory_tools(config, session)

# Convert to OpenAI Agents format
openai_agent_tools = [taf_tool_to_openai_agents(tool) for tool in memory_tools]

# Create agent with tools
agent = Agent(
    name="memory_agent",
    model="gpt-4",
    tools=openai_agent_tools,
    instructions="You are a helpful assistant..."
)

# Run agent
response = await Runner.run(agent, "What are my preferences?")
```

### `webhook_server.py` - Real Webhook Testing Server
HTTP server to receive and test actual Twilio webhooks with TAF processing.

**Features:**
- ✅ Receives POST requests with webhook data
- ✅ Parses JSON payloads using ConversationEvent model
- ✅ Processes with TAF and triggers memory callbacks
- ✅ SMS channel integration with conversation lifecycle

**Usage:**
```bash
# Start server on localhost:8000
python examples/webhook_server.py

# Test with curl - onMessageAdded event
curl --location 'http://localhost:8000' \
--header 'Content-Type: application/json' \
--data '{
    "eventType": "onMessageAdded",  
    "conversationId": "CHd151e6bcbe3643979a3f41f6d0da3b24", 
    "participantProfileId": "mem_profile_00000000000000000000000000",
    "communicationChannel": "sms",
    "communicationMessageBody": "wifi router issues"
}'
```


Happy building! 🚀