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
- **Callback-Based**: Simple `on_memory_ready` callback for LLM integration
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
from typing import List
from taf import TAF, TAFConfig
from taf.channels.sms import SMSChannel
from taf.core.context import ConversationSession
from taf.context.memory import TwilioMemory

# 1. Configure TAF with your Twilio credentials
config = TAFConfig(
    environment="prod",  # or "dev" or "stage"
    twilio_account_sid="ACxxxxx...",
    twilio_auth_token="your_auth_token",
    twilio_phone_number="+1234567890",
    memory_service_sid="MGxxxxx...",
    conversation_service_sid="ISxxxxx..."
)

taf = TAF(config)

# 2. Register callback for when memories are retrieved
def handle_memory_ready(
    context: ConversationSession,
    memories: List[TwilioMemory],
    user_message: str
):
    """Called when memory retrieval completes"""
    print(f"Conversation: {context.conversation_id}")
    print(f"Profile: {context.profile_id}")
    print(f"User message: {user_message}")
    print(f"Memories: {len(memories)}")

    # Process memories and call your LLM with user message
    # llm_response = your_llm.generate(user_message, memories)
    # sms_channel.send_response(context.conversation_id, llm_response)

taf.on_memory_ready(handle_memory_ready)

# 3. Initialize SMS channel
sms_channel = SMSChannel(taf)

# 4. In your webhook handler (Flask example)
@app.route('/webhook', methods=['POST'])
def webhook():
    webhook_data = request.json
    sms_channel.process_webhook(webhook_data)
    return {"status": "ok"}
```

## Configuration

TAF requires the following configuration parameters:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `environment` | TAF environment - automatically sets Memora and Maestro URLs | `"prod"`, `"stage"`, or `"dev"` |
| `twilio_account_sid` | Your Twilio Account SID | `ACxxxxx...` |
| `twilio_auth_token` | Your Twilio Auth Token | From Twilio Console |
| `twilio_phone_number` | Your Twilio Phone Number | `+1234567890` |
| `memory_service_sid` | Memora Memory Service SID | `MGxxxxx...` |
| `conversation_service_sid` | Twilio Conversation Service SID | `ISxxxxx...` |
| `log_level` | Logging level (optional) | `INFO` (default) |

## How It Works

1. **Webhook Received**: Twilio sends SMS webhook to your server
2. **Channel Processing**: `SMSChannel` validates and processes the event
3. **Memory Retrieval**: TAF automatically retrieves user memories from Memora
4. **Callback Invoked**: Your `on_memory_ready` callback receives context and memories
5. **LLM Integration**: Your code calls LLM with memories and sends response

## Examples

Check out the [examples](examples) directory for complete working examples:

- **[`exec_demo/`](examples/exec_demo)**: Complete multi-channel demo with SMS and Voice support, OpenAI Agents integration, and custom business tools
- **[`servers/sms.py`](examples/servers/sms.py)**: SMS webhook server with FastAPI and TAF integration
- **[`servers/voice.py`](examples/servers/voice.py)**: Voice server with FastAPI, TwiML generation, and WebSocket handling
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
