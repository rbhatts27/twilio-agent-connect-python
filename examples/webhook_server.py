#!/usr/bin/env python3
"""
Webhook Test Server for Twilio Agentic Framework

A simple HTTP server to receive and test Twilio webhook events with TAF.
Demonstrates SMS channel integration with memory retrieval.
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path to import taf
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from taf import TAF, TAFConfig, get_logger
from taf.channels.sms import SMSChannel
from taf.context.memory import TwilioMemory
from taf.core.context import ConversationSession


class WebhookHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Twilio webhooks."""

    def __init__(self, *args, taf_instance: TAF, sms_channel: SMSChannel, **kwargs):
        self.taf = taf_instance
        self.sms_channel = sms_channel
        self.logger = get_logger(__name__)
        super().__init__(*args, **kwargs)

    def do_POST(self):
        """Handle POST requests from Twilio webhooks."""
        try:
            # Get content length
            content_length = int(self.headers.get("Content-Length", 0))

            # Read the webhook payload
            post_data = self.rfile.read(content_length).decode("utf-8")

            # Parse JSON data (expected format)
            try:
                webhook_data = json.loads(post_data)
            except json.JSONDecodeError:
                self.send_error(400, "Invalid JSON")
                return

            try:
                # Process webhook through SMS channel
                self.sms_channel.process_webhook(webhook_data)

                # Send success response
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok"}).encode())
                self.logger.info("Successfully processed webhook")

            except Exception as e:
                self.logger.error(f"Error processing webhook: {str(e)}")

                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())

        except Exception as e:
            self.logger.error(f"Server error processing request: {str(e)}")
            self.send_error(500, str(e))

    def log_message(self, fmt, *args):
        """Override to suppress HTTP request logging."""
        pass


def create_handler(taf_instance, sms_channel):
    """Create handler class with TAF and SMS channel instances."""

    def handler(*args, **kwargs):
        return WebhookHandler(*args, taf_instance=taf_instance, sms_channel=sms_channel, **kwargs)

    return handler


def handle_memory_ready(
    context: ConversationSession, memories: list[TwilioMemory], user_message: str
):
    """
    Callback invoked when memory retrieval completes.

    This demonstrates how to process memories and respond to messages.
    In a production app, you would call your LLM here.

    Args:
        context: Conversation session context
        memories: Retrieved memories (traits, observations, sessions)
        user_message: The user's message that triggered memory retrieval
    """
    logger = get_logger(__name__)

    logger.info(
        f"Memory ready for conversation {context.conversation_id} on channel {context.channel}"
    )
    logger.info(f"Profile ID: {context.profile_id}")
    logger.info(f"User message: {user_message}")
    logger.info(f"Retrieved {len(memories)} memories")

    # Log memory details
    for memory in memories:
        if memory.mem_type == "TRAIT":
            logger.info(f"  - Trait: {memory.name} = {memory.value}")
        elif memory.mem_type == "OBSERVATION":
            logger.info(f"  - Observation: {memory.content}")
        elif memory.mem_type == "SESSION":
            logger.info(f"  - Session memory: {memory.content}")

    # TODO: In production, call your LLM with the memories, context, and user_message
    # Example:
    # llm_response = call_your_llm(user_message, memories)
    # sms_channel.send_response(context.conversation_id, llm_response)


def main():
    """Run the webhook test server."""
    logger = get_logger(__name__)

    # Initialize TAF with environment variables
    taf = TAF(
        config=TAFConfig(
            memora_base_url=os.getenv("MEMORA_BASE_URL"),
            memory_service_sid=os.getenv("MEMORY_SERVICE_SID"),
            maestro_base_url=os.getenv("MAESTRO_BASE_URL"),
            conversation_service_sid=os.getenv("CONVERSATION_SERVICE_SID"),
            twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
            twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
        )
    )

    # Register memory ready callback
    taf.on_memory_ready(handle_memory_ready)

    # Initialize SMS channel
    sms_channel = SMSChannel(taf)

    logger.info("Twilio Agentic Framework - SMS Webhook Server")
    logger.info(f"Memory Service SID: {os.getenv('MEMORY_SERVICE_SID')}")
    logger.info(f"Conversation Service SID: {os.getenv('CONVERSATION_SERVICE_SID')}")

    handler_class = create_handler(taf, sms_channel)

    try:
        server = HTTPServer(("localhost", 8000), handler_class)

        logger.info("Server listening on http://localhost:8000")
        logger.info("Ready to receive Twilio SMS webhooks! Press Ctrl+C to stop")

        server.serve_forever()

    except KeyboardInterrupt:
        logger.info("\nServer stopped")
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
