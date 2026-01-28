# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is the `/examples` directory of the Twilio Agent Connect (TAC) Python SDK. For core architecture, API clients, and SDK details, see the parent [CLAUDE.md](../CLAUDE.md).

## Running Examples
```bash
# From repository root
make sync                           # Install dependencies
make quickstart                     # Setup wizard at http://localhost:8080
make exec-demo                      # Multi-channel demo with hot reload
make server                         # SMS webhook server (port 8000)

# Run specific examples
uv run python examples/servers/voice.py
uv run python examples/channels/sms.py --port 3000
uv run python examples/tools/openai_chat_with_tools.py
```

## Directory Structure

- **quickstart/** - Web UI wizard for creating Memory/Maestro services and generating `.env`
- **exec_demo/** - Production-ready multi-channel demo (SMS + Voice) with OpenAI Agents
- **servers/** - Simplified server setup using `VoiceServerConfig` (recommended starting point)
- **channels/** - Manual FastAPI implementations with full control (sms.py, voice.py, voice_escalation.py, voice_interrupts.py)
- **tools/** - LLM tool integration examples (OpenAI Chat, OpenAI Agents)
- **agents/** - Additional agent integration patterns

## Environment Configuration

Examples load configuration from `.env` via `TACConfig.from_env()`. Copy `.env.example` to `.env` or use the quickstart wizard.

**Required:**
- `TWILIO_TAC_ENVIRONMENT` - dev/stage/prod
- `TWILIO_TAC_ACCOUNT_SID`, `TWILIO_TAC_AUTH_TOKEN`
- `TWILIO_TAC_PHONE_NUMBER`, `TWILIO_TAC_CONVERSATION_SERVICE_SID`

**Optional (Memory):**
- `TWILIO_TAC_MEMORY_STORE_ID`, `TWILIO_TAC_MEMORY_API_KEY`, `TWILIO_TAC_MEMORY_API_TOKEN`
- `TWILIO_TAC_TRAIT_GROUPS` (comma-separated)

**Optional (CI):**
- `TWILIO_TAC_CI_CONFIGURATION_ID`, `TWILIO_TAC_CI_OBSERVATION_OPERATOR_SID`, `TWILIO_TAC_CI_SUMMARY_OPERATOR_SID`

**Optional (Examples):**
- `TWILIO_TAC_OPENAI_API_KEY` - For OpenAI examples
- `TWILIO_TAC_VOICE_PUBLIC_DOMAIN` - ngrok domain for voice examples
- `TWILIO_TAC_KNOWLEDGE_IDS` - Comma-separated knowledge base IDs

## Code Style for Examples

Examples have relaxed linting rules (see `pyproject.toml`):
- E402 (import order) - Allowed for `sys.path` manipulation
- E501 (line length) - Allowed for readability
- N803 (naming) - Allowed for Twilio parameter names like `Body`, `From`

When modifying examples, match existing patterns in the file rather than enforcing strict style.

## exec_demo Architecture

The exec_demo is a complete production example with:
- **server.py** - FastAPI server with SMS webhook, Voice WebSocket, and CI webhook endpoints
- **llm_service.py** - OpenAI Agents integration with memory context
- **tools.py** - Custom business tools (plan upgrades, account lookup)
- **business_data.py** - Mock ISP customer data
- **tac/** - Vendored copy of TAC SDK for Railway deployment

Key patterns in exec_demo:
1. Single server handles both SMS and Voice channels
2. `on_message_ready` callback invokes LLM service with memory context
3. CI webhook processes operator results to create observations/summaries
4. Voice uses simplified `VoiceServerConfig` pattern

## Testing Examples Locally

1. Start ngrok tunnel: `make ngrok` or `ngrok http 8000`
2. Configure Twilio webhooks to point to ngrok URL
3. Run example server
4. Test via SMS to your Twilio number or call for voice

## Common Patterns

**SMS with fire-and-forget processing:**
```python
@app.post("/webhook")
async def webhook(request: Request):
    idempotency_token = request.headers.get("i-twilio-idempotency-token")
    asyncio.create_task(sms_channel.process_webhook(data, idempotency_token))
    return {"status": "ok"}  # Return 200 immediately
```

**Voice with simplified server:**
```python
voice_channel = VoiceChannel(
    tac=tac,
    server_config=VoiceServerConfig(
        public_domain=os.environ["TWILIO_TAC_VOICE_PUBLIC_DOMAIN"],
        welcome_greeting="Hello!",
    ),
)
voice_channel.start()
```

**Tool integration:**
```python
from tac.tools import function_tool

@function_tool()
def my_tool(param: str) -> str:
    """Tool description."""
    return result

# Use with OpenAI
openai_format = my_tool.to_openai_format()
```

---

# TAC Demo Builder - Sierra Use Case Anchors

## Mission

Create production-quality demo examples showcasing TAC's "Sierra Use Case Anchors" using **All My Sons Moving & Storage** (https://www.allmysons.com/) as the customer backdrop. Each demo tells a compelling moving industry story with realistic consumer experiences.

## Customer Context: All My Sons Moving & Storage

**Company**: All My Sons Moving & Storage  
**Industry**: Residential & Commercial Moving  
**Website**: https://www.allmysons.com/

**Why Moving Industry is Perfect for TAC Demos:**
- ✅ Naturally multi-channel (calls for quotes, texts for updates, photos of items)
- ✅ Time-sensitive coordination (moving dates, truck schedules)
- ✅ High-touch, emotional journey (people's entire lives)
- ✅ Mix of simple and complex (routine updates vs. damage claims)
- ✅ Perfect for AI + human handoff (AI handles scheduling, humans handle exceptions)

## Official API Documentation

### Memora (Customer Memory) APIs
**Documentation**: https://docs-njwp1fvi0-twilio.vercel.app/docs/platform/customer-memory?beta-feature=true

**Key capabilities**:
- Customer profile management
- Long-term memory storage (observations, traits)
- Session context and conversation summaries
- Memory recall for contextual responses
- Cross-channel identity linking

**When to use**: For storing and retrieving customer information across conversations, implementing context preservation (Anchor 2), and maintaining customer state.

### Maestro (Conversation Backbone) APIs
**Documentation**: https://friendly-adventure-16rng7z.pages.github.io/#events/ConversationEventV1.avsc

**Key capabilities**:
- Conversation lifecycle management
- Multi-channel message grouping
- Participant tracking (AI, human, customer)
- Conversation status and timeouts
- Event streams for conversation activity

**When to use**: For managing conversation state, tracking channel switches (Anchor 3), handling participant changes (Anchor 4), and generating conversation analytics (Anchor 5).

### TAF (Twilio Agent Framework)
**Location**: In the codebase at `/src/tac/`

**Key capabilities**:
- Integration with 3P agent runtimes (OpenAI, Bedrock, etc.)
- Tool/function calling interface
- Event handling for conversations
- Channel-aware message routing

**When to use**: For building the AI agent logic and connecting to LLM providers.

### CINTEL (Conversation Intelligence)
**Status**: Part of the Sierra platform roadmap

**Expected capabilities**:
- Conversation analysis and classification
- Sentiment tracking
- Topic extraction
- Escalation signals
- Performance metrics

**When to use**: For analytics dashboards (Anchor 5) and intelligent routing decisions.

---

## The 6 Use Case Anchors - All My Sons Moving Stories

### Anchor 1: Concurrent Cross-Channel In-Session Communication ⚡ CURRENT PRIORITY

**Capability**: Agent is present across multiple channels simultaneously within one conversation.

**Moving Industry Scenario**: "The Ramirez Family Quote Request"

**Consumer Journey:**
Maria Ramirez is moving from Phoenix, AZ to Austin, TX in 2 weeks.

1. **Voice Call (Primary)**: Maria calls All My Sons for a moving quote
   - AI: "Hi Maria! I can help you get an instant quote. What's your current address?"
   - Maria provides: 3BR house, 2,500 sq ft, Phoenix to Austin
   - AI: "I'll need to see your furniture to give you an accurate quote. Can you text me photos of your living room and any large items while we talk, or I can email you a link?"

2. **SMS (Secondary)** - While still on the call:
   - Maria texts 3 photos: living room, baby grand piano, antique cabinet
   - AI sends SMS: "✓ Got your photos. Analyzing now..."

3. **Voice (Primary)** - Continues immediately:
   - AI: "Perfect! I can see you have a baby grand piano and what looks like a valuable antique cabinet. Those will need special handling. Based on your 2,500 sq ft home and the items you showed me, I'm calculating your quote now..."
   - AI: "Your total estimate is $4,200-$4,800 for a 3-day window. I'm texting you the detailed breakdown now."

4. **SMS (Secondary)**:
   - AI sends: "📋 Your Move Quote: $4,200-$4,800\n• Standard items: $2,800\n• Piano (special): $800\n• Packing: $600\n🔗 View full quote: [link]"

5. **Voice (Primary)**:
   - AI: "Did you get the text? Any questions about the quote?"
   - Maria: "What about insurance for the antiques?"
   - AI explains insurance, sends another SMS with insurance options

**Key Features to Implement:**
- Voice as primary channel (WebSocket + TwiML)
- SMS as secondary channel for artifacts (photos, quote details)
- AI responds on BOTH channels when SMS arrives during voice call
- Photo analysis simulation (AI "seeing" piano, furniture types)
- Quote calculation based on distance, volume, special items
- Real-time timeline visualization in dashboard

**Business Tools Needed:**
```python
@function_tool
async def calculate_move_quote(origin: str, destination: str, sqft: int, special_items: list) -> dict:
    """Calculate moving quote based on distance and inventory."""
    
@function_tool
async def analyze_furniture_photo(description: str) -> list:
    """Simulate AI analyzing furniture photo to identify items."""
    
@function_tool
async def generate_quote_breakdown(items: list, distance: int) -> dict:
    """Generate itemized quote with special handling fees."""
    
@function_tool
async def send_quote_sms(phone: str, quote_details: dict) -> str:
    """Send formatted quote breakdown via SMS."""
```

**TAC Components**: Maestro (conversation management), TAF (multi-channel events), SMS + Voice channels

---

### Anchor 2: Context Preservation Across Channels & Time

**Capability**: Agent uses full interaction history across channels and time, with subject-level discrimination.

**Moving Industry Scenario**: "The Insurance Claim Journey"

**Consumer Journey:**
- **Week 1**: Customer called about initial quote (voice)
- **Week 2**: Texted to update inventory list (SMS)
- **Week 3**: Emailed signed contract (email)
- **Move Day**: Dresser was damaged during move
- **Week 4**: Customer texts: "Hey, about that dresser damage..."
- **AI Response**: "I see the dresser damage from your Austin move on July 15th. You mentioned it was a family heirloom when we did your quote. Let me pull up your claim form and photos from move day..."

**Key Features:**
- Multi-week conversation spanning voice, SMS, email
- Subject-level retrieval (damage claim vs. original quote)
- Memora stores: original quote details, special item notes, move date, crew assignment
- AI correctly associates "dresser damage" with move event, not quote discussion

**TAC Components**: Memora (memory retrieval), Maestro (conversation history), TAF (context injection)

---

### Anchor 3: Seamless Channel Switching

**Capability**: User changes primary channel without losing context or restarting.

**Moving Industry Scenario**: "The Schedule Change Escalation"

**Consumer Journey:**
1. **SMS back-and-forth**: Customer trying to reschedule move date
   - Customer: "I need to change my move date from Aug 1st"
   - AI: "What's your new preferred date?"
   - Customer: "Aug 15th, but my new place isn't ready until then"
   - Customer: "Can I put stuff in storage for 2 weeks?"

2. **Gets complex**: Multiple date conflicts, storage options, pricing changes

3. **AI offers**: "This is getting tricky with the storage timing and your piano. Can I call you now to work this out faster?"

4. **Customer**: "Yes"

5. **Phone rings immediately**: AI starts with full context
   - AI: "I'm looking at your schedule - you need to move out August 1st but your new place isn't ready until August 15th, so we need 2-week storage for your 3BR including that baby grand piano. Let me walk you through the options..."

**Key Features:**
- SMS → Voice channel switch
- Full context carries forward (dates, piano, storage needs)
- Conversation stitching across Maestro conversations
- Primary channel tracking updates

**TAC Components**: Maestro (conversation stitching), Memora (session context), TAF (channel-aware routing)

---

### Anchor 4: Seamless AI↔Human Transfers

**Capability**: Smooth handoff between AI and human agents with full context, plus AI co-pilot mode.

**Moving Industry Scenario**: "The Piano Disaster"

**Consumer Journey:**
1. **AI handling**: Standard move coordination via SMS
2. **Customer reports**: "Your guys just dropped my grandmother's piano down the stairs"
3. **AI detects**: High emotion, damage claim, high-value item, escalation needed
4. **AI response**: "I'm so sorry this happened. I'm connecting you with our claims manager Sarah right now who specializes in high-value items."
5. **Human joins (Sarah)**: Sees complete context:
   - Piano marked "fragile - sentimental value - grandmother's 1920s baby grand" in original quote
   - Photos from 2 weeks ago showing the piano
   - Move crew assignment: Mike's team, truck #247
   - Original quote value: $15,000 for piano alone
6. **Sarah (Human)**: "Maria, I can see this is your grandmother's baby grand that we quoted at $15,000 value. I'm looking at the crew's incident report now and photos they just uploaded. This is clearly our responsibility. Let me explain our claims process and get this resolved today..."
7. **After resolution**: Human hands back to AI for routine follow-up (scheduling repair, insurance paperwork)

**Key Features:**
- Sentiment detection triggers escalation
- Human agent gets full Maestro conversation + Memora profile
- Participant tracking (AI → Human → AI)
- CINTEL tags AI vs. human portions
- AI co-pilot mode (suggesting responses to human)

**TAC Components**: Maestro (participant management), Memora (context sharing), TAF (handoff orchestration)

---

### Anchor 5: Unified Insights Across Conversations

**Capability**: Analytics across all conversations showing AI/human performance, containment, escalation patterns.

**Moving Industry Scenario**: "Operations Dashboard"

**Dashboard Insights:**
- "78% of damage claims originated from 'piano/specialty item' moves"
- "Customers who text photos during quote have 45% higher conversion rate"
- "SMS→Voice channel switches happen 60% more on moves >500 miles"
- "AI handles 89% of schedule changes, escalates 11% to humans"
- "Average quote-to-booking time: 4.2 hours (vs. 18 hours industry average)"
- "Top escalation reasons: damage claims (34%), complex scheduling (28%), pricing disputes (18%)"

**Key Features:**
- Conversation-level metrics (duration, channels used, outcome)
- Aggregate analytics (containment rates, escalation patterns)
- Drill-down from macro to individual conversations
- CINTEL-derived classifications (topics, sentiment, outcomes)

**TAC Components**: Maestro (conversation metadata), CINTEL (analytics), Event Streams (telemetry)

---

### Anchor 6: Outbound-to-Conversational Activation

**Capability**: Outbound alerts/campaigns become two-way conversation entry points.

**Moving Industry Scenario**: "The Moving Day Update"

**Consumer Journey:**
1. **Outbound SMS (8:45 AM)**: 
```
   Your All My Sons crew is 15 minutes away! 
   Driver: Mike (★4.9) 
   Truck: #247
   Reply with any questions.
```

2. **Customer replies (8:46 AM)**: "Wait, do they have the special straps for my piano?"

3. **AI responds immediately**: 
```
   Yes! Your move plan includes piano straps and furniture pads. 
   Mike has handled 47 piano moves this year. 
   Your piano is item #12 on the truck manifest.
   Need anything else?
```

4. **Customer**: "Phew, thanks! How long will loading take?"

5. **AI**: "For your 2,500 sq ft with piano, typically 3-4 hours. Mike's team will give you updates every hour. I'll text you when they're heading to Austin!"

**Key Features:**
- Outbound campaign (moving day alerts) becomes conversational
- Campaign context flows to AI (move plan, crew, inventory)
- Two-way activation without overwhelming human agents
- Memora links outbound message to customer profile

**TAC Components**: Maestro (conversation initiation), Memora (campaign context), TAF (response handling)

---

## Current Development Status

### ✅ Completed
- exec_demo (Owl Internet ISP) - baseline multi-channel demo
- Development environment setup
- Claude.md project instructions

### 🚧 In Progress
- **Anchor 1: All My Sons Concurrent Channels Demo**
  - Directory: `examples/anchor1_allmysons_concurrent/`
  - Consumer Story: The Ramirez Family Quote Request
  - Status: Ready to build with Claude Code

### 📋 Planned
- Anchor 2: Insurance Claim Context Preservation
- Anchor 3: Schedule Change Channel Switching  
- Anchor 4: Piano Disaster Human Escalation
- Anchor 5: Operations Analytics Dashboard
- Anchor 6: Moving Day Activation
- Multi-anchor integration demo

---

## Building Anchor Demos - Instructions for Claude Code

### Phase 1: Setup & Review (Always do this first)
1. **Review exec_demo**: Study `/examples/exec_demo` structure thoroughly
2. **Read API docs**: Browse Memora and Maestro documentation links above
3. **Understand TAC architecture**: Review `/src/tac/` source code
4. **Ask clarifying questions** before coding

### Phase 2: Create Demo Structure

**Directory naming**: `examples/anchor{N}_{company}_{feature}/`

**Example**: `examples/anchor1_allmysons_concurrent/`

**Required files:**
```
anchor1_allmysons_concurrent/
├── server.py              # FastAPI server (webhooks: /webhook, /twiml, /ws)
├── llm_service.py         # OpenAI Agents SDK integration
├── tools.py               # Business logic as @function_tool decorators
├── business_data.py       # Moving industry data model
│   ├── FURNITURE_TYPES    # Furniture catalog with weights, handling
│   ├── PRICING_MATRIX     # Distance-based, item-based pricing
│   ├── LOCATIONS          # City pairs, distances, routes
│   ├── SPECIAL_ITEMS      # Pianos, antiques, fragile items
│   └── MOVE_CREWS         # Crew data, specialties, ratings
├── memora_service.py      # Memora API integration (optional, can be in tools.py)
├── dashboard/             # Real-time visualization
│   ├── static/
│   │   └── dashboard.js   # WebSocket updates, timeline view
│   └── templates/
│       └── index.html     # Dashboard UI
├── README.md              # Consumer story + setup instructions
├── requirements.txt       # Python dependencies
└── .env.example           # Environment variables template
```

### Phase 3: Implementation Checklist

**For each demo, implement:**

✅ **FastAPI Server**
- `/webhook` endpoint for SMS (fire-and-forget pattern)
- `/twiml` endpoint for voice call initiation
- `/ws` WebSocket endpoint for voice streaming
- `/dashboard` endpoint for visualization
- `/events` SSE endpoint for real-time updates

✅ **Business Logic Tools**
- Use `@function_tool` decorator from TAC
- Tools specific to the moving industry scenario
- Realistic data and calculations
- Error handling and validation

✅ **OpenAI Agent Integration**
- Agent instructions tailored to All My Sons brand
- System prompt includes:
  - Company context and values
  - Moving industry expertise
  - Channel-aware response formatting
  - When to use which tools

✅ **Multi-Channel Handling**
- Voice channel with VoiceServerConfig
- SMS channel with SMSChannel
- Concurrent channel coordination
- Channel-specific message formatting

✅ **Memora Integration** (when relevant)
- Profile creation/retrieval
- Observation storage
- Memory recall for context
- Conversation linking

✅ **Dashboard** (optional but recommended)
- Real-time conversation timeline
- Channel activity visualization
- Tool invocation tracking
- Message flow diagram

✅ **Documentation**
- README.md with consumer story
- Step-by-step setup instructions
- Testing procedures
- Expected behavior description

### Code Quality Standards
```python
# ✅ GOOD: Follows exec_demo patterns
@function_tool
async def calculate_move_quote(
    origin: str,
    destination: str, 
    sqft: int,
    special_items: list[str]
) -> dict:
    """
    Calculate moving quote based on distance and inventory.
    
    Args:
        origin: Origin city, state (e.g. "Phoenix, AZ")
        destination: Destination city, state
        sqft: Square footage of home
        special_items: List of special handling items
        
    Returns:
        Quote details with breakdown
    """
    # Implementation with logging
    logger.info(f"Calculating quote: {origin} → {destination}, {sqft} sqft")
    
    # Realistic pricing logic
    distance = calculate_distance(origin, destination)
    base_cost = sqft * 2.5  # $2.50 per sq ft
    distance_cost = distance * 1.2  # $1.20 per mile
    special_cost = sum(SPECIAL_ITEM_FEES.get(item, 0) for item in special_items)
    
    return {
        "total_min": base_cost + distance_cost + special_cost,
        "total_max": (base_cost + distance_cost + special_cost) * 1.15,
        "breakdown": {...}
    }
```
```python
# ❌ BAD: Hardcoded, not realistic
def get_quote():
    return {"price": 5000}  # No logic, no context
```

### Demo-Specific Requirements

**Make it feel real:**
- Use actual All My Sons branding and tone
- Realistic furniture types, weights, handling requirements
- Actual city distances and routes
- Real moving industry pricing (research typical costs)
- Authentic customer scenarios

**Show, don't tell:**
- Working webhooks with actual Twilio events
- Real-time processing (not mock delays)
- Actual OpenAI API calls
- Live dashboard updates

**Easy to run:**
- Single command setup: `uv run uvicorn server:app --reload`
- Clear environment variable instructions
- Test scripts or curl commands provided
- Works with cloudflared or ngrok tunnel

**Visual feedback:**
- Dashboard shows concurrent channel activity
- Terminal logs clearly indicate what's happening
- SMS and Voice events visually distinct
- Timeline shows message flow

**Testable:**
- README includes test procedure
- Sample test cases provided
- Expected outputs documented
- Error cases handled gracefully

## Environment Variables

Copy from exec_demo's `.env`:
```bash
# Twilio credentials
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_API_KEY_SID=
TWILIO_API_SECRET=
TWILIO_PHONE_NUMBER=

# TAC configuration
TWILIO_TAC_CONVERSATION_SERVICE_SID=
TWILIO_TAC_MEMORY_STORE_ID=
TWILIO_TAC_VOICE_PUBLIC_DOMAIN=

# OpenAI
TWILIO_TAC_OPENAI_API_KEY=

# Demo-specific (optional)
TWILIO_TAC_COMPANY_NAME="All My Sons Moving & Storage"
```

## Success Criteria

Each demo must:
1. ✅ Clearly showcase the target anchor capability
2. ✅ Tell the All My Sons moving story authentically
3. ✅ Run locally with minimal setup (<5 commands)
4. ✅ Use Memora APIs correctly (when applicable)
5. ✅ Use Maestro for conversation management
6. ✅ Include visual dashboard or detailed logs
7. ✅ Have comprehensive README with consumer story
8. ✅ Be production-quality code (not hacky POC)
9. ✅ Include inline comments explaining TAC API usage
10. ✅ Work with ngrok/cloudflared tunnels

## Questions to Ask Before Building

When Claude Code starts a new anchor demo, it should ask:

1. **Confirm the scenario**: "I'm building Anchor {N}: {Name}. The consumer story is: {brief}. Is this correct?"

2. **Environment setup**: "Do you have the .env file configured from exec_demo? Is cloudflared/ngrok running?"

3. **Scope decisions**:
   - "Should I include a real-time dashboard?"
   - "Should I use real Memora APIs or mock memory for this demo?"
   - "How detailed should the business_data.py be (simple vs. comprehensive)?"

4. **Technical choices**:
   - "Should I copy patterns exactly from exec_demo or simplify for clarity?"
   - "Any specific OpenAI model preferences (gpt-4, gpt-4-turbo, etc.)?"
   - "Should this demo be standalone or share utilities with other anchors?"

5. **Testing approach**:
   - "How will you test this? (Phone call, SMS, or both?)"
   - "Do you want test scripts or manual testing instructions?"

## Important Reminders

- **Always check API documentation** when using Memora or Maestro features
- **Don't hardcode** - use environment variables for all credentials
- **Handle errors gracefully** - network can fail, APIs can timeout
- **Log extensively** - make debugging easy with clear messages
- **Test incrementally** - build feature by feature, test as you go
- **Follow exec_demo patterns** - consistency matters
- **Make it realistic** - actual moving industry data and workflows
- **Document thoroughly** - future developers will thank you

---

## Getting Started with Anchor 1

**Ready to build the first demo?**

Run Claude Code and provide this task:
```
I want to build Anchor 1 demo: Concurrent Cross-Channel Communication.

Customer: All My Sons Moving & Storage
Scenario: The Ramirez Family Quote Request

Consumer Journey:
- Maria calls for moving quote (voice primary)
- AI asks for furniture photos
- Maria texts 3 photos while on call (SMS secondary)
- AI analyzes photos, acknowledges via SMS
- AI continues on voice with quote calculation
- AI sends detailed quote breakdown via SMS
- Voice conversation continues about insurance/options

Directory: examples/anchor1_allmysons_concurrent/

Copy patterns from exec_demo but:
- Simplify for single use case focus
- Add moving industry business logic
- Emphasize concurrent channel handling
- Include dashboard showing timeline

Ask clarifying questions before you start coding.
```

Let's build compelling TAC demos that showcase what makes Sierra truly different!