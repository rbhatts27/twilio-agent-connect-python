"""
TAF Multi-Channel Demo - Executable Example

A complete multi-channel demo showing how to:
1. Set up TAF with SMS and Voice channels
2. Process webhooks from Twilio (SMS and Voice)
3. Retrieve memories and context
4. Process messages with LLM (OpenAI)
5. Send responses back through SMS and Voice
6. Handle WebSocket connections for Voice streaming

This demo demonstrates TAF's channel-agnostic architecture with both SMS and Voice support.
"""

import logging
import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request, WebSocket
from fastapi.responses import JSONResponse, Response
from llm_service import LLMService
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionUserMessageParam,
)

from taf import TAF, TAFConfig
from taf.channels.sms import SMSChannel
from taf.channels.voice import VoiceChannel
from taf.core.context import ConversationSession
from taf.models.memory import MemoryRetrievalResponse

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Initialize FastAPI app
app = FastAPI(
    title="TAF Multi-Channel Demo",
    description="Multi-channel demo using Twilio Agentic Framework (SMS + Voice)",
    version="1.0.0",
)

# Initialize TAF configuration
taf_config = TAFConfig(
    environment=os.getenv("ENVIRONMENT", "prod"),
    twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
    twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
    twilio_phone_number=os.getenv("TWILIO_PHONE_NUMBER"),
    memory_service_sid=os.getenv("MEMORY_SERVICE_SID"),
    conversation_service_sid=os.getenv("CONVERSATION_SERVICE_SID"),
)

# Initialize TAF
taf = TAF(config=taf_config)
# Initialize channels
sms_channel = SMSChannel(taf)
voice_channel = VoiceChannel(taf)

# Initialize LLM service
llm_service = LLMService()

# User-managed conversation history
# Key: conversation_id, Value: list of messages
conversation_messages: dict[str, list[ChatCompletionMessageParam]] = {}
# todo: use a global conversation id until vnext is ready
active_conversation_sid = None


# Register memory ready callback
async def handle_memory_ready(
    context: ConversationSession,
    memory_response: MemoryRetrievalResponse,
    user_message: str,
) -> None:
    """
    Callback invoked when TAF memory retrieval completes.

    This demonstrates how to process memories and respond to messages.
    Uses LLM service with user-managed message history.
    """
    try:
        global active_conversation_sid
        # Initialize conversation history with system message if needed
        conv_id = context.conversation_id
        active_conversation_sid = conv_id
        if conv_id not in conversation_messages:
            conversation_messages[conv_id] = []

        # Add current user message
        user_msg: ChatCompletionUserMessageParam = {"role": "user", "content": user_message}
        conversation_messages[conv_id].append(user_msg)

        # Call LLM service with conversation history
        llm_response = await llm_service.process_message(
            user_message=user_message,
            memory_response=memory_response,
            profile_id=context.profile_id,
            conversation_history=conversation_messages[conv_id],
        )

        # Send response through appropriate channel
        if llm_response:
            if context.channel == "sms":
                await sms_channel.send_response(
                    context.conversation_id, llm_response, role="assistant"
                )
            elif context.channel == "voice":
                await voice_channel.send_response(
                    context.conversation_id, llm_response, role="assistant"
                )

            # Store assistant response in history
            assistant_msg: ChatCompletionAssistantMessageParam = {
                "role": "assistant",
                "content": llm_response,
            }
            conversation_messages[conv_id].append(assistant_msg)
    except Exception as e:
        logger.error(f"Error handling memory ready callback: {e}", exc_info=True)


taf.on_memory_ready(handle_memory_ready)


@app.post("/sms")
async def sms_webhook(request: Request):
    """
    Webhook endpoint for Twilio SMS events.
    """
    try:
        # Twilio sends form-encoded data, not JSON
        form_data = await request.form()
        webhook_data = dict(form_data)
        sms_channel.process_webhook(webhook_data)
        return JSONResponse(
            status_code=200, content={"status": "success", "message": "Webhook processed"}
        )
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.post("/twiml")
async def post_twiml(From: str = Form(...)) -> Response:
    """Generate TwiML for Twilio voice calls."""
    # Get WebSocket URL from environment
    public_domain = os.environ.get("VOICE_PUBLIC_DOMAIN", "")
    websocket_url = f"wss://{public_domain}/ws"

    # Generate TwiML with conversation and participant setup
    # From contains the caller's phone number
    twiml = voice_channel.handle_incoming_call(
        websocket_url=websocket_url,
        called_phone_number=From,
        welcome_greeting="Hello! How can I assist you today?",
        conversation_id=active_conversation_sid,
    )
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle voice streaming WebSocket connection."""
    await voice_channel.handle_websocket(websocket)


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
