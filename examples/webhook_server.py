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
                # Try to parse as JSON
                try:
                    webhook_data = json.loads(post_data)
                except json.JSONDecodeError:
                    self.send_error(400, "Invalid JSON or form data")
                    return

            # Log essential webhook info
            event_type = webhook_data.get("EventType", "Unknown")
            body = webhook_data.get("Body", "")
            print(f"📨 {event_type}: '{body[:50]}{'...' if len(body) > 50 else ''}'")

            if self.taf:
                try:
                    # 1. get identity from webhook data
                    identity = self.taf.resolve_identity(webhook_data)
                    # 2. build context from identity
                    context = self.taf.build_context(identity)
                    # todo: 3. adapter to vendors
                    # currently just return context

                    response_data = context
                    # Send success response
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(response_data).encode())

                except Exception as e:
                    print(f"❌ Error: {str(e)}")

                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(
                        json.dumps({"status": "error", "message": str(e)}).encode()
                    )
            else:
                # No TAF instance, just echo the data
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps({"status": "received", "data": webhook_data}).encode()
                )

        except Exception as e:
            print(f"Server error: {str(e)}")
            self.send_error(500, str(e))

    def log_message(self, format, *args):
        """Override to customize logging."""
        print(f"[{self.log_date_time_string()}] {format % args}")


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

    # Initialize TAF
    taf = TAF(config=TAFConfig())

    print("=" * 60)
    print("Twilio Agentic Framework - Webhook Test Server")
    print("=" * 60)
    print(f"TAF Configuration: memora_service_id={taf.config.memora_service_id}")
    print(f"Server will start on: http://localhost:{args.port}")
    print()
    print("💡 For real Twilio webhooks:")
    print(f"   1. Start this server: python test_server.py --port {args.port}")
    print(f"   2. In another terminal: ngrok http {args.port}")
    print("   3. Copy ngrok URL to Twilio Console webhook settings")
    print()

    handler_class = create_handler(taf)

    try:
        server = HTTPServer(("localhost", args.port), handler_class)

        print(f"🚀 Server starting on http://localhost:{args.port}")
        print("📨 Ready to receive webhooks!")
        print("⏹️  Press Ctrl+C to stop")
        print("=" * 60)

        server.serve_forever()

    except KeyboardInterrupt:
        print("\n🛑 Shutting down server...")
        server.shutdown()
        print("✅ Server stopped.")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
