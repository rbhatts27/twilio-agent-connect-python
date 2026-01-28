# Anchor 1: Concurrent Cross-Channel Communication

## All My Sons Moving & Storage Demo

This demo showcases TAC's ability to handle **concurrent voice and SMS channels within a single conversation**. The AI agent maintains context across channels and responds appropriately on each.

## The Ramirez Family Quote Request

**Consumer Story**: Maria Ramirez is moving her family from Phoenix, AZ to Austin, TX in 2 weeks. She needs an accurate quote for her 3BR home, including a valuable baby grand piano and antique cabinet.

### The Journey

1. **Voice Call (Primary)**
   - Maria calls All My Sons for a moving quote
   - AI: "Hi! I'd be happy to help you get a quote. Where are you moving from and to?"
   - Maria: "Phoenix to Austin, 3 bedroom house, about 2,500 square feet"
   - AI: "Great! To give you an accurate quote, especially for furniture and special items, could you text me some photos of your living room and any large items while we talk?"

2. **SMS (Secondary)** - While still on the call
   - Maria texts 3 photos: living room, baby grand piano, antique cabinet
   - AI sends SMS: "✓ Got your photos! Analyzing now..."

3. **Voice (Primary)** - Continues immediately
   - AI: "Perfect! I can see you have a beautiful baby grand piano and what looks like a valuable antique cabinet. Those will need our specialty crew. Based on your 2,500 square foot home and the items you showed me..."
   - AI: "Your total estimate is $4,200 to $4,800 for a 3-5 day delivery window. I'm texting you the detailed breakdown now."

4. **SMS (Secondary)**
   - AI sends formatted quote:
     ```
     📋 Your All My Sons Quote
     Phoenix, AZ → Austin, TX (870 miles)

     **Estimate: $4,200 - $4,800**

     Breakdown:
     • Base moving (2,500 sqft): $2,188
     • Distance (870 mi): $1,088
     • Baby Grand Piano: $800
     • Antique Cabinet: $300
     • Truck fee: $400

     🔗 Book online: allmysons.com/quote/AMS-123456
     ```

5. **Voice (Primary)** - Conversation continues
   - AI: "Did you get the text? Any questions about the quote?"
   - Maria: "What about insurance for the piano?"
   - AI explains insurance options and sends another SMS with insurance details

## Architecture Highlights

### Cross-Channel Linking
- Voice and SMS share the same **Maestro conversation ID**
- Customer phone number links channels via **profile_id**
- Conversation state persists across channels

### Event-Driven Processing
- SMS messages arriving during voice calls trigger immediate processing
- AI is instructed to acknowledge SMS and respond on both channels
- Dashboard shows real-time concurrent activity

### Channel-Aware Formatting
- **Voice**: Natural speech, no markdown, numbers spoken out
- **SMS**: Formatted text with bold, bullets, links

## Quick Start

### Prerequisites
- Python 3.11+
- Twilio account with SMS and Voice capabilities
- OpenAI API key
- ngrok for local webhook testing

### Setup

1. **Navigate to this directory**
   ```bash
   cd examples/anchor1_allmysons_concurrent
   ```

2. **Ensure environment is configured**
   The demo uses `.env` from the parent `examples/` directory. Verify these are set:
   ```bash
   TWILIO_TAC_ENVIRONMENT=prod
   TWILIO_TAC_ACCOUNT_SID=...
   TWILIO_TAC_AUTH_TOKEN=...
   TWILIO_TAC_PHONE_NUMBER=+1...
   TWILIO_TAC_CONVERSATION_SERVICE_SID=conv_configuration_...
   TWILIO_TAC_MEMORY_STORE_ID=mem_store_...
   TWILIO_TAC_OPENAI_API_KEY=sk-...
   TWILIO_TAC_VOICE_PUBLIC_DOMAIN=your-domain.ngrok.app
   ```

3. **Start ngrok**
   ```bash
   ngrok http 8000
   ```
   Update `TWILIO_TAC_VOICE_PUBLIC_DOMAIN` with your ngrok domain.

