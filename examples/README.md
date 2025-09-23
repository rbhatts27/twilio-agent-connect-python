# TAF Examples

This directory contains examples and testing tools for the Twilio Agentic Framework (TAF).

## Quick Start

```bash
# Test TAF with sample webhook payloads (no server needed)
python examples/manual_testing.py

# Start webhook server for real Twilio testing
python examples/webhook_server.py
# Then in another terminal: ngrok http 8000
```

## Available Examples

### `manual_testing.py` - Comprehensive TAF Testing
Test TAF processing with various webhook scenarios without needing a server.

**Features:**
- ✅ Sample webhook payloads (basic messages, edge cases, error scenarios)
- ✅ Configuration validation testing
- ✅ Performance benchmarking
- ✅ Interactive mode for custom testing

**Usage:**
```bash
# Run all test suites
python examples/manual_testing.py

# Interactive testing mode
python examples/manual_testing.py interactive
> sample:basic_message
> {"EventType": "onMessageAdded", "ConversationSid": "CH123", "Body": "Test message", "Author": "+1234567890"}
```

### `webhook_server.py` - Real Webhook Testing Server
HTTP server to receive and test actual Twilio webhooks with TAF processing.

**Features:**
- ✅ Receives POST requests with webhook data
- ✅ Parses URL-encoded and JSON payloads
- ✅ Processes with TAF and shows results
- ✅ Web interface with testing instructions

**Usage:**
```bash
# Start server on localhost:8000
python examples/webhook_server.py

# Custom port
python examples/webhook_server.py --port 3000

# Test with curl
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "EventType=onMessageAdded&ConversationSid=CH123&Body=Hello%20world&Author=%2B1234567890"
```

## Real Twilio Webhook Testing

### Step-by-Step Setup

**1. Install ngrok:**
```bash
# macOS
brew install ngrok

# Get authtoken from https://dashboard.ngrok.com/
ngrok authtoken YOUR_TOKEN
```

**2. Start webhook server:**
```bash
python examples/webhook_server.py
```

**3. Expose with ngrok:**
```bash
# In another terminal
ngrok http 8000
```

**4. Configure Twilio Console:**
- Go to [Twilio Console](https://console.twilio.com/)
- Navigate: **Messaging** → **Services** → **[Your Service]**
- Set **Incoming Message Webhook URL** to your ngrok URL (e.g., `https://abc123.ngrok.io`)
- Set **HTTP Method** to `POST` and **Save**

**5. Test:** Send SMS to your Twilio phone number and watch the logs!

## Production Integration Examples

### Flask Integration
```python
from flask import Flask, request, jsonify
import urllib.parse
from taf import TAF

app = Flask(__name__)
taf = TAF({})

@app.route('/webhook', methods=['POST'])
def webhook():
    # Parse URL-encoded webhook data
    if request.content_type == 'application/x-www-form-urlencoded':
        raw_data = request.get_data(as_text=True)
        parsed_data = urllib.parse.parse_qs(raw_data)
        webhook_data = {k: v[0] if v else '' for k, v in parsed_data.items()}
    else:
        webhook_data = request.get_json()

    # Process with TAF
    result = taf.process_message(webhook_data)

    if result['processing']['should_process']:
        # Send to your AI service
        conversation_id = result['event']['conversation_sid']
        message = result['event']['body']
        # your_ai_service.process(conversation_id, message)

    return jsonify({"status": "processed"})
```

### FastAPI Integration
```python
from fastapi import FastAPI, Request
import urllib.parse
from taf import TAF

app = FastAPI()
taf = TAF({})

@app.post("/webhook")
async def webhook(request: Request):
    # Parse webhook data
    if request.headers.get("content-type") == "application/x-www-form-urlencoded":
        body = await request.body()
        parsed_data = urllib.parse.parse_qs(body.decode())
        webhook_data = {k: v[0] if v else '' for k, v in parsed_data.items()}
    else:
        webhook_data = await request.json()

    # Process with TAF
    result = taf.process_message(webhook_data)

    if result['processing']['should_process']:
        # Send to your AI service
        pass

    return {"status": "processed"}
```

## Testing Scenarios

### Supported Event Types
TAF only processes `onMessageAdded` events. All other event types are gracefully ignored:

| Event Type | Action | Description |
|------------|--------|-------------|
| `onMessageAdded` | ✅ Process | New message events |
| `onMessageAdd` | ❌ Ignore | Different event format (ignored) |
| `onParticipantAdded` | ❌ Ignore | Participant events (ignored) |
| Any other event | ❌ Ignore | All other events (ignored) |

### Sample Messages to Test
For `onMessageAdded` events, send these SMS messages to test different processing behaviors:

| Message | Should Process | Description |
|---------|----------------|-------------|
| `"I need help with my order"` | ✅ Yes | Customer message |
| `""` | ❌ No | Empty message |
| `"   "` | ❌ No | Whitespace only |
| `"URGENT: Help needed!"` | ✅ Yes | Urgent message |
| `"Hello! 👋"` | ✅ Yes | Message with emoji |

## Troubleshooting

### Common Issues

**Server won't start:**
```bash
# Check if port is in use
lsof -i :8000
# Try different port
python examples/webhook_server.py --port 8001
```

**No webhooks received:**
- Verify Twilio Console webhook URL matches ngrok URL exactly
- Ensure SMS is sent to correct Twilio phone number
- Check ngrok dashboard at `http://localhost:4040` for requests

**TAF processing errors:**
```bash
# Test TAF logic first
python examples/manual_testing.py
# Check webhook data format in server logs
```

## Security for Production

### Webhook Signature Validation
```python
import hashlib, hmac, base64

def validate_twilio_signature(url, post_data, signature, auth_token):
    expected = base64.b64encode(
        hmac.new(
            auth_token.encode('utf-8'),
            (url + post_data).encode('utf-8'),
            hashlib.sha1
        ).digest()
    ).decode()
    return hmac.compare_digest(expected, signature)

# Use in your webhook handler
signature = request.headers.get('X-Twilio-Signature', '')
if not validate_twilio_signature(request.url, request.get_data(as_text=True), signature, auth_token):
    return jsonify({'error': 'Invalid signature'}), 401
```

## Next Steps

1. **Start with manual testing** to understand TAF behavior
2. **Set up webhook server** and test with curl
3. **Use ngrok** to test with real Twilio webhooks
4. **Integrate with your AI service** using the processed results
5. **Deploy to production** with proper security and monitoring

Happy building! 🚀