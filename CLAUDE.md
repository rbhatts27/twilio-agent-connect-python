# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Twilio Agent Connect (TAC) is a Python SDK that integrates third-party LLM agentic applications with Twilio communication APIs. TAC provides middleware for identity resolution, memory/context management (via Memora), conversation orchestration (via Maestro), and channel handling (Voice, SMS).

**Key Architecture Principle**: TAC is not an agent runtime itself—it's middleware that enables existing LLM applications (OpenAI Agents SDK, Bedrock, LangChain, etc.) to leverage Twilio Sierra primitives (Memora for memory, Maestro for conversations, ConversationRelay for voice).

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
uv run pytest tests/test_tac.py

# Run specific test
uv run pytest tests/test_tac.py::test_function_name
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

The codebase follows a modular design matching the architecture diagram in TAC.md:

- **`src/tac/core/`** - Core TAC class, configuration, and context models
  - `tac.py` - Main `TAC` class with `retrieve_memory()` (with automatic profile lookup), `fetch_profile()`, and `on_message_ready()` hook
  - `config.py` - `TACConfig` Pydantic model for SDK configuration; `TwilioMemoryConfig` with optional `trait_groups`

- **`src/tac/context/`** - Integration with Twilio Sierra primitives
  - `memory.py` - `MemoryClient` for memory retrieval (traits, observations, sessions), profile retrieval with `get_profile()`, and profile lookup with `lookup_profile()`
  - `conversation.py` - `ConversationClient` for conversation/participant management

- **`src/tac/models/`** - Data models
  - `memory.py` - Memory API models: `MemoryRetrievalRequest`, `MemoryRetrievalResponse`, `ObservationInfo`, `SummaryInfo`, `SessionInfo`, `SessionMessage`, `ProfileResponse`, `ProfileLookupRequest`, `ProfileLookupResponse`
  - `conversation.py` - Conversation API models: `ConversationRequest`, `ConversationResponse`, `ParticipantRequest`, `ParticipantResponse`, `ParticipantAddress`
  - `session.py` - Session models: `ConversationSession` (with optional `profile` and `author_info` fields), `AuthorInfo`
  - `voice.py` - Voice WebSocket message models: `SetupMessage`, `PromptMessage`, `InterruptMessage`, `CustomParameters`, `VoiceServerConfig`, `ConversationRelayCallbackPayload`
  - `conversation_event.py` - `ConversationEvent` model for parsing Twilio webhook events with comprehensive event fields
  - `knowledge.py` - `Knowledge` model for knowledge tool integration
  - `intelligence.py` - Conversation Intelligence models: `OperatorResultEvent`, `IntelligenceConfiguration`, `Operator`, `Participant`, `ExecutionDetails`, `TriggerDetails`, `CommunicationsRange`

- **`src/tac/intelligence/`** - Conversation Intelligence webhook processing
  - `operator_result_processor.py` - `OperatorResultProcessor` class for processing CI webhook events; creates observations/summaries in Memora based on operator results

- **`src/tac/channels/`** - Channel-specific orchestration and conversation lifecycle management
  - `base.py` - `BaseChannel` abstract class with conversation session management (`_start_conversation`, `_end_conversation`); `send_response()` with optional `role` parameter
  - `sms.py` - `SMSChannel` implementation handling webhook events, message validation, and memory retrieval
  - `voice.py` - `VoiceChannel` for Voice/ConversationRelay WebSocket protocol handling; supports both simplified server (via `VoiceServerConfig`) and manual FastAPI approaches

- **`src/tac/tools/`** - LLM tool integration for Sierra primitives
  - `base.py` - `TACTool` dataclass with `to_openai_format()` and `to_anthropic_format()` methods; `function_tool` decorator for creating tools from functions
  - `messaging.py` - `create_messaging_tools(config)` factory returning `send_message` tool
  - `memory.py` - `create_memory_tools(config, session)` factory returning `retrieve_profile_memory` tool
  - `example.py` - Example tool implementations

- **`src/tac/adapters/`** - Runtime-specific adapters (future: OpenAI, Bedrock, etc.)

### Critical Workflow

**Channel-Based Architecture** (Recommended):

1. **Channel processes webhook**: Twilio sends webhook → `channel.process_webhook(webhook_data)` → channel parses event via `ConversationEvent` → validates message content

2. **Conversation Management**: Channel handles conversation lifecycle:
   - `onConversationAdded`: Channel extracts `profile_id` from webhook → calls `_start_conversation(conv_id, profile_id)` → stores conversation session
   - `onMessageAdded`: Channel validates message → auto-initializes conversation if needed → creates `ConversationSession` with all fields → calls `tac.retrieve_memory(conversation_context, query)`
   - `onConversationRemoved`: Channel calls `_end_conversation(conv_id)` → cleans up session

