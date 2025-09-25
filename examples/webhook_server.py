#!/usr/bin/env python3
"""
Webhook Test Server for Twilio Agentic Framework

A simple HTTP server to receive and test Twilio webhook events with TAF.
Uses only Python built-in libraries - no external dependencies required.
"""

import json
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from taf.core.context import SessionIdentity

# Add parent directory to path to import taf
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from taf.core import TAF, TAFConfig


class WebhookHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Twilio webhooks."""

    def __init__(self, *args, taf_instance: TAF = None, **kwargs):
        self.taf = taf_instance
        super().__init__(*args, **kwargs)

    def do_POST(self):
        """Handle POST requests from Twilio webhooks."""
        try:
            # Get content length
            content_length = int(self.headers.get("Content-Length", 0))

            # Read the webhook payload
            post_data = self.rfile.read(content_length).decode("utf-8")

            # Parse URL-encoded data (standard Twilio webhook format)
            content_type = self.headers.get("Content-Type", "")
            if content_type.startswith("application/x-www-form-urlencoded"):
                parsed_data = urllib.parse.parse_qs(post_data)
                # Convert from lists to single values
                webhook_data = {k: v[0] if v else "" for k, v in parsed_data.items()}
            else:
                # TODO: Use channels to parse webhook data
                try:
                    webhook_data = json.loads(post_data)
                except json.JSONDecodeError:
                    self.send_error(400, "Invalid JSON or form data")
                    return

            # Log essential webhook info
            body = webhook_data.get("Body", "")

            try:
                print("🔄 Step 1: Resolving identity with Maestro...")
                # 1. get identity from webhook data with maestro
                identity = self.taf.resolve_identity(
                    event_data=webhook_data,
                    profile_id="mem_profile_00000000000000000000000001",
                )
                print(
                    f"✅ Maestro resolved identity: profile_id={identity.profile_id}, conversation_id={identity.conversation_id}"
                )

                print("🔄 Step 2: Building context with Memora...")
                # 2. build context from identity with memora
                context = self.taf.build_context(
                    service_id="mem_service_00000000000000000000000000",
                    identity=SessionIdentity(
                        profile_id=identity.profile_id,
                        conversation_id=identity.conversation_id,
                    ),
                    query=body,
                )
                print(
                    f"✅ Memora built context with {len(context) if isinstance(context, list) else 'N/A'} memories"
                )
                # TODO: 3. adapter to vendors
                # currently just return context

                response_data = context
                print("🎉 Successfully processed webhook with TAF")
                # Send success response
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode())

            except Exception as e:
                print(f"❌ TAF Error processing webhook: {str(e)}")

                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps({"status": "error", "message": str(e)}).encode()
                )

        except Exception as e:
            print(f"❌ Server error processing request: {str(e)}")
            self.send_error(500, str(e))

    def log_message(self, fmt, *args):
        """Override to suppress HTTP request logging."""
        pass


def create_handler(taf_instance):
    """Create handler class with TAF instance."""

    def handler(*args, **kwargs):
        return WebhookHandler(*args, taf_instance=taf_instance, **kwargs)

    return handler


def main():
    """Run the webhook test server."""
    import argparse

    parser = argparse.ArgumentParser(description="Twilio Webhook Test Server")
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to run server on (default: 8000)"
    )
    args = parser.parse_args()

    # Initialize TAF with environment variables
    taf = TAF(
        config=TAFConfig(
            memora_base_url=os.getenv("MEMORA_BASE_URL"),
            memora_auth_token=os.getenv("MEMORA_AUTH_TOKEN"),
            maestro_base_url=os.getenv("MAESTRO_BASE_URL"),
            twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
        )
    )

    print("🚀 Twilio Agentic Framework - Webhook Server")
    print(f"Starting on: http://localhost:{args.port}")

    handler_class = create_handler(taf)

    try:
        server = HTTPServer(("localhost", args.port), handler_class)

        print("📨 Ready to receive webhooks! Press Ctrl+C to stop")

        server.serve_forever()

    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
