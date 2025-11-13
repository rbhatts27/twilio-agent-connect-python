# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Twilio Agentic Framework (TAF) is a Python SDK that integrates third-party LLM agentic applications with Twilio communication APIs. TAF provides middleware for identity resolution, memory/context management (via Memora), conversation orchestration (via Maestro), and channel handling (Voice, SMS).

**Key Architecture Principle**: TAF is not an agent runtime itself—it's middleware that enables existing LLM applications (OpenAI Agents SDK, Bedrock, LangChain, etc.) to leverage Twilio Sierra primitives (Memora for memory, Maestro for conversations, ConversationRelay for voice).

## Development Commands

### Environment Setup
```bash
# Install dependencies (uses uv package manager)
make sync

# Complete dev environment setup with pre-commit hooks
make dev-setup
```

### Code Quality
```bash
# Format code with ruff (includes linting fixes)
make format

# Run type checking with mypy (required: mypy >=1.0.0, strict mode)
make type-check

# Run linting checks only (no auto-fix)
make lint

# Run all checks (lint + type-check + test)
make check

# Run pre-commit hooks
make pre-commit
```

### Testing
```bash
# Run all tests with pytest
make test

# Run single test file
uv run pytest tests/test_taf.py

# Run specific test
uv run pytest tests/test_taf.py::test_function_name
```

### Examples
```bash
# Run webhook server for testing Twilio webhooks (defaults to port 8000)
make server

# Custom port
python examples/channels/sms.py --port 3000

# Start ngrok tunnel for local testing
make ngrok
```

## Core Architecture

### Package Structure

The codebase follows a modular design matching the architecture diagram in TAF.md:

- **`src/taf/core/`** - Core TAF class, configuration, and context models
  - `taf.py` - Main `TAF` class with `retrieve_memory()` and `on_message_ready()` hook
  - `config.py` - `TAFConfig` Pydantic model for SDK configuration
  - `context.py` - `SessionIdentity`, `Profile`, `Memory`, `ConversationSession` models (Note: `ConversationSession` does not store message history)

- **`src/taf/context/`** - Integration with Twilio Sierra primitives
  - `memory.py` - `MemoryClient` for memory retrieval (traits, observations, sessions)
  - `conversation.py` - `ConversationClient` for conversation/participant management

- **`src/taf/models/`** - Data models
  - `memory.py` - Memory API models: `MemoryRetrievalRequest`, `MemoryRetrievalResponse`, `ObservationInfo`, `SummaryInfo`, `SessionInfo`, `SessionMessage`
  - `conversation.py` - Conversation API models: `ConversationRequest`, `ConversationResponse`, `ParticipantRequest`, `ParticipantResponse`, `ParticipantAddress`
  - `voice.py` - Voice WebSocket message models: `SetupMessage`, `PromptMessage`, `InterruptMessage`, `CustomParameters`, `VoiceServerConfig`
  - `webhook.py` - `TwilioWebhookEvent` model for parsing Twilio webhook events
  - `knowledge.py` - `Knowledge` model for knowledge tool integration
  - `conversation_event.py` - `ConversationEvent` model with comprehensive event fields

- **`src/taf/channels/`** - Channel-specific orchestration and conversation lifecycle management
  - `base.py` - `BaseChannel` abstract class with conversation session management (`_start_conversation`, `_end_conversation`); `send_response()` with optional `role` parameter
  - `sms.py` - `SMSChannel` implementation handling webhook events, message validation, and memory retrieval
  - `voice.py` - `VoiceChannel` for Voice/ConversationRelay WebSocket protocol handling; supports both simplified server (via `VoiceServerConfig`) and manual FastAPI approaches

- **`src/taf/tools/`** - LLM tool integration for Sierra primitives
  - `base.py` - `TAFTool` dataclass with `to_openai_format()` and `to_anthropic_format()` methods; `function_tool` decorator for creating tools from functions
  - `messaging.py` - `create_messaging_tools(config)` factory returning `send_message` tool
  - `memory.py` - `create_memory_tools(config, session)` factory returning `retrieve_profile_memory` tool
  - `example.py` - Example tool implementations

