# TAF Examples

This directory contains examples for the Twilio Agentic Framework (TAF).

## Quick Start

0. Install dev dependencies (includes OpenAI and other required packages):
   ```bash
   make sync
   # or
   uv sync --extra dev
   ```
1. Copy `.env.example` to `.env` and fill in your Twilio and OpenAI credentials.
2. **(Optional)** Create knowledge resources using the Knowledge API (see below) and add their IDs to `.env` as `KNOWLEDGE_IDS=KN123,KN456`.

## Creating Knowledge Resources (Optional)

If you want to use knowledge tools in the examples, you'll need to create knowledge resources using Twilio's Knowledge API. You can create three types of knowledge:

### Text Knowledge (Direct Content)

Create knowledge from plain text content:

```bash
curl -X POST https://knowledge.twilio.com/v1/Knowledge \
  -H "Content-Type: application/json" \
  -u "YOUR_TWILIO_ACCOUNT_SID:YOUR_TWILIO_AUTH_TOKEN" \
  -d '{
    "type": "Text",
    "name": "Product FAQ",
    "description": "Frequently asked questions about our products",
    "knowledge_source_details": {
      "content": "Q: What is the return policy?\nA: You can return items within 30 days...\n\nQ: How long does shipping take?\nA: Standard shipping takes 3-5 business days..."
    }
  }'
```

### Web Knowledge (URL Crawling)

Create knowledge by crawling a website:

```bash
curl -X POST https://knowledge.twilio.com/v1/Knowledge \
  -H "Content-Type: application/json" \
  -u "YOUR_TWILIO_ACCOUNT_SID:YOUR_TWILIO_AUTH_TOKEN" \
  -d '{
    "type": "Web",
    "name": "Company Documentation",
    "description": "Official product documentation",
    "knowledge_source_details": {
      "source": "https://example.com/docs",
      "crawl_depth": 3,
      "crawl_period_min": 1440
    }
  }'
```

**Parameters:**
- `source`: The URL to crawl
- `crawl_depth`: How many levels deep to crawl (optional, default: 1)
- `crawl_period_min`: How often to re-crawl in minutes (optional)

### File Knowledge (Document Upload)

Create knowledge by uploading a file (PDF, DOCX, TXT, etc.):

```bash
curl -X POST https://knowledge.twilio.com/v1/Knowledge/Upload \
  -H "Content-Type: multipart/form-data" \
  -u "YOUR_TWILIO_ACCOUNT_SID:YOUR_TWILIO_AUTH_TOKEN" \
  -F 'type=File' \
  -F 'name=Employee Handbook' \
  -F 'description=Company policies and procedures' \
  -F 'file_name=file_0' \
  -F 'file_0=@/path/to/handbook.pdf'
```

**Response:**

All API calls return a knowledge object with an `id` field (e.g., `KN123abc`). Copy these IDs and add them to your `.env` file:

```bash
KNOWLEDGE_IDS=KN123abc,KN456def,KN789ghi
```

## Available Examples

### `openai_chat_with_tools.py` - OpenAI Chat Completions with TAF Tools
Demonstrates integrating TAF memory and knowledge tools with OpenAI's Chat Completions API.

**Features:**
- ✅ TAF memory tools for personalized context
- ✅ TAF knowledge tools for searching documentation
- ✅ Automatic tool execution and result handling
- ✅ Custom tool configuration (name, description, top-K)
- ✅ Async/await pattern for OpenAI API

**Usage:**
```bash
uv run python examples/openai_chat_with_tools.py
```

**Key Code Pattern:**
```python
from taf.tools.memory import create_memory_tools
from taf.tools.knowledge import create_knowledge_tools_from_ids, KnowledgeToolConfig

# Create memory tools with session context
memory_tools = create_memory_tools(config, session)

# Create knowledge tools from environment variable
# Set KNOWLEDGE_IDS in .env as comma-separated list (e.g., "KN123,KN456")
knowledge_ids_str = os.getenv("KNOWLEDGE_IDS", "")
knowledge_tools = []
if knowledge_ids_str:
    knowledge_ids = [k_id.strip() for k_id in knowledge_ids_str.split(",")]
    # Optional: Customize specific tools via tool_configs
    tool_configs = {
        "KN456": KnowledgeToolConfig(name="search_return_policy", top_k=3),
    }
    knowledge_tools = create_knowledge_tools_from_ids(config, knowledge_ids, tool_configs)

# Combine and convert to OpenAI format
all_tools = memory_tools + knowledge_tools
openai_tools = [tool.to_openai_format() for tool in all_tools]

# Use in chat completions
response = await client.chat.completions.create(
    model="gpt-4",
    messages=messages,
    tools=openai_tools,
    tool_choice="auto"
)
```

### `openai_agents_with_tools.py` - OpenAI Agents SDK with TAF Tools
Shows how to use TAF memory and knowledge tools with the OpenAI Agents SDK for autonomous agent workflows.

**Features:**
- ✅ TAF memory and knowledge tools as OpenAI Agent FunctionTools
- ✅ Agent automatically invokes tools as needed
- ✅ Memory search for personalized responses
- ✅ Knowledge search for documentation lookup
- ✅ Converter function for TAF → OpenAI Agents format

**Usage:**
```bash
uv run python examples/openai_agents_with_tools.py
```

