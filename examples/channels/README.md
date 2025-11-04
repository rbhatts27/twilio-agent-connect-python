# TAF Channel Examples

Production-ready channel implementation examples for Twilio Agentic Framework (TAF).

> **Prerequisites:** Complete the [Quick Start setup](../README.md#quick-start) in the main examples README before running these servers.

## `sms.py` - SMS Webhook Server

FastAPI server to receive and process Twilio SMS webhooks with TAF, featuring complete OpenAI LLM integration.

**Additional Environment Variables:**
```bash
OPENAI_API_KEY=sk-xxxxx...  # For OpenAI LLM integration
```

**Features:**
- ✅ FastAPI server with `/sms` endpoint
- ✅ Async/await pattern for webhook handling
- ✅ OpenAI integration for intelligent responses
- ✅ Conversation history management
- ✅ Parses JSON payloads using ConversationEvent model
- ✅ Processes with TAF and triggers memory callbacks
- ✅ SMS channel integration with conversation lifecycle

**Usage:**
```bash
# Start server on 0.0.0.0:8000
uv run python examples/channels/sms.py
```

**Setup Twilio Webhook:**

1. Start ngrok tunnel:
   ```bash
   ngrok http 8000 --domain={your-ngrok-domain}
   ```

2. Your ngrok URL will be `https://{your-ngrok-domain}`

3. Configure Twilio Conversations API Webhook:
   - Go to Twilio Console → Conversations → Configuration
   - Set "Post-Event Webhook URL" to: `https://{your-ngrok-domain}/sms`
   - Enable webhook events: `onMessageAdded`, `onConversationAdded`, `onConversationRemoved`

4. Send an SMS to your Twilio phone number - the webhook will be triggered automatically

**How It Works:**
1. Twilio sends SMS webhook to `/sms` endpoint
2. SMS channel processes webhook and validates message
3. TAF retrieves memories (observations, summaries, sessions)
4. `handle_memory_ready` callback invoked with context and memories
5. OpenAI generates response using conversation history
6. Response sent back via SMS channel

**Key Code Pattern:**
```python
from fastapi import FastAPI, Request
from taf.channels.sms import SMSChannel

# Initialize TAF and channel
taf = TAF(config)
sms_channel = SMSChannel(taf)

# Register callback
async def handle_memory_ready(context, memory_response, user_message):
    # Generate response with OpenAI
    response = await openai_client.chat.completions.create(...)
    await sms_channel.send_response(context.conversation_id, response)

taf.on_memory_ready(handle_memory_ready)

# Create FastAPI app
app = FastAPI(title="TAF SMS Server")

@app.post("/sms")
async def sms_webhook(request: Request):
    webhook_data = await request.json()
    sms_channel.process_webhook(webhook_data)
    return {"status": "ok"}

# Start server
uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## `voice.py` - Simple Voice Channel Server

Basic voice server with FastAPI, TwiML generation, and WebSocket handling for Twilio Voice. This is the recommended starting point for voice integration without escalation features.

**Additional Environment Variables:**
```bash
VOICE_PUBLIC_DOMAIN={your-ngrok-domain}  # Your ngrok or public domain
OPENAI_API_KEY=sk-xxxxx...  # For OpenAI LLM integration
```

**Features:**
- ✅ FastAPI server with `/twiml` and `/ws` endpoints
- ✅ TwiML generation for incoming voice calls
- ✅ WebSocket connection management via `VoiceChannel.handle_websocket()`
- ✅ Memory retrieval and LLM integration (OpenAI)
- ✅ Proper message role handling (`role="assistant"`) for LLM context
- ✅ Conversation lifecycle management

**Usage:**
```bash
# 1. Add VOICE_PUBLIC_DOMAIN to your .env file
VOICE_PUBLIC_DOMAIN={your-ngrok-domain}

# 2. Start ngrok tunnel (in separate terminal)
ngrok http 8000 --domain={your-ngrok-domain}

# 3. Verify VOICE_PUBLIC_DOMAIN in .env matches your ngrok domain

# 4. Run voice server
uv run python examples/channels/voice.py

# 5. Configure Twilio phone number webhook to point to:
#    https://{your-ngrok-domain}/twiml
```

**How It Works:**
1. Twilio phone call arrives, webhook requests TwiML
2. `/twiml` endpoint generates TwiML with WebSocket URL
3. Voice channel establishes WebSocket connection via `/ws`
4. TAF retrieves memories (observations, summaries, sessions)
5. `handle_memory_ready` callback invoked with context and memories
6. OpenAI generates response using conversation history
7. Response sent back via voice channel

**Key Code Pattern:**
```python
from fastapi import FastAPI, Form, WebSocket
from taf.channels.voice import VoiceChannel

# Initialize TAF and channel
taf = TAF(config)
voice_channel = VoiceChannel(taf)

# Register callback
async def handle_memory_ready(context, memory_response, user_message):
    # Generate response with OpenAI
    response = await openai_client.chat.completions.create(...)
    await voice_channel.send_response(context.conversation_id, response)

taf.on_memory_ready(handle_memory_ready)

# Create FastAPI app
app = FastAPI(title="TAF Voice Server")

@app.post("/twiml")
async def post_twiml(From: str = Form(...)):
    websocket_url = f"wss://{public_domain}/ws"
    twiml = voice_channel.handle_incoming_call(
        websocket_url=websocket_url,
        called_phone_number=From,
        welcome_greeting="Hello! How can I assist you today?"
    )
    return Response(content=twiml, media_type="application/xml")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await voice_channel.handle_websocket(websocket)

# Start server
uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## `voice_escalation.py` - Voice Channel with Flex Escalation

Advanced voice server demonstrating agent handoff to Twilio Flex for human escalation. Use this example when you need to transfer calls from AI agents to human agents.

**Additional Environment Variables:**
```bash
VOICE_PUBLIC_DOMAIN={your-ngrok-domain}  # Your ngrok or public domain
OPENAI_API_KEY=sk-xxxxx...  # For OpenAI LLM integration
# Additional Flex configuration may be required
```

**Features:**
- ✅ All features from `voice.py` (TwiML, WebSocket, memory, LLM)
- ✅ Flex escalation tool integration
- ✅ OpenAI tool calling for intelligent escalation decisions
- ✅ `/handoff` endpoint for processing transfer requests
- ✅ Automatic detection of escalation requests (e.g., "speak to a human")
- ✅ Handoff handler registration with `taf.on_handoff()`

**Usage:**
```bash
# Same setup as voice.py, plus:
# 1. Ensure Flex workspace is configured
# 2. Run voice escalation server
uv run python examples/channels/voice_escalation.py

# 3. Configure Twilio phone number webhook to point to:
#    https://{your-ngrok-domain}/twiml
```

**How It Works:**
1. Voice call handled same as `voice.py`
2. AI agent monitors conversation for escalation requests
3. When user requests human assistance, LLM calls `flex_escalate_to_human` tool
4. Tool triggers handoff process via `/handoff` endpoint
5. Call transferred to available Flex agent
6. Conversation context preserved during transfer

**Key Code Pattern:**
```python
from taf.tools.flex_escalation import create_flex_escalation_tool
from taf.util.flex import handle_flex_handoff_logic

# Create escalation tool
flex_escalation_tool = create_flex_escalation_tool(
    websocket=voice_channel._active_websocket
)

# Register handoff handler
def flex_handoff_handler(request_data):
    return handle_flex_handoff_logic(request_data)

taf.on_handoff(flex_handoff_handler)

# Use tool with OpenAI
completion = await client.chat.completions.create(
    model="gpt-4o",
    messages=conversation_messages[conv_id],
    tools=[flex_escalation_tool.to_openai_format()],
    tool_choice="auto",
)

# Add handoff endpoint
@app.post("/handoff")
async def handoff(request: Request):
    return await voice_channel.handle_handoff(request)
```

**When to Use:**
- You need agent-to-human escalation
- Your application integrates with Twilio Flex
- Conversations require human intervention for complex cases
- You want intelligent escalation based on user requests