- **`src/taf/adapters/`** - Runtime-specific adapters (future: OpenAI, Bedrock, etc.)

### Critical Workflow

**Channel-Based Architecture** (Recommended):

1. **Channel processes webhook**: Twilio sends webhook → `channel.process_webhook(webhook_data)` → channel parses event via `TwilioWebhookEvent` → validates message content

2. **Conversation Management**: Channel handles conversation lifecycle:
   - `onConversationAdded`: Channel extracts `profile_id` from webhook → calls `_start_conversation(conv_id, profile_id)` → stores conversation session
   - `onMessageAdded`: Channel validates message → auto-initializes conversation if needed → creates `ConversationSession` with all fields → calls `taf.retrieve_memory(conversation_context, query)`
   - `onConversationRemoved`: Channel calls `_end_conversation(conv_id)` → cleans up session

3. **Message Processing**: `TAF.retrieve_memory(conversation_context, query)` → retrieves memories from Memora using `conversation_context.conversation_id` and `config.twilio_memory_config.memory_store_id` (if memory is enabled) → triggers `on_message_ready()` callback with optional memory response → returns `MemoryRetrievalResponse`

4. **Message Ready Hook**: Developers register callbacks via `taf.on_message_ready(callback)` to handle incoming messages
   - For SMS: Receives `user_message`, `context` (ConversationSession), and `memory_response` (MemoryRetrievalResponse)
   - For Voice: Receives `user_message`, `context`, and `memory_response` (may be None)

### API Clients

**MemoryClient** (`src/taf/context/memory.py`):
- Endpoint: `POST /Services/{service_id}/Conversations/{conversation_id}/Recall`
- Returns: `MemoryRetrievalResponse` with `observations`, `summaries`, `sessions` fields
- Auth: Uses HTTP Basic Authentication (Account SID as username, Auth Token as password)
- Models (from `src/taf/models/memory.py`):
  - `MemoryRetrievalRequest`: Request with `conversation_id`, `query`, optional date filters
  - `MemoryRetrievalResponse`: Response with observations, summaries, sessions arrays
  - `ObservationInfo`: Individual observation memories
  - `SummaryInfo`: Summarized insights from conversations
  - `SessionInfo`: Historical conversation sessions with messages
  - `SessionMessage`: Individual messages within sessions (includes `timestamp`, `direction`, `channel`, `from_address`, `to_address`, `content`)

**ConversationClient** (`src/taf/context/conversation.py`):
- `create_conversation(name, layers, intelligence_agents)`: Creates new conversation, returns `ConversationResponse`
  - Endpoint: `POST /Services/{service_id}/Conversations`
- `add_participant(conversation_id, addresses)`: Adds participant, returns `ParticipantResponse`
  - Endpoint: `POST /Services/{service_id}/Conversations/{conversation_id}/Participants`
- Auth: Uses HTTP Basic Authentication (Account SID as username, Auth Token as password)
- Models (from `src/taf/models/conversation.py`): `ConversationRequest`, `ConversationResponse`, `ParticipantRequest`, `ParticipantResponse`, `ParticipantAddress`

## Type Checking and Code Style

This project uses **strict mypy configuration** (see pyproject.toml):
- All functions must have type hints (`disallow_untyped_defs = true`)
- No incomplete definitions allowed (`disallow_incomplete_defs = true`)
- Use `typing` module types (`Optional`, `List`, `Dict`, `Any`, `Union`, `Literal`)
- Python 3.9+ compatibility required (use `List` not `list` for type hints)

**Pydantic Usage**:
- All models use Pydantic v2 (`>=2.0.0,<3`)
- Use `Field()` with `alias` for API field name mapping (e.g., `trait_group` → `traitGroup`)
- Set `model_config = {"populate_by_name": True}` to accept both Python and API field names
- Use `.model_dump(by_alias=True, exclude_none=True)` for API request payloads

