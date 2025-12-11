"""
TAC Multi-Channel Demo - Executable Example

A complete multi-channel demo showing how to:
1. Set up TAC with SMS and Voice channels
2. Process webhooks from Twilio (SMS and Voice)
3. Retrieve memories and context
4. Process messages with LLM (OpenAI)
5. Send responses back through SMS and Voice
6. Handle WebSocket connections for Voice streaming

This demo demonstrates TAC's channel-agnostic architecture with both SMS and Voice support.
"""

import json
import os
from typing import Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request, WebSocket
from fastapi.datastructures import FormData
from fastapi.responses import JSONResponse, Response
from llm_service import LLMService
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionUserMessageParam,
)

from tac import TAC, TACConfig
from tac.channels import SMSChannel
from tac.channels.voice import VoiceChannel
from tac.core.logging import get_logger, setup_logging
from tac.models.memory import MemoryRetrievalResponse
from tac.models.session import ConversationSession
from tac.util.flex import handle_flex_handoff_logic

load_dotenv()

# Configure structured logging using TAC's logging utilities
setup_logging(log_level="INFO", log_format="console")

logger = get_logger(__name__)

app = FastAPI(
    title="TAC Multi-Channel Demo",
    description="Multi-channel demo using Twilio Agent Connect",
    version="1.0.0",
)

# Initialize TAC - automatically loads all configuration from environment variables
# Required env vars:
#   - TWILIO_TAC_ENVIRONMENT (dev, stage, or prod)
#   - TWILIO_TAC_CONVERSATION_SERVICE_SID
#   - TWILIO_TAC_ACCOUNT_SID
#   - TWILIO_TAC_AUTH_TOKEN
#   - TWILIO_TAC_PHONE_NUMBER
# Optional env vars:
#   - TWILIO_TAC_LOG_LEVEL (defaults to INFO)
#   - TWILIO_TAC_MEMORY_STORE_ID, TWILIO_TAC_MEMORY_API_KEY, TWILIO_TAC_MEMORY_API_TOKEN (for Twilio Memory)
#   - TWILIO_TAC_TRAIT_GROUPS (comma-separated, e.g., "Contact,Preferences")
tac = TAC(config=TACConfig.from_env())
voice_channel = VoiceChannel(tac)
sms_channel = SMSChannel(tac)

llm_service = LLMService(tac)

# User-managed conversation history
# Key: conversation_id, Value: list of messages
conversation_messages: dict[str, list[ChatCompletionMessageParam]] = {}


async def flex_handoff_handler(request_data: FormData) -> Response:
    """
    Handler for Flex handoff requests.

    This function is called when the AI agent triggers a handoff to a human agent.
    It processes the handoff logic and returns the appropriate response.
    """
    return handle_flex_handoff_logic(
        request_data, flex_workflow_sid=os.environ.get("TWILIO_TAC_VOICE_HANDOFF_FLEX_WORKFLOW_SID")
    )


