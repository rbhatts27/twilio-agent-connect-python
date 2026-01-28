"""
Unified All My Sons Demo Server

Single server running on port 8000 that supports all 6 anchor scenarios.
The dashboard provides a dropdown to select which anchor demo to run.
Switching anchors changes the AI agent behavior without restarting the server.

Architecture:
- Single FastAPI app handles SMS + Voice + Dashboard
- Active anchor is selected via API and controls message handling
- Dashboard streams events via SSE with enhanced SMS content display
"""

import asyncio
import os
import re
from pathlib import Path
from typing import Optional

import uvicorn
from anchors import ANCHOR_REGISTRY
from anchors.base import BaseAnchor
from dashboard.event_handler import (
    get_event_queue,
    push_anchor_event,
    push_demo_status,
    push_sms_event,
    setup_dashboard_logging,
)
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request, WebSocket
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from tac import TAC, TACConfig
from tac.channels import SMSChannel
from tac.channels.voice import VoiceChannel
from tac.core.logging import get_logger, setup_logging
from tac.models.memory import MemoryRetrievalResponse
from tac.models.session import ConversationSession

# Load environment from parent examples directory
load_dotenv(Path(__file__).parent.parent / ".env")

# Get the directory where this script is located
BASE_DIR = Path(__file__).resolve().parent

# Configure structured logging
setup_logging(log_level="INFO", log_format="console")
logger = get_logger(__name__)

app = FastAPI(
    title="Unified All My Sons Demo Server",
    description="Single server for all anchor scenarios with dashboard selection",
    version="1.0.0",
)

# Initialize TAC
tac = TAC(config=TACConfig.from_env())

# Setup dashboard logging AFTER TAC initialization
setup_dashboard_logging()

# Initialize channels
# Note: Disable auto memory retrieval for voice - we'll cache memory at call start
voice_channel = VoiceChannel(tac, auto_retrieve_memory=False)
sms_channel = SMSChannel(tac)

# =============================================================================
# Anchor Management
# =============================================================================

# Active anchor instance (default: anchor1)
active_anchor: Optional[BaseAnchor] = None


def get_active_anchor() -> BaseAnchor:
    """Get the currently active anchor, initializing anchor1 if needed."""
    global active_anchor
    if active_anchor is None:
        select_anchor("anchor1")
    return active_anchor  # type: ignore[return-value]


def select_anchor(anchor_id: str) -> BaseAnchor:
    """Select and initialize an anchor by ID."""
    global active_anchor

    if anchor_id not in ANCHOR_REGISTRY:
        raise ValueError(f"Unknown anchor: {anchor_id}. Available: {list(ANCHOR_REGISTRY.keys())}")

    anchor_class = ANCHOR_REGISTRY[anchor_id]
    active_anchor = anchor_class(
        tac=tac,
        sms_channel=sms_channel,
        voice_channel=voice_channel,
    )

    logger.info(f"ANCHOR SELECTED | {active_anchor.name} ({anchor_id})")
    push_anchor_event(anchor_id, active_anchor.name)

    return active_anchor


# Initialize default anchor
select_anchor("anchor1")


# =============================================================================
# Message Handler (Delegates to active anchor)
# =============================================================================


async def handle_message_ready(
    user_message: str,
    context: ConversationSession,
    memory_response: Optional[MemoryRetrievalResponse],
    incoming_channel: str = None,
) -> None:
    """Unified callback that delegates to the active anchor's handler."""
    anchor = get_active_anchor()
    await anchor.handle_message(
        user_message=user_message,
        context=context,
        memory_response=memory_response,
        incoming_channel=incoming_channel,
    )


# Register the message callback with TAC
tac.on_message_ready(handle_message_ready)


# =============================================================================
# Anchor Selection API
# =============================================================================


@app.get("/api/anchors")
async def list_anchors() -> JSONResponse:
    """List all available anchor scenarios."""
    anchors = []
    for anchor_id, anchor_class in ANCHOR_REGISTRY.items():
        # Create a temporary instance to get scenario info
        temp = anchor_class(tac=tac, sms_channel=sms_channel, voice_channel=voice_channel)
        anchors.append(temp.get_scenario_info())
    return JSONResponse(content={"anchors": anchors})


