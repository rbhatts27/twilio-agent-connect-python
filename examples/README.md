# TAF Examples

This directory contains examples demonstrating how to use the Twilio Agentic Framework (TAF) with various LLM frameworks and channels.

## Quick Start

1. **Install dependencies:**
   ```bash
   make sync
   # or
   uv sync --extra dev
   ```

2. **Configure environment:**
   Copy `.env.example` to `.env` and fill in your credentials:

   **Required:**
   ```bash
   TWILIO_TAF_ENVIRONMENT=prod  # 'dev', 'stage', or 'prod'
   TWILIO_TAF_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_TAF_AUTH_TOKEN=your_auth_token_here
   TWILIO_TAF_PHONE_NUMBER=+1234567890
   TWILIO_TAF_CONVERSATION_SERVICE_SID=ISxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

   **Optional (for Twilio Memory):**
   ```bash
   TWILIO_TAF_MEMORY_STORE_ID=MGxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_TAF_MEMORY_API_KEY=your_api_key_here
   TWILIO_TAF_MEMORY_API_TOKEN=your_api_token_here
   TWILIO_TAF_TRAIT_GROUPS=Contact,Preferences
   ```

   **Optional (for specific examples):**
   ```bash
   TWILIO_TAF_LOG_LEVEL=INFO
   TWILIO_TAF_OPENAI_API_KEY=sk-xxxxx...  # For OpenAI examples
   TWILIO_TAF_VOICE_PUBLIC_DOMAIN=example.ngrok.io  # For voice examples
   TWILIO_TAF_KNOWLEDGE_IDS=KN123,KN456  # For knowledge tool examples
   ```

3. **Run an example:**
   ```bash
   # Start simplified voice server (recommended for getting started)
   uv run python examples/servers/voice.py

   # Or start SMS webhook server
   uv run python examples/channels/sms.py

   # Or try a tool integration example
   uv run python examples/tools/openai_chat_with_tools.py
   ```

## Examples Overview

### [exec_demo/](exec_demo/) - Multi-Channel Demo

Complete production-ready example demonstrating both SMS and Voice channels:

- **Multi-channel support** - Single server handling SMS and Voice
- **OpenAI Agents integration** - LLM with custom business tools
- **Memory integration** - Full TAF memory retrieval and context
- **Realistic use case** - ISP customer service agent with plan upgrades

[→ View Multi-Channel Demo](exec_demo/)

### [servers/](servers/) - Simplified Server Setup

**Recommended starting point** for new users. Examples using TAF's built-in server configuration for minimal boilerplate:

- **`voice.py`** - Simplified voice server with automatic FastAPI setup and endpoint creation

Perfect for getting started quickly. For advanced features or custom control, see the manual approach in `channels/`.

[→ View Simplified Server Examples](servers/)

### [channels/](channels/) - Channel Implementation Examples

Ready-to-deploy examples with full control over FastAPI configuration:

- **`sms.py`** - SMS channel webhook server with TAF integration
- **`voice.py`** - Voice channel server with manual FastAPI and WebSocket setup
- **`voice_escalation.py`** - Voice channel with Flex escalation for agent handoff to humans
- **`voice_interrupts.py`** - Voice channel with custom streaming agent and interrupt handling (supports any LLM provider)

Use these examples when you need custom middleware, authentication, or integration with existing apps.

[→ View Channel Examples](channels/)

### [tools/](tools/) - LLM Tool Integration

Examples showing how to integrate TAF tools with popular LLM frameworks:

- **`openai_chat_with_tools.py`** - OpenAI Chat Completions API + TAF tools
- **`openai_agents_with_tools.py`** - OpenAI Agents SDK + TAF tools
- **`messaging.py`** - Automated messaging with OpenAI Agents

[→ View Tool Examples](tools/)

## What You'll Learn

- ✅ Setting up TAF with Twilio services (Memora, Maestro)
- ✅ Processing SMS and Voice webhooks
- ✅ Retrieving and using user memories
- ✅ Integrating TAF tools with LLM frameworks
- ✅ Building production-ready agentic applications

## Need Help?

- See individual example READMEs for detailed setup and usage
- Check the main [project README](../README.md) for core concepts
- Review [CLAUDE.md](../CLAUDE.md) for architecture details