3. **Message Processing**: `TAC.retrieve_memory(conversation_context, query)` → retrieves memories using one of two paths:
   - **If Memora is configured** (`twilio_memory_config` provided):
     - If `profile_id` is available: Uses it directly to retrieve memory
     - If `profile_id` is missing: Automatically calls `lookup_profile(id_type="phone", value=author_info.address)` to find profile, assigns first matching profile to `conversation_context.profile_id`, then retrieves memory
     - Retrieves full memory (observations, summaries, communications) from Memora using `conversation_context.profile_id` and `config.twilio_memory_config.memory_store_id`
   - **If Memora is NOT configured**: Falls back to Maestro's `list_communications()` API to retrieve only communications (conversation history) - observations and summaries arrays will be empty
   - Both paths return `MemoryRetrievalResponse` → triggers `on_message_ready()` callback with memory response

4. **Message Ready Hook**: Developers register callbacks via `tac.on_message_ready(callback)` to handle incoming messages
   - For SMS: Receives `user_message`, `context` (ConversationSession), and `memory_response` (MemoryRetrievalResponse)
   - For Voice: Receives `user_message`, `context`, and `memory_response` (may be None)

### API Clients

**MemoryClient** (`src/tac/context/memory.py`):
- `retrieve_memory()`: Retrieve conversation memories
  - Endpoint: `POST /v1/Stores/{store_id}/Profiles/{profile_id}/Recall`
  - Returns: `MemoryRetrievalResponse` with `observations`, `summaries`, `sessions` fields
- `get_profile()`: Retrieve profile with traits
  - Endpoint: `GET /v1/Stores/{store_id}/Profiles/{profile_id}`
  - Query param: `traitGroups` (comma-separated list)
  - Returns: `ProfileResponse` with `id`, `createdAt`, `traits` fields
- `lookup_profile()`: Find profiles by identifier value (e.g., phone number, email)
  - Endpoint: `POST /Stores/{service_id}/Profiles/Lookup`
  - Request: `ProfileLookupRequest` with `id_type` (e.g., "phone", "email") and `value`
  - Returns: `ProfileLookupResponse` with `normalized_value` and `profiles` (list of profile IDs)
  - Normalizes identifier values according to identity resolution settings (e.g., E.164 for phone numbers)
  - Returns canonical profile IDs (earliest ID if profiles have been merged)
- `create_observation()`: Create a new observation in Memora
  - Endpoint: `POST /v1/Stores/{store_id}/Profiles/{profile_id}/Observations`
  - Parameters: `profile_id`, `content`, `source` (default: "conversation-intelligence"), `conversation_ids`, `occurred_at`
  - Returns: Dict with created observation details
- `create_conversation_summaries()`: Create conversation summaries in Memora
  - Endpoint: `POST /v1/Stores/{store_id}/Profiles/{profile_id}/ConversationSummaries`
  - Parameters: `profile_id`, `summaries` (list of dicts with `content`, `conversationId`, `occurredAt`, `source`)
  - Returns: Response dict with message field
- Auth: Uses HTTP Basic Authentication (Account SID as username, Auth Token as password)
- Models (from `src/tac/models/memory.py`):
  - `MemoryRetrievalRequest`: Request with `conversation_id`, `query`, optional date filters
  - `MemoryRetrievalResponse`: Response with observations, summaries, sessions arrays
  - `ObservationInfo`: Individual observation memories
  - `SummaryInfo`: Summarized insights from conversations
  - `SessionInfo`: Historical conversation sessions with messages
  - `SessionMessage`: Individual messages within sessions (includes `timestamp`, `direction`, `channel`, `from_address`, `to_address`, `content`)
  - `ProfileResponse`: Profile information with `id`, `createdAt`, `traits` (dict)
  - `ProfileLookupRequest`: Request with `id_type` and `value` for profile lookup
  - `ProfileLookupResponse`: Response with `normalized_value` and list of matching profile IDs