@app.get("/api/active-anchor")
async def get_active_anchor_info() -> JSONResponse:
    """Get the currently active anchor."""
    anchor = get_active_anchor()
    return JSONResponse(content=anchor.get_scenario_info())


@app.post("/api/select-anchor")
async def select_anchor_endpoint(request: Request) -> JSONResponse:
    """Select a new active anchor scenario."""
    try:
        body = await request.json()
        anchor_id = body.get("anchor_id")

        if not anchor_id:
            return JSONResponse(content={"error": "anchor_id is required"}, status_code=400)

        anchor = select_anchor(anchor_id)
        return JSONResponse(content=anchor.get_scenario_info())

    except ValueError as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Error selecting anchor", error=str(e), exc_info=True)
        return JSONResponse(content={"error": str(e)}, status_code=500)


# =============================================================================
# SMS Webhook Endpoints
# =============================================================================


@app.post("/webhook")
async def webhook_handler(request: Request) -> JSONResponse:
    """Handle incoming SMS webhooks from Twilio."""
    try:
        form_data = await request.json()
        webhook_data = dict(form_data)

        # Extract idempotency token for deduplication
        idempotency_token = request.headers.get("i-twilio-idempotency-token")

        # Extract SMS details for enhanced dashboard display
        event_type = webhook_data.get("EventType")
        from_number = webhook_data.get("From") or webhook_data.get("from_address")

        if event_type == "onMessageAdded":
            # DEBUG: Log full webhook payload to understand media format
            logger.info(f"SMS WEBHOOK DEBUG | Full payload keys: {list(webhook_data.keys())}")
            if "data" in webhook_data:
                data_obj = webhook_data.get("data", {})
                logger.info(
                    f"SMS WEBHOOK DEBUG | data keys: {list(data_obj.keys()) if isinstance(data_obj, dict) else type(data_obj)}"
                )
                if isinstance(data_obj, dict) and "content" in data_obj:
                    content_obj = data_obj.get("content", {})
                    logger.info(
                        f"SMS WEBHOOK DEBUG | content keys: {list(content_obj.keys()) if isinstance(content_obj, dict) else type(content_obj)}"
                    )

            # Extract message body and media for dashboard
            message_body = webhook_data.get("Body", "")
            conversation_id = webhook_data.get("ConversationSid", "")

            # Extract media attachments - check multiple possible formats
            media_urls = []

            # Format 1: Standard Twilio SMS format (NumMedia, MediaUrl0, etc.)
            num_media = int(webhook_data.get("NumMedia", 0))
            for i in range(num_media):
                media_url = webhook_data.get(f"MediaUrl{i}", "")
                media_type = webhook_data.get(f"MediaContentType{i}", "image/jpeg")
                if media_url:
                    media_urls.append(
                        {
                            "url": media_url,
                            "content_type": media_type,
                            "filename": f"image_{i + 1}.jpg",
                        }
                    )

            # Format 2: Maestro top-level media array
            if not media_urls and "media" in webhook_data:
                media_list = webhook_data.get("media", [])
                if isinstance(media_list, list):
                    for i, media in enumerate(media_list):
                        if isinstance(media, dict):
                            media_urls.append(
                                {
                                    "url": media.get("url", media.get("contentUrl", "")),
                                    "content_type": media.get("contentType", "image/jpeg"),
                                    "filename": media.get("filename", f"image_{i + 1}.jpg"),
                                }
                            )

            # Format 3: Maestro nested in data.content.media
            if not media_urls and "data" in webhook_data:
                data_obj = webhook_data.get("data", {})
                if isinstance(data_obj, dict):
                    content_obj = data_obj.get("content", {})
                    if isinstance(content_obj, dict) and "media" in content_obj:
                        media_list = content_obj.get("media", [])
                        if isinstance(media_list, list):
                            for i, media in enumerate(media_list):
                                if isinstance(media, dict):
                                    media_urls.append(
                                        {
                                            "url": media.get("url", media.get("contentUrl", "")),
                                            "content_type": media.get(
                                                "contentType",
                                                media.get("content_type", "image/jpeg"),
                                            ),
                                            "filename": media.get("filename", f"image_{i + 1}.jpg"),
                                        }
                                    )

            # Format 4: Maestro nested in data.media
            if not media_urls and "data" in webhook_data:
                data_obj = webhook_data.get("data", {})
                if isinstance(data_obj, dict) and "media" in data_obj:
                    media_list = data_obj.get("media", [])
                    if isinstance(media_list, list):
                        for i, media in enumerate(media_list):
                            if isinstance(media, dict):
                                media_urls.append(
                                    {
                                        "url": media.get("url", media.get("contentUrl", "")),
                                        "content_type": media.get(
                                            "contentType", media.get("content_type", "image/jpeg")
                                        ),
                                        "filename": media.get("filename", f"image_{i + 1}.jpg"),
                                    }
                                )

            logger.info(
                f"SMS webhook: body={message_body[:50] if message_body else 'empty'}, media_count={len(media_urls)}"
            )

            # Push enhanced SMS event to dashboard
            if message_body or media_urls:
                push_sms_event(
                    conversation_id=conversation_id,
                    from_number=from_number or "",
                    sms_body=message_body,
                    media_urls=media_urls if media_urls else None,
                    profile_id=webhook_data.get("profile_id") or webhook_data.get("ProfileId"),
                )

            # Check cross-channel linking for active anchor
            anchor = get_active_anchor()
            if from_number:
                existing_conv = anchor.get_conversation_for_phone(from_number)
                if existing_conv and existing_conv in anchor.active_voice_calls:
                    logger.info(
                        f"CONCURRENT SMS | Message from {from_number} linked to active voice call",
                        conversation_id=existing_conv,
                    )

        # Fire and forget - process webhook asynchronously
        asyncio.create_task(sms_channel.process_webhook(webhook_data, idempotency_token))

        return JSONResponse(content={"status": "ok"}, status_code=200)

    except Exception as e:
        logger.error("SMS webhook error", error=str(e), exc_info=True)
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=400)


