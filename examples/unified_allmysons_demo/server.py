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
import json
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
from tac.models.conversation import ParticipantAddress
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
voice_channel = VoiceChannel(tac)
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
            return JSONResponse(
                content={"error": "anchor_id is required"}, status_code=400
            )

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
            # Extract message body and media for dashboard
            message_body = webhook_data.get("Body", "")
            conversation_id = webhook_data.get("ConversationSid", "")

            # Extract media attachments if present
            num_media = int(webhook_data.get("NumMedia", 0))
            media_urls = []
            for i in range(num_media):
                media_url = webhook_data.get(f"MediaUrl{i}", "")
                media_type = webhook_data.get(f"MediaContentType{i}", "image/jpeg")
                if media_url:
                    media_urls.append({
                        "url": media_url,
                        "content_type": media_type,
                        "filename": f"attachment_{i + 1}",
                    })

            # Push enhanced SMS event to dashboard
            if message_body or media_urls:
                push_sms_event(
                    conversation_id=conversation_id,
                    from_number=from_number or "",
                    sms_body=message_body,
                    media_urls=media_urls if media_urls else None,
                    profile_id=webhook_data.get("profile_id")
                    or webhook_data.get("ProfileId"),
                )

            # Check cross-channel linking for active anchor
            anchor = get_active_anchor()
            if from_number:
                existing_conv = anchor.get_conversation_for_phone(from_number)
                if existing_conv and existing_conv in anchor.active_voice_calls:
                    logger.info(
                        f"CONCURRENT SMS | Message from {from_number} "
                        f"linked to active voice call",
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
            return JSONResponse(
                content={"error": "Memora not configured"}, status_code=400
            )

        # Get profile with traits
        profile = await tac.memora_client.get_profile(
            profile_id=profile_id,
            trait_groups=["Contact", "Preferences", "Demographics"],
        )

        return JSONResponse(content={
            "id": profile.id,
            "created_at": profile.created_at,
            "traits": profile.traits,
        })

    except Exception as e:
        logger.error(f"Error fetching profile: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/profile/{profile_id}/memory")
async def get_profile_memory(profile_id: str, query: Optional[str] = None) -> JSONResponse:
    """Fetch profile memory including observations and summaries from Memora."""
    try:
        if not tac.memora_client:
            return JSONResponse(
                content={"error": "Memora not configured"}, status_code=400
            )

        # Get memory (observations, summaries, sessions)
        memory = await tac.memora_client.retrieve_memory(
            profile_id=profile_id,
            query=query,
        )

        return JSONResponse(content={
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
        })

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
        participants = await tac.maestro_client.list_participants(
            conversation_id=conversation_id
        )

        return JSONResponse(content={
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
        })

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
                status_code=400
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
        return JSONResponse(content={
            "success": True,
            "call_sid": call.sid,
            "status": call.status,
            "from": maria_number,
            "to": support_number,
        })

    except Exception as e:
        logger.error(f"Error initiating Maria call: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/api/maria/sms")
async def trigger_maria_sms(request: Request) -> JSONResponse:
    """Trigger Maria to send an SMS with a photo."""
    try:
        from twilio.rest import Client as TwilioClient

        # Get photo type from request body
        body = await request.json() if request.headers.get("content-type") == "application/json" else {}
        photo_type = body.get("photo_type", "living room")

        maria_number = os.environ.get("TWILIO_TAC_MARIA_NUMBER", "")
        support_number = os.environ.get("TWILIO_TAC_PHONE_NUMBER", "")

        if not maria_number:
            return JSONResponse(
                content={"error": "TWILIO_TAC_MARIA_NUMBER not configured"},
                status_code=400
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
        return JSONResponse(content={
            "success": True,
            "message_sid": msg.sid,
            "status": msg.status,
            "photo_type": photo_type,
        })

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
    Creates a conversation and connects to voice handling.
    """
    public_domain = os.environ.get("TWILIO_TAC_VOICE_PUBLIC_DOMAIN", "")
    websocket_url = f"wss://{public_domain}/ws"

    # Get CallSid from Twilio's request
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "unknown")
    from_number = form_data.get("From", "")
    to_number = form_data.get("To", "")

    logger.info(f"MARIA TWIML | Creating conversation for Maria's call [call_sid={call_sid}]")

    try:
        # Create a conversation for Maria's call
        conversation = await tac.maestro_client.create_conversation(
            name=f"Maria Demo Call {str(call_sid)[:10]}"
        )
        conversation_id = conversation.id

        # Add customer participant (Maria)
        customer = await tac.maestro_client.add_participant(
            conversation_id=conversation_id,
            participant_type="CUSTOMER",
            addresses=[ParticipantAddress(channel="VOICE", address=str(from_number))],
        )

        # Lookup profile by phone number
        profile_id = ""
        if tac.memora_client:
            try:
                lookup_result = await tac.memora_client.lookup_profile(
                    id_type="phone", value=str(from_number)
                )
                if lookup_result.profiles:
                    profile_id = lookup_result.profiles[0]
                    logger.info(f"MARIA TWIML | Found profile {profile_id} for {from_number}")
            except Exception as e:
                logger.warning(f"MARIA TWIML | Profile lookup failed: {e}")

        # Add AI agent participant
        ai_agent = await tac.maestro_client.add_participant(
            conversation_id=conversation_id,
            participant_type="AI_AGENT",
        )

        # Track this as an active voice call for cross-channel
        anchor = get_active_anchor()
        anchor.active_voice_calls[conversation_id] = True
        anchor.link_phone_to_conversation(str(from_number), conversation_id)

        logger.info(f"MARIA TWIML | Conversation created [conversation_id={conversation_id}, profile_id={profile_id}]")

        # Generate TwiML with conversation parameters
        twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <ConversationRelay url="{websocket_url}" voice="Google.en-US-Standard-C" welcomeGreeting="Hello! Thank you for calling All My Sons Moving and Storage. I'm your AI assistant. How can I help you today?">
            <Parameter name="conversationId" value="{conversation_id}" />
            <Parameter name="profileId" value="{profile_id}" />
            <Parameter name="customerParticipantId" value="{customer.id}" />
            <Parameter name="aiAgentParticipantId" value="{ai_agent.id}" />
            <Parameter name="isMariaAgent" value="true" />
        </ConversationRelay>
    </Connect>
</Response>'''

        return Response(content=twiml, media_type="application/xml")

    except Exception as e:
        logger.error(f"MARIA TWIML | Error creating conversation: {e}", exc_info=True)
        # Fallback to simple TTS if conversation creation fails
        twiml = '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">
        Sorry, there was an error setting up the call. Please try again.
    </Say>
</Response>'''
        return Response(content=twiml, media_type="application/xml")


# =============================================================================
# Health Check
# =============================================================================


@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint."""
    anchor = get_active_anchor()
    return JSONResponse({
        "status": "healthy",
        "demo": "Unified All My Sons Demo",
        "active_anchor": anchor.anchor_id,
        "active_anchor_name": anchor.name,
        "channels": ["voice", "sms"],
        "active_voice_calls": len(
            [c for c, active in anchor.active_voice_calls.items() if active]
        ),
    })


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
