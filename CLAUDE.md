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
python examples/webhook_server.py --port 3000

# Start ngrok tunnel for local testing
make ngrok
```

## Core Architecture

### Package Structure

The codebase follows a modular design matching the architecture diagram in TAF.md:

- **`src/taf/core/`** - Core TAF class, configuration, and context models
  - `taf.py` - Main `TAF` class with `retrieve_memory()` and `on_memory_ready()` hook
  - `config.py` - `TAFConfig` Pydantic model for SDK configuration
  - `context.py` - `SessionIdentity`, `Profile`, `Memory`, `ConversationSession` models

- **`src/taf/context/`** - Integration with Twilio Sierra primitives
  - `memory.py` - `MemoryClient` for memory retrieval (traits, observations, sessions)
  - `conversation.py` - `ConversationClient` for conversation/participant management

- **`src/taf/models/`** - Data models
  - `webhook.py` - `TwilioWebhookEvent` model for parsing Twilio webhook events

- **`src/taf/channels/`** - Channel-specific orchestration and conversation lifecycle management
  - `base.py` - `BaseChannel` abstract class with conversation session management (`_start_conversation`, `_end_conversation`)
  - `sms.py` - `SMSChannel` implementation handling webhook events, message validation, and memory retrieval
  - Future: `voice.py` for Voice/ConversationRelay
- **`src/taf/adapters/`** - Runtime-specific adapters (future: OpenAI, Bedrock, etc.)
- **`src/taf/tools/`** - LLM tools for Sierra primitives (future)

### Critical Workflow

**Channel-Based Architecture** (Recommended):

1. **Channel processes webhook**: Twilio sends webhook → `channel.process_webhook(webhook_data)` → channel parses event via `TwilioWebhookEvent` → validates message content

2. **Conversation Management**: Channel handles conversation lifecycle:
   - `onConversationAdded`: Channel extracts `profile_id` from webhook → calls `_start_conversation(conv_id, profile_id)` → stores conversation session
   - `onMessageAdded`: Channel validates message → auto-initializes conversation if needed → creates `ConversationSession` with all fields → calls `taf.retrieve_memory(conversation_context, query)`
   - `onConversationRemoved`: Channel calls `_end_conversation(conv_id)` → cleans up session

3. **Memory Retrieval**: `TAF.retrieve_memory(conversation_context, query)` → retrieves memories from Memora using `conversation_context.profile_id` and `config.memory_service_sid` → triggers `on_memory_ready()` callback if registered → returns list of `TwilioMemory` objects

4. **Memory Ready Hook**: Developers register callbacks via `taf.on_memory_ready(callback)` to receive `ConversationSession` and memories when ready (triggered automatically in `retrieve_memory()`)

### API Clients

**MemoryClient** (`src/taf/context/memory.py`):
- Endpoint: `POST /Services/{service_id}/Profiles/{profile_id}/Recall`
- Returns: List of `TwilioMemory` objects (traits, observations, sessions)
- Auth: Uses `X-Pre-Auth-Context` header with auth token
- Models: `TraitMemory`, `ObservationMemory`, `SessionMemory` with discriminated union on `memType`

**ConversationClient** (`src/taf/context/conversation.py`):
- `create_conversation()`: Creates new conversation, returns `ConversationResponse`
- `add_participant(conversation_id, profile_id)`: Adds participant, returns `ParticipantResponse`
- Auth: Uses `X-Twilio-Account-Sid` header

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
- `test_webhook.py` - Webhook event parsing tests
- `test_config.py` - Configuration tests
- `test_integration.py` - Integration tests

Test requirements (pytest.ini_options in pyproject.toml):
- Test files: `test_*.py` or `*_test.py`
- Test classes: `Test*`
- Test functions: `test_*`

## Configuration Requirements

When initializing TAF, developers must provide:
- `twilio_account_sid` - From Twilio Console
- `twilio_auth_token` - From Twilio Console
- `memora_base_url` - Memora API base URL (e.g., `https://memory.twilio.com/v1`)
- `memory_service_sid` - Memora service ID for memory retrieval (starts with `MG`)
- `maestro_base_url` - Maestro API base URL (e.g., `https://maestro.twilio.com/v1`)
- `conversation_service_sid` - Twilio Conversation Service SID (starts with `IS`)
- `log_level` - Optional, defaults to "INFO"

## Common Patterns

### SMS Channel Usage (Recommended)

```python
from typing import List
from taf import TAF, TAFConfig
from taf.channels import SMSChannel
from taf.core.context import ConversationSession
from taf.context.memory import TwilioMemory

# 1. Setup TAF and SMS Channel
config = TAFConfig(
    twilio_account_sid="AC...",
    twilio_auth_token="...",
    memora_base_url="https://memory.twilio.com/v1",
    memory_service_sid="MG...",
    maestro_base_url="https://maestro.twilio.com/v1",
    conversation_service_sid="IS..."
)
taf = TAF(config)
sms_channel = SMSChannel(taf)

# 2. Register callback to handle memory-ready events
def handle_memory(context: ConversationSession, memories: List[TwilioMemory]):
    """Called when memory retrieval completes."""
    print(f"Conversation {context.conversation_id} on channel {context.channel}")
    print(f"Profile: {context.profile_id}")

    # Process memories with type narrowing
    for memory in memories:
        if memory.mem_type == 'TRAIT':
            print(f"Trait: {memory.name} = {memory.value}")

    # Call your LLM here with conversation context
    llm_response = call_your_llm(memories)

    # Send response back through SMS channel
    sms_channel.send_response(context.conversation_id, llm_response)

taf.on_memory_ready(handle_memory)

# 3. In your webhook handler
@app.route('/webhook', methods=['POST'])
def webhook():
    webhook_data = request.json
    sms_channel.process_webhook(webhook_data)
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
   - Creates `ConversationSession` with `conversation_id`, `profile_id`, and `channel`
   - Calls `taf.retrieve_memory(conversation_context, query=message_body)`
   - This triggers `on_memory_ready` callback with full context and memories

3. **`onConversationRemoved`**: Cleans up conversation state
   - Calls `_end_conversation(conv_id)` to remove conversation from internal tracking

**Important**: Profile ID must be included in webhook data as `profile_id` or `ProfileId` field.

## Dependencies

**Core Dependencies**:
- `pydantic>=2.0.0,<3` - Data validation
- `requests>=2.31.0,<3` - HTTP client
- `python-dotenv>=1.0.0,<2` - Environment variable loading

**Dev Dependencies**:
- `pytest>=7.0.0,<8` - Testing framework
- `ruff>=0.8.0,<1` - Code formatting and linting (replaces black + isort + flake8)
- `mypy>=1.0.0,<2` - Type checking
- `types-requests>=2.31.0,<3` - Type stubs for requests

## Future Enhancements

Based on TAF.md architecture, these modules are planned but not yet implemented:
- **Channels**: Voice channel with ConversationRelay websocket handling, SMS channel
- **Adapters**: Runtime-specific adapters for OpenAI, Bedrock, Azure AI, LangChain (with `toOpenAiMessages()`, `toBedrockMessages()` formatting)
- **Tools**: LLM tools for `twilio.memory.fetch`, `twilio.knowledge.fetch`, `twilio.escalate-to-human`, `twilio.session-memory.fetch`
- **Server**: Webhook + websocket server package for "batteries included" setup
- **Analytics**: Integration with Twilio workbench observability

When implementing these features, refer to the detailed architecture diagrams and sequence flows in TAF.md.