**Code Formatting**:
- Line length: 100 characters
- Use ruff for formatting and linting (black-compatible)
- Known first party: `["taf"]`
- Import combining: `combine-as-imports = true`
- Enabled lint rules: pycodestyle (E/W), pyflakes (F), isort (I), flake8-bugbear (B), flake8-comprehensions (C4), pyupgrade (UP)
- Per-file ignores: Examples allow E402 (import order) and E501 (line length)

## Testing

Tests are located in `tests/` directory:
- `test_taf.py` - Core TAF class tests
- `test_config.py` - Configuration tests
- `test_integration.py` - Integration tests
- `test_sms_channel.py` - SMS channel tests
- `test_voice_channel.py` - Voice channel tests
- `test_voice_models.py` - Voice WebSocket message model tests
- `test_conversation.py` - Conversation client tests
- `test_webhook.py` - Webhook event parsing tests
- `test_tools.py` - Tools module tests (function_tool decorator, TAFTool format conversions)
- `test_init.py` - Package initialization tests

Test requirements (pytest.ini_options in pyproject.toml):
- Test files: `test_*.py` or `*_test.py`
- Test classes: `Test*`
- Test functions: `test_*`

## Configuration Requirements

When initializing TAF, developers must provide:
- `environment` - TAF environment ("dev", "stage", or "prod") - automatically sets Memora and Maestro base URLs
- `twilio_account_sid` - From Twilio Console
- `twilio_auth_token` - From Twilio Console
- `twilio_phone_number` - Twilio Phone Number to use for sending messages (required for messaging tools)
- `conversation_service_sid` - Twilio Conversation Service SID (starts with `IS`)
- `twilio_memory_config` - Optional TwilioMemoryConfig object with `memory_store_id` field (starts with `MG`). Only needed if using Twilio Memory functionality. When provided, memory is automatically retrieved for SMS conversations.
- `log_level` - Optional, defaults to "INFO"

## Common Patterns

### SMS Channel Usage

```python
from taf import TAF, TAFConfig
from taf.channels import SMSChannel
from taf.core.config import TwilioMemoryConfig

# 1. Setup TAF and SMS Channel
config = TAFConfig(
    environment="prod",  # or "dev" or "stage"
    twilio_account_sid="AC...",
    twilio_auth_token="...",
    twilio_phone_number="+1234567890",
    conversation_service_sid="IS...",
    twilio_memory_config=TwilioMemoryConfig(
        memory_store_id="MG..."
    )  # Optional - only if using Twilio Memory
)
taf = TAF(config)
sms_channel = SMSChannel(taf)

# 2. Register callback to handle message processing
def handle_message(user_message, context, memory_response=None):
    llm_response = call_your_llm(user_message, memory_response)
    sms_channel.send_response(context.conversation_id, llm_response)

taf.on_message_ready(handle_message)

# 3. In your webhook handler
@app.route('/webhook', methods=['POST'])
def webhook():
    sms_channel.process_webhook(request.json)
    return {"status": "ok"}
```

### SMS Channel Conversation Lifecycle

The SMS channel handles three webhook events:

1. **`onConversationAdded`**: Initializes conversation session
   - Extracts `profile_id` from webhook data (supports both `profile_id` and `ProfileId`)
   - Calls `_start_conversation(conv_id, profile_id)` to store conversation session

2. **`onMessageAdded`**: Processes incoming message
   - Validates message body (ignores empty/whitespace messages)
   - Auto-initializes conversation if not already started (extracts `profile_id` from webhook)
   - Creates `ConversationSession` with `conversation_id`, `profile_id`, `channel`, and `started_at`
   - Calls `taf.retrieve_memory(conversation_context, query=message_body)`
   - This triggers `on_message_ready` callback with `user_message`, `context`, and optional `memory_response`

3. **`onConversationRemoved`**: Cleans up conversation state
   - Calls `_end_conversation(conv_id)` to remove conversation from internal tracking

**Important**: Profile ID must be included in webhook data as `profile_id` or `ProfileId` field.

