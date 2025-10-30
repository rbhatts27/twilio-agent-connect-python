# TAF Tool Integration Examples

Examples showing how to integrate TAF tools (memory, knowledge, messaging) with LLM frameworks.

> **Prerequisites:** Complete the [Quick Start setup](../README.md#quick-start) in the main examples README before running these examples.

---

## `openai_chat_with_tools.py` - OpenAI Chat Completions + TAF Tools

Demonstrates integrating TAF memory and knowledge tools with OpenAI's Chat Completions API.

**Additional Environment Variables (Optional):**
```bash
KNOWLEDGE_IDS=KN123abc,KN456def  # Comma-separated knowledge resource IDs
```

**Features:**
- ✅ TAF memory tools for personalized context
- ✅ TAF knowledge tools for searching documentation
- ✅ Automatic tool execution and result handling
- ✅ Custom tool configuration (name, description, top-K)
- ✅ Async/await pattern for OpenAI API

**Usage:**
```bash
uv run python examples/tools/openai_chat_with_tools.py
```

**Key Code Pattern:**
```python
from taf.tools.memory import create_memory_tools
from taf.tools.knowledge import create_knowledge_tools_from_ids, KnowledgeToolConfig

# Create memory tools with session context
memory_tools = create_memory_tools(config, session)

# Create knowledge tools from environment variable
knowledge_ids_str = os.getenv("KNOWLEDGE_IDS", "")
knowledge_tools = []
if knowledge_ids_str:
    knowledge_ids = [k_id.strip() for k_id in knowledge_ids_str.split(",")]
    # Optional: Customize specific tools
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

---

## `openai_agents_with_tools.py` - OpenAI Agents SDK + TAF Tools

Shows how to use TAF memory and knowledge tools with the OpenAI Agents SDK for autonomous agent workflows.

**Additional Environment Variables (Optional):**
```bash
KNOWLEDGE_IDS=KN123abc,KN456def  # Comma-separated knowledge resource IDs
```

**Features:**
- ✅ TAF memory and knowledge tools as OpenAI Agent FunctionTools
- ✅ Agent automatically invokes tools as needed
- ✅ Memory search for personalized responses
- ✅ Knowledge search for documentation lookup
- ✅ Converter function for TAF → OpenAI Agents format

**Usage:**
```bash
uv run python examples/tools/openai_agents_with_tools.py
```

**Key Code Pattern:**
```python
from agents import Agent, FunctionTool, Runner
from taf.tools.memory import create_memory_tools
from taf.tools.knowledge import create_knowledge_tools_from_ids

# Create memory and knowledge tools
memory_tools = create_memory_tools(config, session)
knowledge_tools = create_knowledge_tools_from_ids(config, knowledge_ids)

# Convert to OpenAI Agents format
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

---

## `messaging.py` - OpenAI Agents SDK + TAF Messaging Tools

Demonstrates integrating TAF messaging tools with the OpenAI Agents SDK for automated message sending.

**Features:**
- ✅ TAF messaging tools integrated as OpenAI Agent FunctionTools
- ✅ Agent can send SMS messages through Twilio
- ✅ Converter function for TAF → OpenAI Agents format
- ✅ Natural language to SMS automation

**Usage:**
```bash
uv run python examples/tools/messaging.py
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

---

## Creating Knowledge Resources (Optional)

To use knowledge tools in these examples, create knowledge resources using Twilio's Knowledge API.

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

**After Creating Resources:**

All API calls return a knowledge object with an `id` field (e.g., `KN123abc`). Copy these IDs and add them to your `.env` file:

```bash
KNOWLEDGE_IDS=KN123abc,KN456def,KN789ghi
```
