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
- **Memory Management**: Automatic integration with Twilio Memora for persistent user context
- **Conversation Lifecycle**: Automatic tracking of conversation sessions and state
- **Type-Safe**: Full type hints and Pydantic models throughout
- **Callback-Based**: Simple `on_memory_ready` callback for LLM integration
- **Production Ready**: Comprehensive test coverage and error handling

## Get Started

To get started, set up your Python environment (Python 3.9 or newer required), and then install TAF SDK package.

### venv

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install git+https://github.com/twilio-internal/twilio-agentic-framework-python.git
```

### uv

If you're familiar with [uv](https://docs.astral.sh/uv/), using the tool would be even simpler:

```bash
uv init
uv add git+https://github.com/twilio-internal/twilio-agentic-framework-python.git
```

## Quick Example: SMS Channel with Memory

```python
from typing import List
from taf import TAF, TAFConfig
from taf.channels.sms import SMSChannel
from taf.core.context import ConversationContext
from taf.context.memora import MemoraMemory

# 1. Configure TAF with your Twilio credentials
config = TAFConfig(
    twilio_account_sid="ACxxxxx...",
    twilio_auth_token="your_auth_token",
    memora_base_url="https://memory.twilio.com/v1",
    memory_service_sid="MGxxxxx...",
    maestro_base_url="https://maestro.twilio.com/v1",
    conversation_service_sid="ISxxxxx..."
)

taf = TAF(config)

# 2. Register callback for when memories are retrieved
def handle_memory_ready(context: ConversationContext, memories: List[MemoraMemory]):
    """Called when memory retrieval completes"""
    print(f"Conversation: {context.conversation_id}")
    print(f"Profile: {context.profile_id}")
    print(f"Memories: {len(memories)}")

    # Process memories and call your LLM
    # llm_response = your_llm.generate(memories)
    # sms_channel.send_response(context.conversation_id, llm_response)

taf.on_memory_ready(handle_memory_ready)

# 3. Initialize SMS channel
sms_channel = SMSChannel(taf)

# 4. In your webhook handler (Flask example)
@app.route('/webhook', methods=['POST'])
def webhook():
    webhook_data = request.form.to_dict()
    sms_channel.process_webhook(webhook_data)
    return {"status": "ok"}
```

## Configuration

TAF requires the following configuration parameters:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `twilio_account_sid` | Your Twilio Account SID | `ACxxxxx...` |
| `twilio_auth_token` | Your Twilio Auth Token | From Twilio Console |
| `memora_base_url` | Memora API base URL | `https://memory.twilio.com/v1` |
| `memory_service_sid` | Memora Memory Service SID | `MGxxxxx...` |
| `maestro_base_url` | Maestro API base URL | `https://maestro.twilio.com/v1` |
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

- **`webhook_server.py`**: Full webhook server with SMS channel integration

---

# TAF Development / Contribution

0. Ensure you have [`uv`](https://docs.astral.sh/uv/) installed.

```bash
uv --version
```

1. Install dependencies

```bash
make sync
```

2. (After making changes) lint/test

```
make format # run tests linter and typechecker
```
