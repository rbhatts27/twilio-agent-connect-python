"""
AI Maria Agent - Consumer Simulation for Anchor 1 Demo

This agent simulates Maria Ramirez, a customer who:
1. Calls the All My Sons support line for a moving quote
2. Sends SMS with photos of furniture during the call
3. Engages naturally with the AI customer support agent

Usage:
    python maria_agent.py --call    # Initiate a voice call
    python maria_agent.py --sms     # Send an SMS with photo
    python maria_agent.py --demo    # Run full demo scenario
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment from parent examples directory
load_dotenv(Path(__file__).parent.parent / ".env")

# Twilio credentials
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_TAC_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_TAC_AUTH_TOKEN", "")
SUPPORT_NUMBER = os.environ.get("TWILIO_TAC_PHONE_NUMBER", "")  # The All My Sons support line
MARIA_NUMBER = os.environ.get("TWILIO_TAC_MARIA_NUMBER", "")  # Maria's phone number (caller)
OPENAI_API_KEY = os.environ.get("TWILIO_TAC_OPENAI_API_KEY", "")
PUBLIC_DOMAIN = os.environ.get("TWILIO_TAC_VOICE_PUBLIC_DOMAIN", "")

# Maria's persona for the LLM
MARIA_PERSONA = """You are Maria Ramirez, a friendly 35-year-old mother of two who is planning
a move from Austin, TX to Denver, CO in about 3 weeks. You're calling All My Sons Moving & Storage
to get a quote for your move.

