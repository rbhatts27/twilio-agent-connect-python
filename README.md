# Twilio Agent Connect (TAC)

Twilio Agent Connect (TAC) is a powerful Python library designed to simplify the development of intelligent,
context-aware applications using Twilio's communication technologies. TAC provides seamless integration with Twilio's
Memora (memory management) and conversation services, enabling you to build LLM-powered agents with persistent memory
and conversation context.

> [!NOTE]
> Looking for the JavaScript/TypeScript version? Check out [TAC SDK JS/TS](https://github.com/twilio-internal/twilio-agentic-framework-typescript).

Explore the [examples](examples) directory to see the SDK in action.

## Key Features

- **SMS Channel Support**: Built-in webhook handling for Twilio SMS conversations
- **Voice Channel Support**: WebSocket protocol handling for Twilio Voice with ConversationRelay
- **Memory Management**: Automatic integration with Twilio Memora for persistent user context
- **Conversation Lifecycle**: Automatic tracking of conversation sessions and state
- **Type-Safe**: Full type hints and Pydantic models throughout
- **Callback-Based**: Simple `on_message_ready` callback for LLM integration with optional memory retrieval
- **Production Ready**: Comprehensive test coverage and error handling

## Get Started

To get started, set up your Python environment (Python 3.9 or newer required), and then install TAC SDK package.

### uv (Recommended)

We recommend using [uv](https://docs.astral.sh/uv/) for the best development experience:

```bash
uv init
uv add git+https://github.com/twilio-internal/twilio-agentic-framework-python.git

# Install with voice support (includes FastAPI and uvicorn)
uv add git+https://github.com/twilio-internal/twilio-agentic-framework-python.git --extra voice
```

### pip/venv (Alternative)

If you prefer using pip and venv:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install git+https://github.com/twilio-internal/twilio-agentic-framework-python.git

# Install with voice support
pip install "git+https://github.com/twilio-internal/twilio-agentic-framework-python.git[voice]"
```

## Quick Example: SMS Channel with Memory

```python
from typing import Optional
from tac import TAC, TACConfig
from tac.channels.sms import SMSChannel
from tac.models.session import ConversationSession
from tac.models.memory import MemoryRetrievalResponse

# 1. Configure TAC - automatically loads from environment variables
# Set these in your .env file:
#   TWILIO_TAC_ENVIRONMENT=prod
#   TWILIO_TAC_ACCOUNT_SID=ACxxxxx...
#   TWILIO_TAC_AUTH_TOKEN=your_auth_token
#   TWILIO_TAC_PHONE_NUMBER=+1234567890
#   TWILIO_TAC_CONVERSATION_SERVICE_SID=ISxxxxx...
#   TWILIO_TAC_MEMORY_STORE_ID=MGxxxxx... (optional)
#   TWILIO_TAC_MEMORY_API_KEY=your_api_key (optional)
#   TWILIO_TAC_MEMORY_API_TOKEN=your_api_token (optional)

tac = TAC(config=TACConfig.from_env())

# 2. Register callback for when messages are processed
def handle_message_ready(
    user_message: str,
    context: ConversationSession,
    memory_response: Optional[MemoryRetrievalResponse] = None
):
    """Called when message is received and memory is retrieved"""
    print(f"Conversation: {context.conversation_id}")
    print(f"Profile: {context.profile_id}")
    print(f"User message: {user_message}")

    if memory_response:
        print(f"Memories: {len(memory_response.observations)}")

    # Process message and call your LLM with user message
    # llm_response = your_llm.generate(user_message, memory_response)
    # sms_channel.send_response(context.conversation_id, llm_response)

tac.on_message_ready(handle_message_ready)

# 3. Initialize SMS channel
sms_channel = SMSChannel(tac)

# 4. In your webhook handler (Flask example)
@app.route('/webhook', methods=['POST'])
def webhook():
    webhook_data = request.json
    sms_channel.process_webhook(webhook_data)
    return {"status": "ok"}
```

## Quick Example: Voice Channel with Simplified Server

For the fastest way to get started with voice, use the built-in server configuration:

```python
import os
from tac import TAC, TACConfig, VoiceServerConfig
from tac.channels.voice import VoiceChannel
from tac.models.session import ConversationSession
from tac.models.memory import MemoryRetrievalResponse

# 1. Configure TAC - automatically loads from environment variables
tac = TAC(config=TACConfig.from_env())

# 2. Register callback for when memories are retrieved
async def handle_memory_ready(
    context: ConversationSession,
    memory_response: MemoryRetrievalResponse,
    user_message: str
):
    """Called when memory retrieval completes"""
    # Process memories and call your LLM
    # llm_response = await your_llm.generate(user_message, memory_response)
    # await voice_channel.send_response(context.conversation_id, llm_response)

tac.on_memory_ready(handle_memory_ready)

# 3. Initialize Voice channel with server configuration
voice_channel = VoiceChannel(
    tac=tac,
    server_config=VoiceServerConfig(
        public_domain=os.environ["TWILIO_TAC_VOICE_PUBLIC_DOMAIN"],  # Your ngrok domain
        host="0.0.0.0",
        port=8000,
        welcome_greeting="Hello! How can I assist you today?",
    ),
)

# 4. Start server (automatically creates FastAPI app with /twiml and /ws endpoints)
voice_channel.start()
```

That's it! The server automatically:
- Creates FastAPI app
- Sets up POST /twiml endpoint for call handling
- Sets up WebSocket /ws endpoint for ConversationRelay
- Creates conversations and participants
- Handles all WebSocket protocol details

For manual control over FastAPI configuration, see [`examples/channels/voice.py`](examples/channels/voice.py).

## Configuration

TAC can be configured using environment variables (recommended) or programmatically.

### Using Environment Variables (Recommended)

Set these in your `.env` file and use `TACConfig.from_env()`:

```python
from tac import TAC, TACConfig

# Automatically loads all configuration from environment
tac = TAC(config=TACConfig.from_env())
```

**Required Environment Variables:**
- `TWILIO_TAC_ENVIRONMENT` - TAC environment: `"prod"`, `"stage"`, or `"dev"` (sets Memora and Maestro URLs)
- `TWILIO_TAC_ACCOUNT_SID` - Your Twilio Account SID (e.g., `ACxxxxx...`)
- `TWILIO_TAC_AUTH_TOKEN` - Your Twilio Auth Token
- `TWILIO_TAC_PHONE_NUMBER` - Your Twilio Phone Number (e.g., `+1234567890`)
- `TWILIO_TAC_CONVERSATION_SERVICE_SID` - Twilio Conversation Service SID (e.g., `ISxxxxx...`)

**Optional Environment Variables:**
- `TWILIO_TAC_LOG_LEVEL` - Logging level (default: `INFO`)
- `TWILIO_TAC_MEMORY_STORE_ID` - Memora Memory Store ID (e.g., `MGxxxxx...`)
- `TWILIO_TAC_MEMORY_API_KEY` - API Key for Memora
- `TWILIO_TAC_MEMORY_API_TOKEN` - API Token for Memora
- `TWILIO_TAC_TRAIT_GROUPS` - Comma-separated trait groups (e.g., `"Contact,Preferences"`)

### Manual Configuration

You can also configure TAC programmatically:

```python
from tac import TAC, TACConfig
from tac.core.config import TwilioMemoryConfig

config = TACConfig(
    environment="prod",
    twilio_account_sid="ACxxxxx...",
    twilio_auth_token="your_auth_token",
    twilio_phone_number="+1234567890",
    conversation_service_sid="ISxxxxx...",
    twilio_memory_config=TwilioMemoryConfig(  # Optional
        memory_store_id="MGxxxxx...",
        api_key="your_api_key",
        api_token="your_api_token",
        trait_groups=["Contact", "Preferences"],
    ),
)

tac = TAC(config=config)
```

## How It Works

1. **Webhook Received**: Twilio sends SMS webhook to your server
2. **Channel Processing**: `SMSChannel` validates and processes the event
3. **Memory Retrieval**: TAC optionally retrieves user memories from Memora
4. **Callback Invoked**: Your `on_message_ready` callback receives user message, context, and optional memory response
5. **LLM Integration**: Your code calls LLM with message and optional memories, sends response

## Examples

Check out the [examples](examples) directory for complete working examples:

- **[`exec_demo/`](examples/exec_demo)**: Complete multi-channel demo with SMS and Voice support, OpenAI Agents integration, and custom business tools
- **[`servers/voice.py`](examples/servers/voice.py)**: **Recommended starting point** - Simplified voice server with automatic setup using VoiceServerConfig
- **[`channels/sms.py`](examples/channels/sms.py)**: SMS webhook server with FastAPI and TAC integration
- **[`channels/voice.py`](examples/channels/voice.py)**: Voice server with manual FastAPI, TwiML generation, and WebSocket handling
- **[`channels/voice_escalation.py`](examples/channels/voice_escalation.py)**: Voice server with Flex escalation for agent handoff to humans
- **[`tools/`](examples/tools)**: LLM tool integration examples with OpenAI Chat Completions and Agents SDK

---

# TAC Development / Contribution

TAC uses [`uv`](https://docs.astral.sh/uv/) for package management. Ensure you have it installed:

```bash
uv --version
```

### Setup Development Environment

```bash
# Install all dependencies (including dev tools)
make sync

# Or manually with uv
uv sync --all-extras --all-packages
```

### Running Tests and Checks

```bash
# Format code
make format

# Run linting
make lint

# Run type checking
make type-check

# Run tests
make test

# Run all checks at once
make check
```

# TAF E2E Tests
[![Build status](https://badge.buildkite.com/68ec35be00f84b3ad7895e1f2079ebccbe69dd75eba2889543.svg?branch=main)](https://buildkite.com/twilio/taf-e2e-tests)