### Voice Channel Usage

The Voice channel provides WebSocket protocol handling for Twilio ConversationRelay. TAF offers two approaches:

**Simplified Approach (Recommended for Getting Started):**

Use `VoiceServerConfig` for automatic server setup with minimal boilerplate:

```python
from taf import TAF, TAFConfig, VoiceServerConfig
from taf.channels.voice import VoiceChannel
from taf.core.config import TwilioMemoryConfig

# 1. Setup TAF and Voice Channel with server config
config = TAFConfig(
    environment="prod",  # or "dev" or "stage"
    twilio_account_sid="AC...",
    twilio_auth_token="...",
    twilio_phone_number="+1234567890",
    conversation_service_sid="IS...",
    twilio_memory_config=TwilioMemoryConfig(
        memory_store_id="MG..."
    )  # Optional - only if using Twilio Memory
)
taf = TAF(config)

# 2. Register callback to handle memory-ready events
async def handle_memory(context, memory_response, user_message):
    llm_response = await call_your_llm(user_message, memory_response)
    await voice_channel.send_response(context.conversation_id, llm_response)

taf.on_memory_ready(handle_memory)

# 3. Initialize channel with server configuration
voice_channel = VoiceChannel(
    taf=taf,
    server_config=VoiceServerConfig(
        public_domain="example.ngrok.io",  # Required
        host="0.0.0.0",  # Optional (default: "0.0.0.0")
        port=8000,  # Optional (default: 8000)
        welcome_greeting="Hello! How can I assist you today?",  # Optional
    ),
)

# 4. Start server (automatically creates FastAPI app with /twiml and /ws endpoints)
voice_channel.start()
```

See `examples/servers/voice.py` for a complete implementation.

**Manual Approach (For Advanced Use Cases):**

Create your own FastAPI application for full control over server configuration:

```python
from fastapi import FastAPI, WebSocket
from fastapi.responses import Response
from taf import TAF, TAFConfig
from taf.channels.voice import VoiceChannel
from taf.core.config import TwilioMemoryConfig

# 1. Setup TAF and Voice Channel
config = TAFConfig(
    environment="prod",  # or "dev" or "stage"
    twilio_account_sid="AC...",
    twilio_auth_token="...",
    twilio_phone_number="+1234567890",
    conversation_service_sid="IS...",
    twilio_memory_config=TwilioMemoryConfig(
        memory_store_id="MG..."
    )  # Optional - only if using Twilio Memory
)
taf = TAF(config)
voice_channel = VoiceChannel(taf)

# 2. Register callback to handle message processing
async def handle_message(user_message, context, memory_response=None):
    llm_response = await call_your_llm(user_message, memory_response)
    await voice_channel.send_response(context.conversation_id, llm_response)

taf.on_message_ready(handle_message)

# 3. Create FastAPI app with TwiML and WebSocket endpoints
app = FastAPI()

@app.get("/twiml")
async def get_twiml():
    conversation = taf.maestro_client.create_conversation()
    twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <ConversationRelay url="wss://your-domain.ngrok.io/ws">
            <Parameter name="conversationId" value="{conversation.id}" />
        </ConversationRelay>
    </Connect>
</Response>'''
    return Response(content=twiml, media_type="application/xml")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await voice_channel.handle_websocket(websocket)
```

See `examples/channels/voice.py` for a complete implementation.

### Voice Channel Architecture

TAF provides two architectural patterns:

**Simplified Pattern (VoiceServerConfig):**
- **Built-in Server**: Automatic FastAPI app creation and endpoint setup
- **Convention over Configuration**: Opinionated defaults for quick starts
- **Use Case**: Getting started quickly, prototyping, simple voice applications

