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
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from llm_service import LLMService

from taf import TAF, TAFConfig
from taf.channels.sms import SMSChannel
from taf.context.memory import MemoryRetrievalResponse
from taf.core.context import ConversationSession

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TAFWebhookHandler:
    """
    Webhook handler that integrates TAF with LLM processing.

    This handler:
    1. Receives webhooks and passes them to TAF SMSChannel
    2. Processes memory retrieval through TAF
    3. Sends messages with memory context to LLM
    4. Returns LLM responses via SMSChannel
    """

    def __init__(self, taf: TAF, llm_service: LLMService):
        """
        Initialize webhook handler.

        Args:
            taf: Initialized TAF instance
            llm_service: LLM service for message processing
        """
        self.taf = taf
        self.llm_service = llm_service
        self.sms_channel = SMSChannel(taf)

        # Register memory ready callback
        self.taf.on_memory_ready(self._handle_memory_ready)

        logger.info("TAF webhook handler initialized")

    def process_webhook(self, webhook_data: dict) -> None:
        """
        Process incoming webhook from Twilio.

        Args:
            webhook_data: Raw webhook data from Twilio
        """
        try:
            logger.info(f"Processing webhook event: {webhook_data.get('eventType', 'unknown')}")

            # Pass webhook to TAF SMS channel for processing
            # This will:
            # 1. Parse the webhook event
            # 2. Manage conversation lifecycle
            # 3. Retrieve memories and trigger on_memory_ready callback
            self.sms_channel.process_webhook(webhook_data)

        except Exception as e:
            logger.error(f"Error processing webhook: {e}", exc_info=True)
            raise

    async def _handle_memory_ready(
        self,
        context: ConversationSession,
        memory_response: MemoryRetrievalResponse,
        user_message: str,
    ) -> None:
        """
        Callback invoked when TAF memory retrieval completes.

        This is where we:
        1. Receive the conversation context, memories, and user message from TAF
        2. Process the user message with LLM using memory context
        3. Send the response back through SMS channel

        Args:
            context: Conversation session context from TAF
            memory_response: Retrieved memory response with observations, summaries, and sessions
            user_message: The user's message that triggered memory retrieval
        """
        try:
            logger.info(
                f"Memory ready for conversation {context.conversation_id} "
                f"(profile: {context.profile_id}, channel: {context.channel})"
            )
            logger.info(f"User message: {user_message}")
            logger.info(f"Retrieved {len(memory_response.observations)} observations")
            logger.info(f"Retrieved {len(memory_response.summaries)} summaries")
            logger.info(f"Retrieved {len(memory_response.sessions)} sessions")

            # Log memory details for debugging
            logger.debug("Memory breakdown:")
            for obs in memory_response.observations:
                logger.debug(f"  Observation: {obs.content[:50]}...")
            for summary in memory_response.summaries:
                logger.debug(f"  Summary: {summary.content[:50]}...")
            for session in memory_response.sessions:
                logger.debug(f"  Session: {len(session.messages)} messages")

            # Process with LLM using memories
            llm_response = await self.llm_service.process_message(
                user_message=user_message,
                memory_response=memory_response,
                profile_id=context.profile_id,
            )

            logger.info(f"Generated LLM response: {llm_response[:100]}...")

            # Send response through SMS channel
            self.sms_channel.send_response(context.conversation_id, llm_response)

        except Exception as e:
            logger.error(f"Error handling memory ready callback: {e}", exc_info=True)


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
logger.info("TAF initialized successfully")

# Initialize LLM service
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

if not openai_api_key:
    logger.warning("OPENAI_API_KEY not found in environment. LLM service will not be available.")
    llm_service = None
else:
    llm_service = LLMService(api_key=openai_api_key, model=openai_model)
    logger.info(f"LLM service initialized with model: {openai_model}")

# Initialize webhook handler
if llm_service:
    webhook_handler = TAFWebhookHandler(taf=taf, llm_service=llm_service)
    logger.info("Webhook handler initialized")
else:
    webhook_handler = None
    logger.warning("Webhook handler not initialized - LLM service is not available")


@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {"service": "TAF SMS Demo", "status": "running", "version": "1.0.0"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "taf_configured": True, "llm_configured": llm_service is not None}


@app.post("/webhook/sms")
async def sms_webhook(request: Request):
    """
    Webhook endpoint for Twilio SMS events.

    This endpoint:
    1. Receives webhook events from Twilio
    2. Passes them to TAF for processing
    3. TAF handles memory retrieval and conversation management
    4. Returns success response to Twilio
    """
    if not webhook_handler:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "message": "Webhook handler not available - check LLM configuration",
            },
        )

    try:
        # Parse webhook data
        webhook_data = await request.json()

        logger.info(
            f"Received webhook: {webhook_data.get('eventType', 'unknown')} "
            f"for conversation {webhook_data.get('conversationId', 'unknown')}"
        )

        # Process through TAF webhook handler
        webhook_handler.process_webhook(webhook_data)

        return JSONResponse(
            status_code=200, content={"status": "success", "message": "Webhook processed"}
        )

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("=" * 60)
    logger.info("TAF SMS Demo Application Starting")
    logger.info("=" * 60)
    logger.info(f"Memory Service SID: {os.getenv('MEMORY_SERVICE_SID')}")
    logger.info(f"Conversation Service SID: {os.getenv('CONVERSATION_SERVICE_SID')}")
    logger.info(f"OpenAI Model: {openai_model}")
    logger.info(f"Log Level: {os.getenv('LOG_LEVEL', 'INFO')}")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("TAF SMS Demo Application Shutting Down")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8001"))
    debug = os.getenv("DEBUG", "false").lower() == "true"

    logger.info(f"Starting server on port {port}")
    logger.info(f"Debug mode: {debug}")

    uvicorn.run("exec_demo_sms:app", host="0.0.0.0", port=port, reload=debug)