# =============================================================================
# Voice Endpoints
# =============================================================================


@app.post("/twiml")
async def post_twiml(
    from_number: str = Form(..., alias="From"),
    to_number: str = Form(..., alias="To"),
    call_sid: str = Form(..., alias="CallSid"),
) -> Response:
    """Generate TwiML for incoming voice calls."""
    logger.info(
        f"\n{'=' * 80}\nINCOMING CALL | {from_number} -> {to_number}",
        call_sid=call_sid,
    )

    # Get WebSocket URL from environment
    public_domain = os.environ.get("TWILIO_TAC_VOICE_PUBLIC_DOMAIN", "")
    websocket_url = f"wss://{public_domain}/ws"
    callback_url = f"https://{public_domain}/conversation-relay-callback"

    # Generate TwiML with conversation and participant setup
    twiml = await voice_channel.handle_incoming_call(
        websocket_url=websocket_url,
        to_number=to_number,
        from_number=from_number,
        call_sid=call_sid,
        action_url=callback_url,
    )

    # Extract conversation ID from TwiML to link phone number
    conv_match = re.search(r'name="conversationId" value="([^"]+)"', twiml)
    if conv_match:
        conversation_id = conv_match.group(1)
        anchor = get_active_anchor()
        anchor.link_phone_to_conversation(from_number, conversation_id)
        anchor.active_voice_calls[conversation_id] = True
        logger.info(
            f"VOICE ACTIVE | Cross-channel enabled for {from_number}",
            conversation_id=conversation_id,
        )

    logger.info("CALL SETUP | TwiML generated, WebSocket connecting...", call_sid=call_sid)
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle voice streaming WebSocket connection."""
    logger.info("WEBSOCKET | Connected - voice streaming ready")
    await voice_channel.handle_websocket(websocket)
    logger.info("WEBSOCKET | Disconnected")


@app.post("/conversation-relay-callback")
async def conversation_relay_callback(request: Request) -> Response:
    """Handle ConversationRelay callback webhook from Twilio."""
    response = await voice_channel.handle_conversation_relay_callback(request)

    # Clean up active voice calls
    anchor = get_active_anchor()
    for conv_id in list(anchor.active_voice_calls.keys()):
        if conv_id not in voice_channel._conversations:
            if anchor.active_voice_calls.get(conv_id):
                anchor.active_voice_calls[conv_id] = False
                logger.info(
                    "VOICE ENDED | Cross-channel disabled",
                    conversation_id=conv_id,
                )

    return response


# =============================================================================
# Dashboard Routes
# =============================================================================

# Mount static files
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "dashboard" / "static")),
    name="static",
)


@app.get("/dashboard")
async def dashboard_page() -> FileResponse:
    """Serve the dashboard HTML page."""
    return FileResponse(
        BASE_DIR / "dashboard" / "templates" / "dashboard.html",
        media_type="text/html",
    )


@app.get("/")
async def root() -> FileResponse:
    """Redirect root to dashboard."""
    return FileResponse(
        BASE_DIR / "dashboard" / "templates" / "dashboard.html",
        media_type="text/html",
    )


@app.get("/events")
async def event_stream(request: Request) -> StreamingResponse:
    """SSE endpoint for streaming dashboard events."""

    async def event_generator():
        queue = get_event_queue()
        try:
            while True:
                if queue:
                    event = queue.popleft()
                    yield f"data: {event.model_dump_json()}\n\n"
                else:
                    yield ": keepalive\n\n"
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            logger.info("Dashboard client disconnected")
            raise

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# =============================================================================
# Profile & Conversation Data APIs (for Dashboard)
# =============================================================================


@app.get("/api/profile/{profile_id}")
async def get_profile_data(profile_id: str) -> JSONResponse:
    """Fetch profile data including traits from Memora."""
    try:
        if not tac.memora_client:
            return JSONResponse(content={"error": "Memora not configured"}, status_code=400)

        # Get profile with traits
        profile = await tac.memora_client.get_profile(
            profile_id=profile_id,
            trait_groups=["Contact", "Preferences", "Demographics"],
        )

        return JSONResponse(
            content={
                "id": profile.id,
                "created_at": profile.created_at,
                "traits": profile.traits,
            }
        )

    except Exception as e:
        logger.error(f"Error fetching profile: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/profile/{profile_id}/memory")
async def get_profile_memory(profile_id: str, query: Optional[str] = None) -> JSONResponse:
    """Fetch profile memory including observations and summaries from Memora."""
    try:
        if not tac.memora_client:
            return JSONResponse(content={"error": "Memora not configured"}, status_code=400)

        # Get memory (observations, summaries, sessions)
        memory = await tac.memora_client.retrieve_memory(
            profile_id=profile_id,
            query=query,
        )

        return JSONResponse(
            content={
                "observations": [
                    {
                        "id": obs.id,
                        "content": obs.content,
                        "created_at": obs.created_at,
                        "source": obs.source,
                    }
                    for obs in (memory.observations or [])
                ],
                "summaries": [
                    {
                        "id": s.id,
                        "content": s.content,
                        "created_at": s.created_at,
                    }
                    for s in (memory.summaries or [])
                ],
                "communications": [
                    {
                        "id": comm.id,
                        "content": comm.content.text if comm.content else None,
                        "created_at": comm.created_at,
                        "channel": comm.author.channel if comm.author else None,
                    }
                    for comm in (memory.communications or [])
                ],
            }
        )

    except Exception as e:
        logger.error(f"Error fetching profile memory: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/conversation/{conversation_id}")
async def get_conversation_data(conversation_id: str) -> JSONResponse:
    """Fetch conversation data and communications from Maestro."""
    try:
        # Get communications for this conversation
        communications = await tac.maestro_client.list_communications(
            conversation_id=conversation_id,
            page_size=50,
        )

        # Get participants
        participants = await tac.maestro_client.list_participants(conversation_id=conversation_id)

        return JSONResponse(
            content={
                "conversation_id": conversation_id,
                "participants": [
                    {
                        "id": p.id,
                        "type": p.type,
                        "addresses": [
                            {"channel": a.channel, "address": a.address}
                            for a in (p.addresses or [])
                        ],
                    }
                    for p in participants
                ],
                "communications": [
                    {
                        "id": comm.id,
                        "content": comm.content.text if comm.content else None,
                        "author_id": comm.author.participant_id if comm.author else None,
                        "author_address": comm.author.address if comm.author else None,
                        "created_at": comm.created_at,
                        "channel": comm.author.channel if comm.author else None,
                    }
                    for comm in communications
                ],
            }
        )

    except Exception as e:
        logger.error(f"Error fetching conversation: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e)}, status_code=500)


# =============================================================================
# Maria Agent API Endpoints (for Dashboard buttons)
# =============================================================================


@app.post("/api/maria/call")
async def trigger_maria_call() -> JSONResponse:
    """Trigger Maria to call the support line."""
    try:
        from twilio.rest import Client as TwilioClient

        maria_number = os.environ.get("TWILIO_TAC_MARIA_NUMBER", "")
        support_number = os.environ.get("TWILIO_TAC_PHONE_NUMBER", "")
        public_domain = os.environ.get("TWILIO_TAC_VOICE_PUBLIC_DOMAIN", "")

        if not maria_number:
            return JSONResponse(
                content={"error": "TWILIO_TAC_MARIA_NUMBER not configured. Add it to .env"},
                status_code=400,
            )

        twilio_client = TwilioClient(
            os.environ.get("TWILIO_TAC_ACCOUNT_SID"),
            os.environ.get("TWILIO_TAC_AUTH_TOKEN"),
        )

        # Use TwiML URL for ConversationRelay connection
        if public_domain:
            call = twilio_client.calls.create(
                to=support_number,
                from_=maria_number,
                url=f"https://{public_domain}/maria-twiml",
            )
        else:
            # Fallback to simple TTS
            call = twilio_client.calls.create(
                to=support_number,
                from_=maria_number,
                twiml="""
                <Response>
                    <Say voice="Polly.Joanna">
                        Hi, this is Maria Ramirez. I'm calling to get a quote for a move
                        from Austin to Denver. We have a 3 bedroom house and some special
                        items including a baby grand piano.
                    </Say>
                    <Pause length="60"/>
                </Response>
                """,
            )

        logger.info(f"Maria call initiated: {call.sid}")
        return JSONResponse(
            content={
                "success": True,
                "call_sid": call.sid,
                "status": call.status,
                "from": maria_number,
                "to": support_number,
            }
        )

    except Exception as e:
        logger.error(f"Error initiating Maria call: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/api/maria/sms")
async def trigger_maria_sms(request: Request) -> JSONResponse:
    """Trigger Maria to send an SMS with a photo."""
    try:
        from twilio.rest import Client as TwilioClient

        # Get photo type from request body
        body = (
            await request.json()
            if request.headers.get("content-type") == "application/json"
            else {}
        )
        photo_type = body.get("photo_type", "living room")

        maria_number = os.environ.get("TWILIO_TAC_MARIA_NUMBER", "")
        support_number = os.environ.get("TWILIO_TAC_PHONE_NUMBER", "")

        if not maria_number:
            return JSONResponse(
                content={"error": "TWILIO_TAC_MARIA_NUMBER not configured"}, status_code=400
            )

        # Sample images
        sample_images = {
            "living room": "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=800",
            "bedroom": "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?w=800",
            "piano": "https://images.unsplash.com/photo-1520523839897-bd0b52f945a0?w=800",
            "furniture": "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=800",
        }

        image_url = sample_images.get(photo_type, sample_images["living room"])
        message = f"Here's a photo of our {photo_type}. This should help with the estimate!"

        twilio_client = TwilioClient(
            os.environ.get("TWILIO_TAC_ACCOUNT_SID"),
            os.environ.get("TWILIO_TAC_AUTH_TOKEN"),
        )

        msg = twilio_client.messages.create(
            to=support_number,
            from_=maria_number,
            body=message,
            media_url=[image_url],
        )

        logger.info(f"Maria SMS sent: {msg.sid}")

        # Push SMS event directly to dashboard with media
        push_sms_event(
            conversation_id="maria_sms",
            from_number=maria_number,
            sms_body=message,
            media_urls=[
                {
                    "url": image_url,
                    "content_type": "image/jpeg",
                    "filename": f"{photo_type.replace(' ', '_')}.jpg",
                }
            ],
            profile_id=None,
        )

        return JSONResponse(
            content={
                "success": True,
                "message_sid": msg.sid,
                "status": msg.status,
                "photo_type": photo_type,
            }
        )

    except Exception as e:
        logger.error(f"Error sending Maria SMS: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


# =============================================================================
# Maria Agent TwiML Endpoint (for AI-to-AI demo)
# =============================================================================


@app.post("/maria-twiml")
async def maria_twiml(request: Request) -> Response:
    """
    TwiML endpoint for Maria's outbound calls.
    Maria is a scripted customer who speaks pre-defined lines.
    The support agent (on the receiving end) responds via ConversationRelay.
    """
    # Get CallSid from Twilio's request
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "unknown")

    logger.info(f"MARIA TWIML | Generating scripted customer dialogue [call_sid={call_sid}]")

    # Scripted conversation from Maria's perspective
    # Maria speaks, pauses to let agent respond, then continues
    # Timeline: SMS sent at ~18s, so Maria mentions photo at ~15s
    # Total script ~45 seconds for natural pacing
    twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Pause length="2"/>
    <Say voice="Polly.Joanna">
        Hi! I'm Maria Ramirez. I'm calling about a move from Austin to Denver.
    </Say>
    <Pause length="4"/>
    <Say voice="Polly.Joanna">
        We have a three bedroom house. I'm going to text you a photo of our living room right now.
    </Say>
    <Pause length="6"/>
    <Say voice="Polly.Joanna">
        We have a piano, about 500 pounds, and some antiques that need special care.
    </Say>
    <Pause length="5"/>
    <Say voice="Polly.Joanna">
        We're hoping to move next month. Can you give me a rough estimate?
    </Say>
    <Pause length="6"/>
    <Say voice="Polly.Joanna">
        That sounds reasonable. Thank you for your help!
    </Say>
    <Pause length="2"/>
    <Say voice="Polly.Joanna">
        Goodbye!
    </Say>
    <Hangup/>
</Response>"""

    return Response(content=twiml, media_type="application/xml")