4. **Configure Twilio Webhooks**
   - SMS Webhook: `https://your-domain.ngrok.app/webhook`
   - Voice Webhook: `https://your-domain.ngrok.app/twiml`

5. **Run the server**
   ```bash
   # From repository root
   uv run python examples/anchor1_allmysons_concurrent/server.py

   # Or from this directory
   python server.py
   ```

6. **Open the dashboard**
   - Navigate to `http://localhost:8000/dashboard`
   - Watch real-time concurrent channel activity

## Testing the Demo

### Test Scenario 1: Voice + SMS Concurrent

1. **Call your Twilio number**
   - Say: "I need a quote for moving from Phoenix to Austin"
   - When AI asks for photos, say: "I'll text you some"

2. **Text the same number** (while on call)
   - Send: "Photo of living room with piano and antique cabinet"
   - The AI will acknowledge via SMS AND voice

3. **Continue voice conversation**
   - Ask about insurance, storage, or packing options
   - AI will send relevant details via SMS

### Test Scenario 2: Photo-Driven Quote

1. **Call and describe your move**
2. **Text descriptions** (simulating photos):
   - "living room with sectional sofa and entertainment center"
   - "dining room with table, 6 chairs, and china cabinet"
   - "bedroom with king bed, dresser, and nightstands"
3. **AI analyzes and calculates quote** incorporating all items

## Files Structure

```
anchor1_allmysons_concurrent/
├── server.py              # FastAPI server with concurrent channel handling
├── llm_service.py         # OpenAI Agents SDK integration
├── tools.py               # Moving industry tools (quote, photo analysis)
├── business_data.py       # Moving pricing, furniture catalog
├── dashboard/
│   ├── event_handler.py   # SSE event processing
│   ├── static/
│   │   └── dashboard.js   # Real-time dashboard UI
│   └── templates/
│       └── dashboard.html # Dashboard layout
├── tac/                   # Vendored TAC SDK
└── README.md              # This file
```

## Key Implementation Details

### Concurrent Channel Detection (server.py:108-124)
```python
# Check if SMS is from phone with active voice call
from_number = webhook_data.get("From")
existing_conv = get_conversation_for_phone(from_number)
if existing_conv and existing_conv in active_voice_calls:
    logger.info("CONCURRENT | SMS during active voice call")
```

### Cross-Channel Tools (tools.py)
```python
# Send quote via SMS while on voice call
@agents_function_tool
async def send_quote_sms(quote_summary: str) -> str:
    """Send formatted quote via SMS during voice conversation."""
```

### Channel-Aware LLM Instructions (llm_service.py:85-105)
```python
"CRITICAL: You are managing a conversation across BOTH voice and SMS.",
"- If customer sends SMS during voice call, acknowledge verbally",
"- Use send_quote_sms tool to send formatted quotes via SMS",
"- Keep voice responses conversational, SMS can be formatted",
```

## Dashboard Features

- **Concurrent Badge**: Shows when both channels are active
- **Timeline View**: Events with channel indicators (green=voice, blue=SMS)
- **Real-time Updates**: SSE streaming of all conversation events
- **Channel Dots**: Animated indicators when activity on each channel

## Troubleshooting

### SMS not linking to voice call
- Verify phone number format (E.164: +1234567890)
- Check that voice call established first
- Verify webhook URL includes `/webhook` path

### Voice responses not working
- Check ngrok is running and domain matches env var
- Verify TwiML webhook is configured
- Check WebSocket connection in dashboard

### Quote calculation issues
- Special items must match keys in `business_data.py`
- Distance lookup falls back to 800 miles if cities unknown

## Next Steps

- **Anchor 2**: Context Preservation Across Time
- **Anchor 3**: Seamless Channel Switching
- **Anchor 4**: AI↔Human Transfers

---

Built with [Twilio Agent Connect (TAC)](https://github.com/twilio/tac-python) SDK