**Key Code Pattern:**
```python
from agents import Agent, FunctionTool, Runner
from taf.tools.memory import create_memory_tools
from taf.tools.knowledge import create_knowledge_tools_from_ids, KnowledgeToolConfig

# Create memory tools
memory_tools = create_memory_tools(config, session)

# Create knowledge tools from environment variable
# Set KNOWLEDGE_IDS in .env as comma-separated list (e.g., "KN123,KN456")
knowledge_ids_str = os.getenv("KNOWLEDGE_IDS", "")
knowledge_tools = []
if knowledge_ids_str:
    knowledge_ids = [k_id.strip() for k_id in knowledge_ids_str.split(",")]
    # Optional: Customize specific tools via tool_configs
    tool_configs = {
        "KN456": KnowledgeToolConfig(name="search_return_policy", top_k=3),
    }
    knowledge_tools = create_knowledge_tools_from_ids(config, knowledge_ids, tool_configs)

# Combine and convert to OpenAI Agents format
all_tools = memory_tools + knowledge_tools
openai_agent_tools = [taf_tool_to_openai_agents(tool) for tool in all_tools]

# Create agent with tools
agent = Agent(
    name="support_agent",
    model="gpt-4",
    tools=openai_agent_tools,
    instructions="You are a helpful customer support assistant..."
)

# Run agent
response = await Runner.run(agent, "Did I order a blue fleece?")
```

### `messaging.py` - OpenAI Agents SDK with TAF Messaging Tools
Demonstrates integrating TAF messaging tools with the OpenAI Agents SDK for automated message sending.

**Features:**
- ✅ TAF messaging tools integrated as OpenAI Agent FunctionTools
- ✅ Agent can send SMS messages through Twilio
- ✅ Converter function for TAF → OpenAI Agents format
- ✅ Natural language to SMS automation

**Usage:**
```bash
uv run python examples/messaging.py
```

**Key Code Pattern:**
```python
from agents import Agent, FunctionTool, Runner
from taf.tools.messaging import create_messaging_tools

# Create TAF messaging tools
messaging_tools = create_messaging_tools(config)

# Convert to OpenAI Agents format
agent_tools = [taf_tool_to_agent_tool(tool) for tool in messaging_tools]

# Create agent with messaging capabilities
agent = Agent(
    name="messaging agent",
    model="gpt-4o",
    tools=agent_tools,
    instructions="You are a helpful assistant"
)

# Agent can now send messages via natural language
response = await Runner.run(
    agent, "Send a message to +12345678900 saying 'Hello from TAF agent!'"
)
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
uv run python examples/webhook_server.py

# Or use the Makefile
make server

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

### `voice_server.py` - Voice Server with ConversationRelay
Complete voice server implementation with FastAPI, TwiML generation, and WebSocket handling for Twilio Voice ConversationRelay.

**Features:**
- ✅ FastAPI server with `/twiml` and `/ws` endpoints
- ✅ TwiML generation for incoming voice calls
- ✅ WebSocket connection management via `VoiceChannel.handle_websocket()`
- ✅ Memory retrieval and LLM integration (OpenAI)
- ✅ Proper message role handling (`role="assistant"`) for LLM context
- ✅ Conversation lifecycle management

**Architecture:**
- **VoiceChannel**: Protocol handler only (no built-in server)
- **Application Layer**: Creates FastAPI app, handles TwiML generation
- **RelayConfiguration**: Configures public domain, host, port, greeting

**Usage:**
```bash
# 1. Set up environment variables in .env
ENVIRONMENT=dev  # or 'stage' or 'prod' - automatically sets Memora/Maestro URLs
VOICE_PUBLIC_DOMAIN=your-domain.ngrok.io  # Your ngrok or public domain
MEMORY_SERVICE_SID=MGxxxxx...
CONVERSATION_SERVICE_SID=ISxxxxx...
TWILIO_ACCOUNT_SID=ACxxxxx...
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
OPENAI_API_KEY=sk-xxxxx...

# 2. Start ngrok tunnel (in separate terminal)
ngrok http 8000

# 3. Update VOICE_PUBLIC_DOMAIN in .env with ngrok domain (e.g., abc123.ngrok.io)

# 4. Run voice server
uv run python examples/voice_server.py

# 5. Configure Twilio phone number webhook to point to:
#    https://your-domain.ngrok.io/twiml
```

**Key Code Pattern:**
```python
from fastapi import FastAPI, WebSocket
from fastapi.responses import Response
from taf.channels.voice import VoiceChannel

# Initialize TAF and Voice channel
taf = TAF(config)
voice_channel = VoiceChannel(taf)

# Register memory callback
async def handle_memory_ready(context, memories, user_message):
    # Call your LLM
    response = await openai_client.chat.completions.create(...)

    # Send response with role for proper LLM context
    await voice_channel.send_response(
        context.conversation_id, response, role="assistant"
    )

taf.on_memory_ready(handle_memory_ready)

# Create FastAPI app
app = FastAPI()

@app.get("/twiml")
async def get_twiml():
    """Generate TwiML for incoming calls"""
    conversation = taf.maestro_client.create_conversation()
    # Return TwiML with ConversationRelay pointing to /ws endpoint
    ...

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connection"""
    await voice_channel.handle_websocket(websocket)

# Run with uvicorn
uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Why This Architecture?**
- **Separation of Concerns**: VoiceChannel handles protocol, you handle TwiML/server
- **Flexibility**: Easy to integrate into existing FastAPI applications
- **Customization**: Full control over TwiML generation and server configuration


Happy building! 🚀