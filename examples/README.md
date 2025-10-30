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
   ```bash
   ENVIRONMENT=dev  # Required: 'dev', 'stage', or 'prod'
   MEMORY_SERVICE_SID=MGxxxxx...
   CONVERSATION_SERVICE_SID=ISxxxxx...
   TWILIO_ACCOUNT_SID=ACxxxxx...
   TWILIO_AUTH_TOKEN=your_auth_token
   TWILIO_PHONE_NUMBER=+1234567890
   OPENAI_API_KEY=sk-xxxxx...  # For examples using OpenAI
   ```

3. **Run an example:**
   ```bash
   # Start SMS webhook server
   uv run python examples/servers/sms.py

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

### [servers/](servers/) - Production Server Implementations

Ready-to-deploy server examples for handling Twilio webhooks and voice calls:

- **`sms.py`** - SMS webhook server with TAF integration
- **`voice.py`** - Voice server with FastAPI and ConversationRelay WebSocket

[→ View Server Examples](servers/)

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
