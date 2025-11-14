# Twilio Agentic Framework (TAF)

Twilio Agentic Framework (TAF) is a powerful Python library designed to simplify the development of intelligent,
context-aware applications using Twilio's communication technologies. TAF provides seamless integration with Twilio's
Memora (memory management) and conversation services, enabling you to build LLM-powered agents with persistent memory
and conversation context.

> [!NOTE]
> Looking for the JavaScript/TypeScript version? Check out [TAF SDK JS/TS](https://github.com/twilio-internal/twilio-agentic-framework-typescript).

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

To get started, set up your Python environment (Python 3.9 or newer required), and then install TAF SDK package.

### uv (Recommended)

We recommend using [uv](https://docs.astral.sh/uv/) for the best development experience:

```bash
uv init
uv add git+https://github.com/twilio-internal/twilio-agentic-framework-python.git

# Install with voice support (includes websockets)
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
from typing import List, Optional
from taf import TAF, TAFConfig
from taf.channels.sms import SMSChannel
from taf.core.context import ConversationSession
from taf.context.memory import MemoryRetrievalResponse

# 1. Configure TAF with your Twilio credentials
from taf.core.config import TwilioMemoryConfig

config = TAFConfig(
    environment="prod",  # or "dev" or "stage"
    twilio_account_sid="ACxxxxx...",
    twilio_auth_token="your_auth_token",
    twilio_phone_number="+1234567890",
    twilio_memory_config=TwilioMemoryConfig(
        memory_store_id="MGxxxxx...",
        api_key="your_api_key",
        api_token="your_api_token"
    ),  # Optional
    conversation_service_sid="ISxxxxx..."
)

taf = TAF(config)

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

taf.on_message_ready(handle_message_ready)

# 3. Initialize SMS channel
sms_channel = SMSChannel(taf)

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
from taf import TAF, TAFConfig, VoiceServerConfig
from taf.channels.voice import VoiceChannel
from taf.core.context import ConversationSession
from taf.models.memory import MemoryRetrievalResponse

# 1. Configure TAF
from taf.core.config import TwilioMemoryConfig

config = TAFConfig(
    environment="prod",
    twilio_account_sid="ACxxxxx...",
    twilio_auth_token="your_auth_token",
    twilio_phone_number="+1234567890",
    twilio_memory_config=TwilioMemoryConfig(
        memory_store_id="MGxxxxx...",
        api_key="your_api_key",
        api_token="your_api_token"
    ),  # Optional
    conversation_service_sid="ISxxxxx..."
)

taf = TAF(config)

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

taf.on_memory_ready(handle_memory_ready)

# 3. Initialize Voice channel with server configuration
voice_channel = VoiceChannel(
    taf=taf,
    server_config=VoiceServerConfig(
        public_domain=os.environ["VOICE_PUBLIC_DOMAIN"],  # Your ngrok domain
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

TAF requires the following configuration parameters:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `environment` | TAF environment - automatically sets Memora and Maestro URLs | `"prod"`, `"stage"`, or `"dev"` |
| `twilio_account_sid` | Your Twilio Account SID | `ACxxxxx...` |
| `twilio_auth_token` | Your Twilio Auth Token | From Twilio Console |
| `twilio_phone_number` | Your Twilio Phone Number | `+1234567890` |
| `twilio_memory_config` | Optional Twilio Memory configuration (requires `memory_store_id`, `api_key`, and `api_token`) | `TwilioMemoryConfig(memory_store_id="MGxxxxx...", api_key="...", api_token="...")` |
| `conversation_service_sid` | Twilio Conversation Service SID | `ISxxxxx...` |
| `log_level` | Logging level (optional) | `INFO` (default) |

## How It Works

1. **Webhook Received**: Twilio sends SMS webhook to your server
2. **Channel Processing**: `SMSChannel` validates and processes the event
3. **Memory Retrieval**: TAF optionally retrieves user memories from Memora
4. **Callback Invoked**: Your `on_message_ready` callback receives user message, context, and optional memory response
5. **LLM Integration**: Your code calls LLM with message and optional memories, sends response

## Examples

Check out the [examples](examples) directory for complete working examples:

- **[`exec_demo/`](examples/exec_demo)**: Complete multi-channel demo with SMS and Voice support, OpenAI Agents integration, and custom business tools
- **[`servers/voice.py`](examples/servers/voice.py)**: **Recommended starting point** - Simplified voice server with automatic setup using VoiceServerConfig
- **[`channels/sms.py`](examples/channels/sms.py)**: SMS webhook server with FastAPI and TAF integration
- **[`channels/voice.py`](examples/channels/voice.py)**: Voice server with manual FastAPI, TwiML generation, and WebSocket handling
- **[`channels/voice_escalation.py`](examples/channels/voice_escalation.py)**: Voice server with Flex escalation for agent handoff to humans
- **[`tools/`](examples/tools)**: LLM tool integration examples with OpenAI Chat Completions and Agents SDK

---

# TAF Development / Contribution

TAF uses [`uv`](https://docs.astral.sh/uv/) for package management. Ensure you have it installed:

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