**Manual Pattern (Custom FastAPI):**
- **Protocol Layer** (`VoiceChannel`): Handles WebSocket lifecycle, processes ConversationRelay messages, manages conversation state
- **Application Layer** (User's FastAPI app): Provides TwiML endpoint and WebSocket endpoint
- **Benefits**: Separation of concerns, no forced dependencies, full control over server configuration
- **Use Case**: Custom middleware, authentication, integration with existing apps

## Dependencies

**Core Dependencies**:
- `pydantic>=2.0.0,<3` - Data validation
- `requests>=2.31.0,<3` - HTTP client
- `python-dotenv>=1.0.0,<2` - Environment variable loading
- `twilio>=9.8.3,<10` - Twilio Python SDK for messaging and other APIs

**Optional Dependencies**:
- `voice` - Voice channel support: `fastapi>=0.115.0,<1`, `uvicorn>=0.32.0,<1` (WebSocket support built-in to FastAPI)
- `dev` - Development tools: `pytest>=7.0.0,<8`, `pytest-cov>=5.0.0,<6`, `ruff>=0.8.0,<1`, `mypy>=1.0.0,<2`, `types-requests>=2.31.0,<3`, `openai>=1.0.0,<2`, `openai-agents>=0.1.0`, `fastapi`, `uvicorn`

**Note**: FastAPI and uvicorn are only required if using the Voice channel (either simplified or manual approach). The core TAF package does not depend on them.

## Tools Integration

The tools module provides LLM-compatible tool definitions for integrating Twilio Sierra primitives with LLM runtimes:

### TAFTool Class (`tools/base.py`)

The `TAFTool` dataclass represents a tool/function for LLM integration:
- `name` - Function name
- `description` - What the tool does
- `params_json_schema` - JSON Schema for parameters (auto-generated from type hints)
- `implementation` - The actual function to execute

**Format Conversions**:
- `to_openai_format()` - Returns `{"type": "function", "function": {...}}` for OpenAI API
- `to_anthropic_format()` - Returns `{"name": "...", "description": "...", "input_schema": {...}}` for Anthropic API
- `to_json()` - JSON string representation (OpenAI format by default)

### Creating Tools

**Using `@function_tool()` decorator** (recommended):
```python
from taf.tools import function_tool

@function_tool()
def send_message(phone_number: str, message: str) -> bool:
    """
    Sends a message to a user.

    Args:
        phone_number: The phone number to send to
        message: The message content

    Returns:
        True on success, False on failure
    """
    # Implementation here
    return True
```

The decorator automatically:
- Extracts function name and docstring
- Generates JSON Schema from type hints (supports `str`, `int`, `bool`, `float`, `Optional`, `Literal`, `list`, `dict`, etc.)
- Tracks required vs optional parameters
- Creates TAFTool instance

**Using `create_tool()` function**:
```python
from taf.tools import create_tool

tool = create_tool(
    name="send_message",
    description="Sends a message to a user",
    params_json_schema={
        "type": "object",
        "properties": {
            "phone_number": {"type": "string"},
            "message": {"type": "string"}
        },
        "required": ["phone_number", "message"]
    },
    implementation=my_function
)
```

### Built-in Tool Factories

**Messaging Tools** (`tools/messaging.py`):
```python
from taf.tools.messaging import create_messaging_tools

tools = create_messaging_tools(config)  # Returns [send_message]
```

**Memory Tools** (`tools/memory.py`):
```python
from taf.tools.memory import create_memory_tools

tools = create_memory_tools(config, session)  # Returns [retrieve_profile_memory]
```

Both factories return lists of `TAFTool` objects configured with your TAF settings.

## Future Enhancements

Based on TAF.md architecture, these modules are planned but not yet implemented:
- **Adapters**: Runtime-specific adapters for OpenAI, Bedrock, Azure AI, LangChain (with `toOpenAiMessages()`, `toBedrockMessages()` formatting)
- **Additional Tools**: `twilio.escalate-to-human`, `twilio.session-memory.fetch`
- **Server**: Standalone server package for "batteries included" setup (separate from core to avoid forcing FastAPI dependency)
- **Analytics**: Integration with Twilio workbench observability

When implementing these features, refer to the detailed architecture diagrams and sequence flows in TAF.md.