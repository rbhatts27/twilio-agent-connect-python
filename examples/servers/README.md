# TAF Server Examples

Production-ready server implementations for Twilio Agentic Framework (TAF).

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
uv run python examples/servers/sms.py
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

## `voice.py` - Voice Server with ConversationRelay

Complete voice server with FastAPI, TwiML generation, and WebSocket handling for Twilio Voice.

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
uv run python examples/servers/voice.py

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