# =============================================================================
# One-Click Demo Endpoint (Call + SMS sequence)
# =============================================================================


@app.post("/api/maria/demo")
async def run_demo() -> JSONResponse:
    """
    Run a complete demo: Maria calls, then sends SMS with photo after 8 seconds.
    The demo auto-ends after ~30 seconds.
    """
    try:
        from twilio.rest import Client as TwilioClient

        maria_number = os.environ.get("TWILIO_TAC_MARIA_NUMBER", "")
        support_number = os.environ.get("TWILIO_TAC_PHONE_NUMBER", "")
        public_domain = os.environ.get("TWILIO_TAC_VOICE_PUBLIC_DOMAIN", "")

        if not maria_number:
            return JSONResponse(
                content={"error": "TWILIO_TAC_MARIA_NUMBER not configured"}, status_code=400
            )

        push_demo_status("started", "🚀 Demo starting...", 0)

        twilio_client = TwilioClient(
            os.environ.get("TWILIO_TAC_ACCOUNT_SID"),
            os.environ.get("TWILIO_TAC_AUTH_TOKEN"),
        )

        # Step 1: Initiate the call
        push_demo_status("progress", "📞 Maria is calling support...", 10)

        call = twilio_client.calls.create(
            to=support_number,
            from_=maria_number,
            url=f"https://{public_domain}/maria-twiml",
            timeout=30,  # Auto-hangup after 30 seconds
        )

        logger.info(f"DEMO | Call initiated: {call.sid}")
        push_demo_status("progress", f"📞 Call connected (ID: {call.sid[:8]}...)", 30)

        # Step 2: Schedule SMS with photo when Maria mentions it (~16 seconds in)
        # Timeline: Maria says "I'm going to text you a photo" at ~12s, send at ~16s
        async def send_delayed_sms():
            await asyncio.sleep(16)
            push_demo_status("progress", "📱 Maria is sending a photo...", 60)

            # Sample house photo (living room with furniture)
            image_url = "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=800"
            # Note: Include specific items that the mock analyze_furniture_photo tool can recognize
            message = "Here's a photo of our living room! You can see the sofa, coffee table, bookshelf, and the antique cabinet I mentioned. The piano is in the next room."

            try:
                msg = twilio_client.messages.create(
                    to=support_number,
                    from_=maria_number,
                    body=message,
                    media_url=[image_url],
                )
                logger.info(f"DEMO | SMS sent: {msg.sid}")

                # Push SMS event directly to dashboard with media (workaround for Maestro webhook format)
                # This ensures the image thumbnail appears in the activity timeline immediately
                push_sms_event(
                    conversation_id="demo",  # Use "demo" as placeholder since we don't have Maestro conv ID
                    from_number=maria_number,
                    sms_body=message,
                    media_urls=[
                        {
                            "url": image_url,
                            "content_type": "image/jpeg",
                            "filename": "living_room.jpg",
                        }
                    ],
                    profile_id=None,
                )

                push_demo_status("progress", "📱 Photo sent! Waiting for call to complete...", 80)

                # Wait for call to finish (Maria's script is ~35 seconds total)
                await asyncio.sleep(20)
                push_demo_status("completed", "✅ Demo complete! Review the conversation.", 100)

            except Exception as e:
                logger.error(f"DEMO | SMS failed: {e}")
                push_demo_status("error", f"SMS failed: {str(e)}", 60)

        # Fire and forget the delayed SMS
        asyncio.create_task(send_delayed_sms())

        return JSONResponse(
            content={
                "success": True,
                "call_sid": call.sid,
                "message": "Demo started. Maria is calling and will send a photo in 8 seconds.",
            }
        )

    except Exception as e:
        logger.error(f"DEMO | Error: {e}")
        push_demo_status("error", f"Demo failed: {str(e)}", 0)
        return JSONResponse(content={"error": str(e)}, status_code=500)