# Register message ready callback
async def handle_message_ready(
    user_message: str,
    context: ConversationSession,
    memory_response: Optional[MemoryRetrievalResponse],
) -> None:
    """
    Callback invoked when a message is ready to be processed.

    This demonstrates how to process memories and respond to messages.
    Uses LLM service with user-managed message history.
    Memory response is optional - SMS channel provides it, Voice channel does not.
    """
    conv_id = context.conversation_id
    try:
        # Initialize conversation history if needed
        if conv_id not in conversation_messages:
            conversation_messages[conv_id] = []

        # Add current user message
        user_msg: ChatCompletionUserMessageParam = {"role": "user", "content": user_message}
        conversation_messages[conv_id].append(user_msg)

        # Log incoming message with clear separator
        logger.info(
            f"\n{'=' * 80}\n📨 USER MESSAGE | Channel: {context.channel.upper()}",
            conversation_id=conv_id,
        )
        logger.info(
            f'💬 "{user_message}"',
            conversation_id=conv_id,
            profile_id=context.profile_id,
        )

        # Retrieve memory only if Twilio Memory is enabled
        memory_response = None
        if tac.is_twilio_memory_enabled():
            try:
                memory_response = await tac.retrieve_memory(context, query=user_message)
                if memory_response:
                    obs_count = (
                        len(memory_response.observations) if memory_response.observations else 0
                    )
                    sum_count = len(memory_response.summaries) if memory_response.summaries else 0
                    logger.info(
                        f"🧠 MEMORY | Retrieved: {obs_count} observations, {sum_count} summaries",
                        conversation_id=conv_id,
                    )
            except Exception as e:
                logger.error(
                    "❌ Failed to retrieve memory",
                    conversation_id=conv_id,
                    error=str(e),
                    exc_info=True,
                )

        # Get the active websocket for this conversation if it's a voice channel
        active_websocket = (
            voice_channel.get_websocket(conv_id) if context.channel == "voice" else None
        )

        # Process message with LLM
        logger.info("🤖 AI AGENT | Processing message...", conversation_id=conv_id)
        llm_response = await llm_service.process_message(
            user_message=user_message,
            memory_response=memory_response,
            context=context,
            websocket=active_websocket,
            conversation_history=conversation_messages[conv_id],
        )

        # Send response through appropriate channel
        if llm_response:
            if context.channel == "voice":
                await voice_channel.send_response(
                    context.conversation_id, llm_response, role="assistant"
                )
            elif context.channel == "sms":
                await sms_channel.send_response(
                    context.conversation_id, llm_response, role="assistant"
                )
            else:
                logger.error(
                    "❌ Unknown channel",
                    conversation_id=conv_id,
                    channel=context.channel,
                )
                return

            logger.info(
                "✅ AI RESPONSE | Sent successfully",
                conversation_id=conv_id,
            )
            logger.info(
                f'💬 "{llm_response}"',
                conversation_id=conv_id,
            )

            # Check if there's a pending handoff in session metadata
            if "pending_handoff" in context.metadata:
                pending_handoff = context.metadata["pending_handoff"]
                handoff_data_json = pending_handoff.get("handoff_data")

                if context.channel == "voice" and handoff_data_json:
                    try:
                        logger.info(
                            f"\n{'=' * 80}\n🔄 HANDOFF | Transferring to human agent...",
                            conversation_id=conv_id,
                        )
                        await active_websocket.send_text(
                            json.dumps({"type": "end", "handoffData": handoff_data_json})
                        )
                        # Clear the metadata after processing
                        del context.metadata["pending_handoff"]
                    except Exception as e:
                        logger.error(
                            "❌ Handoff failed",
                            conversation_id=conv_id,
                            error=str(e),
                            exc_info=True,
                        )

            # Store assistant response in history
            assistant_msg: ChatCompletionAssistantMessageParam = {
                "role": "assistant",
                "content": llm_response,
            }
            conversation_messages[conv_id].append(assistant_msg)
    except Exception as e:
        logger.error(
            "❌ Error processing message",
            conversation_id=conv_id,
            error=str(e),
            exc_info=True,
        )


tac.on_message_ready(handle_message_ready)

tac.on_handoff(flex_handoff_handler)


@app.post("/sms")
async def sms_webhook(request: Request) -> JSONResponse:
    """Handle incoming SMS webhooks from Twilio."""
    try:
        form_data = await request.json()
        webhook_data = dict(form_data)

        # Process all events (including deduplicated communication.created)
        await sms_channel.process_webhook(webhook_data)
        return JSONResponse(content={"status": "ok"}, status_code=200)

    except Exception as e:
        logger.error("❌ SMS webhook error", error=str(e), exc_info=True)
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=400)


@app.post("/twiml")
async def post_twiml(
    from_number: str = Form(..., alias="From"),
    to_number: str = Form(..., alias="To"),
    call_sid: str = Form(..., alias="CallSid"),
) -> Response:
    """Generate TwiML for Twilio voice calls."""
    logger.info(
        f"\n{'=' * 80}\n📞 INCOMING CALL | {from_number} → {to_number}",
        call_sid=call_sid,
    )

    # Get WebSocket URL from environment
    public_domain = os.environ.get("TWILIO_TAC_VOICE_PUBLIC_DOMAIN", "")
    websocket_url = f"wss://{public_domain}/ws"
    callback_url = f"https://{public_domain}/conversation-relay-callback"

    # Generate TwiML with conversation and participant setup
    # From contains the caller's phone number, To contains the Twilio number
    twiml = await voice_channel.handle_incoming_call(
        websocket_url=websocket_url,
        to_number=to_number,
        from_number=from_number,
        call_sid=call_sid,
        action_url=callback_url,
    )

    logger.info("✅ CALL SETUP | TwiML generated, connecting WebSocket...", call_sid=call_sid)
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle voice streaming WebSocket connection."""
    logger.info("🔌 WEBSOCKET | Connected - streaming ready")
    await voice_channel.handle_websocket(websocket)
    logger.info("🔌 WEBSOCKET | Disconnected")


@app.post("/conversation-relay-callback")
async def conversation_relay_callback(request: Request) -> Response:
    """Handle ConversationRelay callback webhook from Twilio."""
    return await voice_channel.handle_conversation_relay_callback(request)


if __name__ == "__main__":
    # Configure uvicorn logging to reduce noise
    uvicorn_log_config = uvicorn.config.LOGGING_CONFIG
    uvicorn_log_config["formatters"]["default"]["fmt"] = "%(levelprefix)s %(message)s"
    uvicorn_log_config["formatters"]["access"]["fmt"] = (
        '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s'
    )

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        log_level="warning",  # Only show warnings and errors from uvicorn
        access_log=False,  # Disable access logs
        log_config=uvicorn_log_config,
    )
