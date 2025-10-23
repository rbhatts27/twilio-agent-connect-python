"""
TAF SMS Demo - Executable Example

A complete SMS demo showing how to:
1. Set up TAF with SMS channel
2. Process webhooks from Twilio
3. Retrieve memories and context
4. Process messages with LLM (OpenAI)
5. Send responses back through SMS

This demo consolidates the FastAPI-based taf_sms_demo into a single executable script.
"""

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import JSONResponse, Response
from llm_service import LLMService

from taf import TAF, TAFConfig
from taf.channels.sms import SMSChannel
from taf.channels.voice import VoiceChannel
from taf.context.memory import MemoryRetrievalResponse
from taf.core.context import ConversationSession

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Initialize FastAPI app
app = FastAPI(
    title="TAF SMS Demo", description="SMS demo using Twilio Agentic Framework", version="1.0.0"
)

# Initialize TAF configuration
taf_config = TAFConfig(
    twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
    twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
    twilio_phone_number=os.getenv("TWILIO_PHONE_NUMBER"),
    memora_base_url=os.getenv("MEMORA_BASE_URL", "https://memory.twilio.com/v1"),
    memory_service_sid=os.getenv("MEMORY_SERVICE_SID"),
    maestro_base_url=os.getenv("MAESTRO_BASE_URL", "https://maestro.twilio.com/v1"),
    conversation_service_sid=os.getenv("CONVERSATION_SERVICE_SID"),
    log_level=os.getenv("LOG_LEVEL", "INFO"),
)

# Initialize TAF
taf = TAF(config=taf_config)
# Initialize channels
sms_channel = SMSChannel(taf)
voice_channel = VoiceChannel(taf)

# Initialize LLM service
llm_service = LLMService()


# Register memory ready callback
async def handle_memory_ready(
    context: ConversationSession,
    memory_response: MemoryRetrievalResponse,
    user_message: str,
) -> None:
    """
    Callback invoked when TAF memory retrieval completes.
    """
    try:
        llm_response = await llm_service.process_message(
            user_message=user_message,
            memory_response=memory_response,
            profile_id=context.profile_id,
        )

        if context.channel == "sms":
            await sms_channel.send_response(context.conversation_id, llm_response, role="assistant")
        elif context.channel == "voice":
            await voice_channel.send_response(
                context.conversation_id, llm_response, role="assistant"
            )
    except Exception as e:
        logger.error(f"Error handling memory ready callback: {e}", exc_info=True)


taf.on_memory_ready(handle_memory_ready)


@app.post("/sms")
async def sms_webhook(request: Request):
    """
    Webhook endpoint for Twilio SMS events.
    """
    try:
        webhook_data = await request.json()
        sms_channel.process_webhook(webhook_data)
        return JSONResponse(
            status_code=200, content={"status": "success", "message": "Webhook processed"}
        )
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/twiml")
async def get_twiml() -> Response:
    """Generate TwiML for Twilio voice calls."""
    public_domain = os.environ.get("VOICE_PUBLIC_DOMAIN", "")
    websocket_url = f"wss://{public_domain}/ws"
    twiml = voice_channel.handle_incoming_call(websocket_url=websocket_url)
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle voice streaming WebSocket connection."""
    await voice_channel.handle_websocket(websocket)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8001"))
    debug = os.getenv("DEBUG", "false").lower() == "true"

    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=debug)