# =============================================================================
# Health Check
# =============================================================================


@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint."""
    anchor = get_active_anchor()
    return JSONResponse(
        {
            "status": "healthy",
            "demo": "Unified All My Sons Demo",
            "active_anchor": anchor.anchor_id,
            "active_anchor_name": anchor.name,
            "channels": ["voice", "sms"],
            "active_voice_calls": len(
                [c for c, active in anchor.active_voice_calls.items() if active]
            ),
        }
    )


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Unified All My Sons Demo Server")
    print("All 6 Anchor Scenarios in One Place")
    print("=" * 60)
    print("\nEndpoints:")
    print("  Dashboard:       http://localhost:8000/dashboard")
    print("  SMS Webhook:     POST /webhook")
    print("  Voice TwiML:     POST /twiml")
    print("  Voice WS:        WS /ws")
    print("  Health:          GET /health")
    print("  List Anchors:    GET /api/anchors")
    print("  Active Anchor:   GET /api/active-anchor")
    print("  Select Anchor:   POST /api/select-anchor")
    print("\nData APIs (for Dashboard):")
    print("  Profile Data:    GET /api/profile/{profile_id}")
    print("  Profile Memory:  GET /api/profile/{profile_id}/memory")
    print("  Conversation:    GET /api/conversation/{conversation_id}")
    print("\nAvailable Anchors:")
    for aid, aclass in ANCHOR_REGISTRY.items():
        temp = aclass(tac=tac, sms_channel=sms_channel, voice_channel=voice_channel)
        print(f"  {aid}: {temp.name} - {temp.short_description}")
    print("\n🤖 Maria Agent (AI Consumer Simulation):")
    print("  python maria_agent.py --demo   # Run full demo scenario")
    print("  python maria_agent.py --call   # Initiate voice call")
    print("  python maria_agent.py --photo  # Send SMS with photo")
    print("=" * 60 + "\n")

    uvicorn_log_config = uvicorn.config.LOGGING_CONFIG
    uvicorn_log_config["formatters"]["default"]["fmt"] = "%(levelprefix)s %(message)s"
    uvicorn_log_config["formatters"]["access"]["fmt"] = (
        '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s'
    )

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        log_level="warning",
        access_log=False,
        log_config=uvicorn_log_config,
    )