**ConversationClient** (`src/tac/context/conversation.py`):
- `create_conversation(name, configuration)`: Creates new conversation, returns `ConversationResponse`
  - Endpoint: `POST /v2/Conversations`
  - Note: Does not take `configuration_id` parameter (uses client's service_id internally)
- `list_conversations(status, channel_id, page_size, page_token)`: Lists conversations with optional filtering
  - Endpoint: `GET /v2/Conversations`
  - Returns: List of `ConversationResponse` objects
- `update_conversation(conversation_id, name, status, configuration)`: Updates an existing conversation
  - Endpoint: `PUT /v2/Conversations/{conversation_id}`
  - Note: `status` parameter is required
  - Returns: `ConversationResponse`
- `add_participant(conversation_id, name, type, addresses)`: Adds participant, returns `ParticipantResponse`
  - Endpoint: `POST /v2/Conversations/{conversation_id}/Participants`
  - Note: Does not take `profile_id` parameter
- `list_communications(conversation_id, channel_id, page_size, page_token)`: Lists communications for a conversation
  - Endpoint: `GET /v2/Conversations/{conversation_id}/Communications`
  - Returns: List of `CommunicationResponse` objects
  - Used for memory fallback when Memora is not configured
- `create_communication(conversation_id, communication_request)`: Creates a new communication in a conversation
  - Endpoint: `POST /v2/Conversations/{conversation_id}/Communications`
  - Returns: `Communication` object
- Auth: Uses HTTP Basic Authentication (Account SID as username, Auth Token as password)
- Models (from `src/tac/models/conversation.py`): `ConversationRequest`, `ConversationResponse`, `UpdateConversationRequest`, `ConversationsListResponse`, `ParticipantRequest`, `ParticipantResponse`, `ParticipantAddress`, `CommunicationRequest`, `Communication`, `CommunicationsListResponse`
- Pagination (from `src/tac/models/pagination.py`): `PaginationMeta` - Reusable pagination metadata for API list responses

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
- Known first party: `["tac"]`
- Import combining: `combine-as-imports = true`
- Enabled lint rules: pycodestyle (E/W), pyflakes (F), isort (I), flake8-bugbear (B), flake8-comprehensions (C4), pyupgrade (UP)
- Per-file ignores: Examples allow E402 (import order) and E501 (line length)

## Testing

Tests are located in `tests/` directory:
- `test_tac.py` - Core TAC class tests
- `test_config.py` - Configuration tests
- `test_integration.py` - Integration tests
- `test_sms_channel.py` - SMS channel tests
- `test_voice_channel.py` - Voice channel tests
- `test_voice_models.py` - Voice WebSocket message model tests
- `test_conversation.py` - Conversation client tests
- `test_conversation_event.py` - ConversationEvent model tests
- `test_tools.py` - Tools module tests (function_tool decorator, TACTool format conversions)
- `test_profile_retrieval.py` - Profile retrieval tests (trait_groups, fetch_profile, context.profile, lookup_profile)
- `test_profile_lookup_in_memory.py` - Automatic profile lookup in retrieve_memory tests (lookup by phone, fallback behavior)
- `test_memory_fallback.py` - Memory retrieval fallback tests (Memora to Maestro fallback)
- `test_init.py` - Package initialization tests
- `test_intelligence.py` - Conversation Intelligence processor tests (models, filtering, validation, content parsing)

Test requirements (pytest.ini_options in pyproject.toml):
- Test files: `test_*.py` or `*_test.py`
- Test classes: `Test*`
- Test functions: `test_*`

## Configuration Requirements

When initializing TAC, developers must provide:
- `environment` - TAC environment ("dev", "stage", or "prod") - automatically sets Memora and Maestro base URLs
- `twilio_account_sid` - From Twilio Console
- `twilio_auth_token` - From Twilio Console
- `conversation_service_sid` - Twilio Conversation Service SID (starts with `conv_configuration_`)

Optional configuration:
- `twilio_phone_number` - Twilio Phone Number to use for sending messages - **Required for SMS channel, optional for Voice**
- `twilio_memory_config` - Optional TwilioMemoryConfig object with:
  - `memory_store_id` field (starts with `mem_service_`) - Required for Twilio Memory functionality
  - `trait_groups` field (list of strings) - Optional, specifies which trait groups to include in profile retrieval
  - When provided, memory is automatically retrieved for SMS conversations and profile is fetched (once for Voice, per message for SMS)
- `log_level` - Optional, defaults to "INFO"

## Common Patterns

### SMS Channel Usage

```python
from tac import TAC, TACConfig
from tac.channels import SMSChannel
from tac.core.config import TwilioMemoryConfig

# 1. Setup TAC and SMS Channel
config = TACConfig(
    environment="prod",  # or "dev" or "stage"
    twilio_account_sid="AC...",
    twilio_auth_token="...",
    twilio_phone_number="+1234567890",
    conversation_service_sid="conv_configuration_...",
    twilio_memory_config=TwilioMemoryConfig(
        memory_store_id="mem_service_...",
        trait_groups=["Contact", "Preferences"]  # Optional: specify trait groups
    )  # Optional - only if using Twilio Memory
)
tac = TAC(config)
sms_channel = SMSChannel(tac)

# 2. Register callback to handle message processing
def handle_message(user_message, context, memory_response=None):
    # Access profile traits if available (fetched per message for SMS)
    if context.profile:
        traits = context.profile.traits
        # Profile includes name, location, preferences, etc.

    llm_response = call_your_llm(user_message, memory_response, context.profile)
    sms_channel.send_response(context.conversation_id, llm_response)

tac.on_message_ready(handle_message)

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
   - Fetches profile if `profile_id` is available (for Voice, this is the only fetch)
   - Calls `_start_conversation(conv_id, profile_id)` to store conversation session with profile

2. **`onMessageAdded`**: Processes incoming message
   - Validates message body (ignores empty/whitespace messages)
   - Auto-initializes conversation if not already started (extracts `profile_id` from webhook)
   - Fetches profile if `profile_id` is available (updates `context.profile` with fresh data)
   - Creates `ConversationSession` with `conversation_id`, `profile_id`, `channel`, `started_at`, and `profile`
   - Calls `tac.retrieve_memory(conversation_context, query=message_body)`
   - This triggers `on_message_ready` callback with `user_message`, `context`, and optional `memory_response`
   - `context.profile` contains profile traits if memory config includes `trait_groups`

3. **`onConversationRemoved`**: Cleans up conversation state
   - Calls `_end_conversation(conv_id)` to remove conversation from internal tracking

**Important**: Profile ID must be included in webhook data as `profile_id` or `ProfileId` field.

### Voice Channel Usage

The Voice channel provides WebSocket protocol handling for Twilio ConversationRelay. TAC offers two approaches:

**Simplified Approach (Recommended for Getting Started):**

Use `VoiceServerConfig` for automatic server setup with minimal boilerplate:

```python
from tac import TAC, TACConfig, VoiceServerConfig
from tac.channels.voice import VoiceChannel
from tac.core.config import TwilioMemoryConfig

# 1. Setup TAC and Voice Channel with server config
config = TACConfig(
    environment="prod",  # or "dev" or "stage"
    twilio_account_sid="AC...",
    twilio_auth_token="...",
    twilio_phone_number="+1234567890",
    conversation_service_sid="conv_configuration_...",
    twilio_memory_config=TwilioMemoryConfig(
        memory_store_id="mem_service_...",
        trait_groups=["Contact", "Preferences"]  # Optional: specify trait groups
    )  # Optional - only if using Twilio Memory
)
tac = TAC(config)

# 2. Register callback to handle memory-ready events
# Note: context.profile available (fetched once at conversation start for Voice)
async def handle_memory(context, memory_response, user_message):
    llm_response = await call_your_llm(user_message, memory_response)
    await voice_channel.send_response(context.conversation_id, llm_response)

tac.on_memory_ready(handle_memory)

# 3. Initialize channel with server configuration
voice_channel = VoiceChannel(
    tac=tac,
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
from tac import TAC, TACConfig
from tac.channels.voice import VoiceChannel
from tac.core.config import TwilioMemoryConfig

# 1. Setup TAC and Voice Channel
config = TACConfig(
    environment="prod",  # or "dev" or "stage"
    twilio_account_sid="AC...",
    twilio_auth_token="...",
    twilio_phone_number="+1234567890",
    conversation_service_sid="conv_configuration_...",
    twilio_memory_config=TwilioMemoryConfig(
        memory_store_id="mem_service_...",
        trait_groups=["Contact", "Preferences"]  # Optional: specify trait groups
    )  # Optional - only if using Twilio Memory
)
tac = TAC(config)
voice_channel = VoiceChannel(tac)

# 2. Register callback to handle message processing
async def handle_message(user_message, context, memory_response=None):
    # Access profile traits if available (fetched once at conversation start for Voice)
    if context.profile:
        traits = context.profile.traits
        # Profile includes name, location, preferences, etc.

    llm_response = await call_your_llm(user_message, memory_response, context.profile)
    await voice_channel.send_response(context.conversation_id, llm_response)

tac.on_message_ready(handle_message)

# 3. Create FastAPI app with TwiML and WebSocket endpoints
app = FastAPI()

@app.get("/twiml")
async def get_twiml():
    conversation = tac.maestro_client.create_conversation()
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

TAC provides two architectural patterns:

**Simplified Pattern (VoiceServerConfig):**
- **Built-in Server**: Automatic FastAPI app creation and endpoint setup
- **Convention over Configuration**: Opinionated defaults for quick starts
- **Use Case**: Getting started quickly, prototyping, simple voice applications

**Manual Pattern (Custom FastAPI):**
- **Protocol Layer** (`VoiceChannel`): Handles WebSocket lifecycle, processes ConversationRelay messages, manages conversation state
- **Application Layer** (User's FastAPI app): Provides TwiML endpoint and WebSocket endpoint
- **Benefits**: Separation of concerns, no forced dependencies, full control over server configuration
- **Use Case**: Custom middleware, authentication, integration with existing apps

### Conversation Intelligence Webhook Processing

The `OperatorResultProcessor` processes Conversation Intelligence webhook events and creates observations or summaries in Memora:

```python
from tac import TAC, TACConfig
from tac.intelligence import OperatorResultProcessor

# 1. Setup TAC with memory configuration
tac = TAC(config=TACConfig.from_env())

# 2. Initialize the processor (requires Twilio Memory to be enabled)
if tac.is_twilio_memory_enabled():
    processor = OperatorResultProcessor(tac.memory_client)

# 3. Process CI webhook events
@app.post("/ci-webhook")
async def ci_webhook_handler(request: Request):
    payload = await request.json()
    result = await processor.process_event(payload)

    if result.success:
        if result.skipped:
            # Event was filtered (non-MEMORA_, test event, etc.)
            print(f"Skipped: {result.skip_reason}")
        else:
            # Observations or summaries created
            print(f"Created {result.created_count} {result.event_type}(s)")
    else:
        print(f"Error: {result.error}")

    return result.model_dump()
```

**Filtering Logic** (ported from Go transformer.go):
- Only processes events where `intelligence_configuration.friendly_name` starts with `MEMORA_`
- Filters out test events (patterns: `testserviceconfig`, `test_service`, `test-service`, `testservice`)
- Validates required fields: `account_id`, `conversation_id`, `output_format`, `result`, `date_created`
- Validates ID formats: `conv_conversation_[0-7][0-9a-z]{25}`, `mem_profile_[0-7][0-9a-z]{25}`, `mem_(store|service)_[0-7][0-9a-z]{25}`

**Event Type Determination**:
- If `operator.friendly_name == "Summary Extractor"` → Creates conversation summaries
- Otherwise → Creates observations

See `examples/exec_demo/server.py` for a complete implementation.

## Dependencies

**Core Dependencies**:
- `pydantic>=2.0.0,<3` - Data validation
- `requests>=2.31.0,<3` - HTTP client
- `python-dotenv>=1.0.0,<2` - Environment variable loading
- `twilio>=9.8.3,<10` - Twilio Python SDK for messaging and other APIs

**Optional Dependencies**:
- `voice` - Voice channel support: `fastapi>=0.115.0,<1`, `uvicorn>=0.32.0,<1` (WebSocket support built-in to FastAPI)
- `dev` - Development tools: `pytest>=7.0.0,<8`, `pytest-cov>=5.0.0,<6`, `ruff>=0.8.0,<1`, `mypy>=1.0.0,<2`, `types-requests>=2.31.0,<3`, `openai>=1.0.0,<2`, `openai-agents>=0.1.0`, `fastapi`, `uvicorn`

**Note**: FastAPI and uvicorn are only required if using the Voice channel (either simplified or manual approach). The core TAC package does not depend on them.

## Tools Integration

The tools module provides LLM-compatible tool definitions for integrating Twilio Sierra primitives with LLM runtimes:

### TACTool Class (`tools/base.py`)

The `TACTool` dataclass represents a tool/function for LLM integration:
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
from tac.tools import function_tool

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
- Creates TACTool instance

**Using `create_tool()` function**:
```python
from tac.tools import create_tool

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
from tac.tools.messaging import create_messaging_tools

tools = create_messaging_tools(config)  # Returns [send_message]
```

**Memory Tools** (`tools/memory.py`):
```python
from tac.tools.memory import create_memory_tools

tools = create_memory_tools(config, session)  # Returns [retrieve_profile_memory]
```

Both factories return lists of `TACTool` objects configured with your TAC settings.

## Future Enhancements

Based on TAC.md architecture, these modules are planned but not yet implemented:
- **Adapters**: Runtime-specific adapters for OpenAI, Bedrock, Azure AI, LangChain (with `toOpenAiMessages()`, `toBedrockMessages()` formatting)
- **Additional Tools**: `twilio.escalate-to-human`, `twilio.session-memory.fetch`
- **Server**: Standalone server package for "batteries included" setup (separate from core to avoid forcing FastAPI dependency)
- **Analytics**: Integration with Twilio workbench observability

When implementing these features, refer to the detailed architecture diagrams and sequence flows in TAC.md.