Your situation:
- Family of 4 (you, husband Carlos, and two kids ages 8 and 5)
- Current home: 3-bedroom house in Austin with about 1,800 sq ft
- Moving to: 4-bedroom house in Denver (husband got a new job)
- Timeline: Need to move in 3 weeks
- Special items: A baby grand piano (was your grandmother's), some antique furniture,
  and your husband's vintage wine collection (~50 bottles)
- Budget conscious but want quality service for the piano

Your personality:
- Warm and conversational
- A bit anxious about the piano (sentimental value)
- Organized - you've started packing some boxes yourself
- Appreciative of helpful service

When asked about furniture, you'll mention you can send photos via text.
Keep responses natural and conversational - you're a real person on a phone call.
Don't be too formal. Use filler words occasionally like "um", "you know", etc.
"""


class MariaAgent:
    """AI agent that simulates Maria the consumer."""

    def __init__(self):
        self.twilio_client = None
        self.openai_client = None
        self.conversation_history: list[dict] = []
        self._setup_clients()

    def _setup_clients(self):
        """Initialize Twilio and OpenAI clients."""
        try:
            from twilio.rest import Client as TwilioClient

            self.twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            print("✓ Twilio client initialized")
        except Exception as e:
            print(f"✗ Failed to initialize Twilio client: {e}")

        try:
            from openai import OpenAI

            self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
            print("✓ OpenAI client initialized")
        except Exception as e:
            print(f"✗ Failed to initialize OpenAI client: {e}")

    async def generate_response(self, agent_message: str) -> str:
        """Generate Maria's response using OpenAI."""
        if not self.openai_client:
            return "Hello, I'm interested in getting a moving quote."

        # Add agent message to history
        self.conversation_history.append(
            {"role": "user", "content": f"[All My Sons Agent]: {agent_message}"}
        )

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": MARIA_PERSONA}, *self.conversation_history],
                max_tokens=200,
                temperature=0.8,
            )

            maria_response = response.choices[0].message.content or ""

            # Add Maria's response to history
            self.conversation_history.append({"role": "assistant", "content": maria_response})

            return maria_response

        except Exception as e:
            print(f"Error generating response: {e}")
            return "Yes, that sounds good."

    def initiate_call(self, twiml_url: Optional[str] = None) -> Optional[str]:
        """
        Initiate an outbound call from Maria to the support line.

        Returns the Call SID if successful.
        """
        if not self.twilio_client:
            print("✗ Twilio client not available")
            return None

        if not MARIA_NUMBER:
            print("✗ TWILIO_TAC_MARIA_NUMBER not set - need a verified caller ID number")
            print("  Set this to a verified Twilio number or your personal number")
            return None

        if not SUPPORT_NUMBER:
            print("✗ TWILIO_TAC_PHONE_NUMBER not set")
            return None

        # Use a TwiML URL that connects to our voice WebSocket
        # Or use Twilio's <Say> for a simple test
        if not twiml_url:
            # Default: simple TwiML that says Maria's greeting
            twiml_url = f"https://{PUBLIC_DOMAIN}/maria-twiml" if PUBLIC_DOMAIN else None

        try:
            print("\n📞 Initiating call...")
            print(f"   From: {MARIA_NUMBER} (Maria)")
            print(f"   To:   {SUPPORT_NUMBER} (All My Sons Support)")

            if twiml_url:
                call = self.twilio_client.calls.create(
                    to=SUPPORT_NUMBER,
                    from_=MARIA_NUMBER,
                    url=twiml_url,
                )
            else:
                # Use inline TwiML for simple greeting
                call = self.twilio_client.calls.create(
                    to=SUPPORT_NUMBER,
                    from_=MARIA_NUMBER,
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

            print(f"✓ Call initiated! SID: {call.sid}")
            print(f"   Status: {call.status}")
            return call.sid

        except Exception as e:
            print(f"✗ Failed to initiate call: {e}")
            return None

    def send_sms(
        self,
        message: str,
        media_url: Optional[str] = None,
    ) -> Optional[str]:
        """
        Send an SMS from Maria to the support line.

        Args:
            message: The SMS text content
            media_url: Optional URL to an image (must be publicly accessible)

        Returns the Message SID if successful.
        """
        if not self.twilio_client:
            print("✗ Twilio client not available")
            return None

        if not MARIA_NUMBER:
            print("✗ TWILIO_TAC_MARIA_NUMBER not set")
            return None

        try:
            print("\n📱 Sending SMS...")
            print(f"   From: {MARIA_NUMBER} (Maria)")
            print(f"   To:   {SUPPORT_NUMBER} (All My Sons Support)")
            print(
                f"   Message: {message[:50]}..." if len(message) > 50 else f"   Message: {message}"
            )

            kwargs = {
                "to": SUPPORT_NUMBER,
                "from_": MARIA_NUMBER,
                "body": message,
            }

            if media_url:
                kwargs["media_url"] = [media_url]
                print(f"   Media: {media_url}")

            msg = self.twilio_client.messages.create(**kwargs)

            print(f"✓ SMS sent! SID: {msg.sid}")
            print(f"   Status: {msg.status}")
            return msg.sid

        except Exception as e:
            print(f"✗ Failed to send SMS: {e}")
            return None

    def send_photo_sms(self, photo_description: str = "living room") -> Optional[str]:
        """
        Send an SMS with a sample house photo.

        Uses a publicly available sample image for demo purposes.
        """
        # Sample house/furniture images (publicly accessible)
        sample_images = {
            "living room": "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=800",
            "bedroom": "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?w=800",
            "piano": "https://images.unsplash.com/photo-1520523839897-bd0b52f945a0?w=800",
            "furniture": "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=800",
            "boxes": "https://images.unsplash.com/photo-1600585152220-90363fe7e115?w=800",
        }

        image_url = sample_images.get(photo_description.lower(), sample_images["living room"])

        message = f"Here's a photo of our {photo_description}. This should help with the estimate!"

        return self.send_sms(message, media_url=image_url)


async def run_demo_scenario(agent: MariaAgent):
    """
    Run the full Anchor 1 demo scenario:
    1. Maria calls for a moving quote
    2. During the call, she sends photos via SMS
    """
    print("\n" + "=" * 60)
    print("🎬 ANCHOR 1 DEMO: The Ramirez Family Quote Request")
    print("=" * 60)

    print("\n📋 Scenario Steps:")
    print("   1. Maria calls for a moving quote (Voice)")
    print("   2. AI agent asks about furniture")
    print("   3. Maria texts photos while on call (SMS)")
    print("   4. AI analyzes photos and provides quote")
    print("   5. Quote sent via SMS")

    # Step 1: Initiate the call
    print("\n" + "-" * 40)
    print("STEP 1: Initiating voice call...")
    print("-" * 40)

    call_sid = agent.initiate_call()

    if call_sid:
        print("\n⏳ Waiting for call to connect (10 seconds)...")
        await asyncio.sleep(10)

        # Step 3: Send photo while on call
        print("\n" + "-" * 40)
        print("STEP 3: Sending photo via SMS (concurrent channel)...")
        print("-" * 40)

        agent.send_photo_sms("living room")

        await asyncio.sleep(3)

        # Send another photo
        print("\n📸 Sending another photo...")
        agent.send_photo_sms("piano")

        print("\n" + "=" * 60)
        print("✓ Demo scenario initiated!")
        print("  Watch the dashboard at http://localhost:8000/dashboard")
        print("  to see concurrent channel activity.")
        print("=" * 60)
    else:
        print("\n⚠️  Call failed. Sending SMS only...")
        agent.send_sms(
            "Hi! I'm interested in getting a moving quote from Austin to Denver. "
            "We have a 3 bedroom house with a baby grand piano. Can you help?"
        )
        await asyncio.sleep(2)
        agent.send_photo_sms("living room")


def main():
    parser = argparse.ArgumentParser(
        description="AI Maria Agent - Consumer simulation for Anchor 1 demo"
    )
    parser.add_argument(
        "--call", action="store_true", help="Initiate a voice call to the support line"
    )
    parser.add_argument(
        "--sms",
        type=str,
        nargs="?",
        const="Hi, I'm interested in getting a moving quote.",
        help="Send an SMS (optionally with custom message)",
    )
    parser.add_argument(
        "--photo",
        type=str,
        nargs="?",
        const="living room",
        help="Send an SMS with a photo (living room, bedroom, piano, furniture, boxes)",
    )
    parser.add_argument(
        "--demo", action="store_true", help="Run the full demo scenario (call + SMS with photos)"
    )

    args = parser.parse_args()

    # Validate configuration
    print("\n🔧 Configuration Check:")
    print(
        f"   Account SID: {'✓' if TWILIO_ACCOUNT_SID else '✗'} {TWILIO_ACCOUNT_SID[:10]}..."
        if TWILIO_ACCOUNT_SID
        else "   Account SID: ✗ Not set"
    )
    print(f"   Support #:   {'✓' if SUPPORT_NUMBER else '✗'} {SUPPORT_NUMBER}")
    print(f"   Maria #:     {'✓' if MARIA_NUMBER else '✗'} {MARIA_NUMBER}")
    print(
        f"   OpenAI Key:  {'✓' if OPENAI_API_KEY else '✗'} {'Set' if OPENAI_API_KEY else 'Not set'}"
    )

    if not MARIA_NUMBER:
        print("\n⚠️  TWILIO_TAC_MARIA_NUMBER is not set!")
        print("   Add this to your examples/.env file:")
        print("   TWILIO_TAC_MARIA_NUMBER=+1XXXXXXXXXX")
        print("   (Use a verified Twilio number or your personal number)")
        sys.exit(1)

    agent = MariaAgent()

    if args.demo:
        asyncio.run(run_demo_scenario(agent))
    elif args.call:
        agent.initiate_call()
    elif args.photo:
        agent.send_photo_sms(args.photo)
    elif args.sms:
        agent.send_sms(args.sms)
    else:
        parser.print_help()
        print("\n💡 Examples:")
        print("   python maria_agent.py --demo          # Run full demo")
        print("   python maria_agent.py --call          # Just call")
        print("   python maria_agent.py --sms 'Hello!'  # Send SMS")
        print("   python maria_agent.py --photo piano   # Send photo SMS")


if __name__ == "__main__":
    main()
