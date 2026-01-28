"""
Moving industry tools for All My Sons Moving & Storage demo.

These tools demonstrate TAC's function calling capabilities for:
- Quote calculation based on distance, home size, and special items
- Mock photo analysis (simulating AI vision for furniture identification)
- SMS quote delivery
- Special handling identification
"""

import logging
import random
from typing import Annotated, Any, Optional

from agents import function_tool as agents_function_tool
from business_data import (
    COMPANY_INFO,
    FURNITURE_TYPES,
    HOME_SIZE_ESTIMATES,
    INSURANCE_OPTIONS,
    PACKING_SERVICES,
    PRICING_MATRIX,
    SPECIAL_ITEMS,
    STORAGE_OPTIONS,
    get_distance,
    get_pricing_tier,
)

from tac import TAC
from tac.models.session import ConversationSession
from tac.tools.base import InjectedToolArg, function_tool

logger = logging.getLogger(__name__)


# =============================================================================
# Photo Analysis Tools (Mock - simulates AI vision)
# =============================================================================


@agents_function_tool
async def analyze_furniture_photo(photo_description: str) -> dict[str, Any]:
    """
    Analyze a furniture photo to identify items and their handling requirements.
    This is a MOCK implementation - in production, would use GPT-4 Vision.

    The AI agent should call this when a customer mentions sending a photo
    or when processing an MMS image. The photo_description should be what
    the AI "sees" or what the customer describes.

    Args:
        photo_description: Description of what's in the photo (e.g., "living room with piano")

    Returns:
        Dictionary with identified items, handling requirements, and special notes
    """
    logger.info(f"[TOOL:PHOTO] Analyzing photo: {photo_description[:50]}...")

    # Mock photo analysis - identify items based on keywords in description
    description_lower = photo_description.lower()

    identified_items = []
    special_items_found = []
    handling_notes = []
    total_estimated_weight = 0
    total_cubic_feet = 0

    # Check for special items first (they have specific requirements)
    special_keywords = {
        "piano": "baby_grand_piano",
        "baby grand": "baby_grand_piano",
        "grand piano": "grand_piano",
        "upright piano": "upright_piano",
        "antique": "antique_furniture",
        "antique cabinet": "antique_cabinet",
        "grandfather clock": "grandfather_clock",
        "pool table": "pool_table",
        "billiard": "pool_table",
        "hot tub": "hot_tub",
        "spa": "hot_tub",
        "safe": "safe",
        "gun safe": "safe",
        "artwork": "artwork_large",
        "painting": "artwork_large",
        "wine": "wine_collection",
    }

    for keyword, item_key in special_keywords.items():
        if keyword in description_lower:
            item_data = SPECIAL_ITEMS[item_key]
            special_items_found.append({
                "item": item_key.replace("_", " ").title(),
                "weight_lbs": item_data["avg_weight_lbs"],
                "cubic_feet": item_data["cubic_feet"],
                "handling": item_data["handling"],
                "special_fee": item_data["base_fee"],
                "requirements": item_data["requirements"],
                "insurance_value": item_data["insurance_value_typical"],
            })
            total_estimated_weight += item_data["avg_weight_lbs"]
            total_cubic_feet += item_data["cubic_feet"]
            handling_notes.extend(item_data["requirements"])

    # Check for standard furniture
    furniture_keywords = {
        "sofa": "sofa",
        "couch": "sofa",
        "sectional": "sectional_sofa",
        "armchair": "armchair",
        "recliner": "armchair",
        "coffee table": "coffee_table",
        "tv stand": "entertainment_center",
        "entertainment": "entertainment_center",
        "bookshelf": "bookshelf",
        "dining table": "dining_table",
        "dining chair": "dining_chair",
        "china cabinet": "china_cabinet",
        "king bed": "king_bed",
        "queen bed": "queen_bed",
        "dresser": "dresser",
        "nightstand": "nightstand",
        "desk": "desk",
        "office chair": "office_chair",
        "refrigerator": "refrigerator",
        "fridge": "refrigerator",
        "washer": "washer",
        "dryer": "dryer",
    }

    for keyword, item_key in furniture_keywords.items():
        if keyword in description_lower:
            item_data = FURNITURE_TYPES[item_key]
            identified_items.append({
                "item": item_key.replace("_", " ").title(),
                "category": item_data["category"],
                "weight_lbs": item_data["avg_weight_lbs"],
                "cubic_feet": item_data["cubic_feet"],
                "handling": item_data["handling"],
            })
            total_estimated_weight += item_data["avg_weight_lbs"]
            total_cubic_feet += item_data["cubic_feet"]

    # Generate analysis result
    result = {
        "analysis_complete": True,
        "standard_items": identified_items,
        "special_items": special_items_found,
        "total_estimated_weight_lbs": total_estimated_weight,
        "total_cubic_feet": total_cubic_feet,
        "handling_notes": list(set(handling_notes)),  # Dedupe
        "special_handling_required": len(special_items_found) > 0,
        "special_item_fees": sum(item.get("special_fee", 0) for item in special_items_found),
        "recommended_insurance": "high_value" if special_items_found else "full_value",
    }

    # Add friendly summary
    if special_items_found:
        special_names = [item["item"] for item in special_items_found]
        result["summary"] = (
            f"I can see you have some valuable items that need special care: {', '.join(special_names)}. "
            f"These will require specialized handling and I recommend full insurance coverage."
        )
    elif identified_items:
        result["summary"] = (
            f"I identified {len(identified_items)} standard items. "
            "These are straightforward to move with our standard crew."
        )
    else:
        result["summary"] = (
            "I couldn't identify specific items from the description. "
            "Could you describe what's in the photo or send another one?"
        )

    logger.info(
        f"[TOOL:PHOTO] Analysis complete: {len(identified_items)} standard, "
        f"{len(special_items_found)} special items"
    )

    return result


# =============================================================================
# Quote Calculation Tools
# =============================================================================


@agents_function_tool
async def calculate_move_quote(
    origin: str,
    destination: str,
    home_size_sqft: int,
    special_items: Optional[list[str]] = None,
    packing_service: str = "self_pack",
) -> dict[str, Any]:
    """
    Calculate a comprehensive moving quote based on move details.

    Args:
        origin: Origin city and state (e.g., "Phoenix, AZ")
        destination: Destination city and state (e.g., "Austin, TX")
        home_size_sqft: Square footage of home (e.g., 2500)
        special_items: List of special items requiring extra handling (e.g., ["baby_grand_piano", "antique_cabinet"])
        packing_service: Packing option - "full_pack", "partial_pack", "fragile_only", or "self_pack"

    Returns:
        Comprehensive quote with itemized breakdown
    """
    logger.info(
        f"[TOOL:QUOTE] Calculating quote: {origin} -> {destination}, "
        f"{home_size_sqft} sqft, special items: {special_items}"
    )

    # Get distance and pricing tier
    distance = get_distance(origin, destination)
    tier = get_pricing_tier(distance)
    pricing = PRICING_MATRIX[tier]

    # Base cost calculation
    base_cost = max(
        home_size_sqft * pricing["base_rate_per_sqft"],
        pricing["min_charge"]
    )

    # Distance cost
    distance_cost = distance * pricing["per_mile"]

    # Truck fee
    truck_fee = pricing["truck_fee"]

    # Special items cost
    special_items_cost = 0
    special_items_detail = []
    if special_items:
        for item_key in special_items:
            item_key_normalized = item_key.lower().replace(" ", "_")
            if item_key_normalized in SPECIAL_ITEMS:
                item_data = SPECIAL_ITEMS[item_key_normalized]
                special_items_cost += item_data["base_fee"]
                special_items_detail.append({
                    "item": item_key_normalized.replace("_", " ").title(),
                    "fee": item_data["base_fee"],
                    "handling": item_data["handling"],
                })

    # Packing cost
    packing_cost = 0
    packing_detail = None
    if packing_service in PACKING_SERVICES:
        packing_data = PACKING_SERVICES[packing_service]
        packing_cost = max(
            home_size_sqft * packing_data["rate_per_sqft"],
            packing_data["min_charge"]
        )
        packing_detail = {
            "service": packing_data["name"],
            "cost": packing_cost,
        }

    # Calculate total
    subtotal = base_cost + distance_cost + truck_fee + special_items_cost + packing_cost

    # Add 15% buffer for estimate range
    total_min = round(subtotal, -1)  # Round to nearest 10
    total_max = round(subtotal * 1.15, -1)

    result = {
        "quote_id": f"AMS-{random.randint(100000, 999999)}",
        "origin": origin,
        "destination": destination,
        "distance_miles": distance,
        "pricing_tier": tier.replace("_", " ").title(),
        "home_size_sqft": home_size_sqft,
        "breakdown": {
            "base_moving_cost": round(base_cost, 2),
            "distance_cost": round(distance_cost, 2),
            "truck_fee": truck_fee,
            "special_items_cost": special_items_cost,
            "packing_cost": packing_cost,
            "subtotal": round(subtotal, 2),
        },
        "special_items": special_items_detail,
        "packing": packing_detail,
        "total_estimate_min": total_min,
        "total_estimate_max": total_max,
        "estimate_range": f"${total_min:,.0f} - ${total_max:,.0f}",
        "valid_for_days": 30,
        "notes": [],
    }

    # Add relevant notes
    if distance > 500:
        result["notes"].append(
            "Long-distance moves include delivery within a 3-5 day window. "
            "We'll confirm exact dates closer to your move."
        )

    if special_items_detail:
        result["notes"].append(
            f"Your {len(special_items_detail)} special item(s) will be handled by our specialty crew."
        )

    if tier == "cross_country":
        result["notes"].append(
            "Cross-country moves may qualify for our vault storage option - "
            "your items stay packed the entire journey."
        )

    logger.info(f"[TOOL:QUOTE] Quote generated: {result['estimate_range']}")

    return result


@agents_function_tool
async def get_insurance_options(declared_value: int, has_special_items: bool = False) -> dict[str, Any]:
    """
    Get available insurance options for a move.

    Args:
        declared_value: Total declared value of items being moved
        has_special_items: Whether move includes high-value items (pianos, antiques, etc.)

    Returns:
        Available insurance options with pricing
    """
    logger.info(f"[TOOL:INSURANCE] Getting options for ${declared_value} value, special: {has_special_items}")

    options = []

    # Basic coverage (always included)
    basic = INSURANCE_OPTIONS["basic"].copy()
    basic["premium"] = 0
    basic["recommended"] = not has_special_items and declared_value < 10000
    options.append(basic)

    # Full value protection
    full_value = INSURANCE_OPTIONS["full_value"].copy()
    full_value["premium"] = round((declared_value / 1000) * full_value["rate_per_thousand"], 2)
    full_value["declared_value"] = declared_value
    full_value["recommended"] = not has_special_items and declared_value >= 10000
    options.append(full_value)

    # High-value items coverage
    if has_special_items:
        high_value = INSURANCE_OPTIONS["high_value"].copy()
        high_value["premium"] = round((declared_value / 1000) * high_value["rate_per_thousand"], 2)
        high_value["declared_value"] = declared_value
        high_value["recommended"] = True
        options.append(high_value)

    return {
        "declared_value": declared_value,
        "has_special_items": has_special_items,
        "options": options,
        "recommendation": (
            "high_value" if has_special_items else
            "full_value" if declared_value >= 10000 else
            "basic"
        ),
    }


@agents_function_tool
async def get_storage_options(estimated_sqft: int, duration_weeks: int) -> dict[str, Any]:
    """
    Get storage options for gap between move-out and move-in dates.

    Args:
        estimated_sqft: Estimated square footage of items to store
        duration_weeks: Expected storage duration in weeks

    Returns:
        Available storage options with pricing
    """
    logger.info(f"[TOOL:STORAGE] Getting options for {estimated_sqft} sqft, {duration_weeks} weeks")

    options = []
    months = max(1, duration_weeks / 4)

    # Short-term storage
    if duration_weeks <= 4:
        short_term = STORAGE_OPTIONS["short_term"].copy()
        cost = max(
            estimated_sqft * short_term["rate_per_sqft_month"] * months,
            short_term["min_charge_month"] * months
        )
        short_term["estimated_cost"] = round(cost, 2)
        short_term["duration_months"] = round(months, 1)
        short_term["recommended"] = True
        options.append(short_term)

    # Long-term storage
    long_term = STORAGE_OPTIONS["long_term"].copy()
    cost = max(
        estimated_sqft * long_term["rate_per_sqft_month"] * months,
        long_term["min_charge_month"] * months
    )
    long_term["estimated_cost"] = round(cost, 2)
    long_term["duration_months"] = round(months, 1)
    long_term["recommended"] = duration_weeks > 4
    options.append(long_term)

    # Vault storage (for larger moves)
    if estimated_sqft > 500:
        vault = STORAGE_OPTIONS["vault_storage"].copy()
        num_vaults = max(1, estimated_sqft // vault["vault_size_sqft"])
        cost = num_vaults * vault["rate_per_vault_month"] * months
        vault["num_vaults"] = num_vaults
        vault["estimated_cost"] = round(cost, 2)
        vault["duration_months"] = round(months, 1)
        vault["recommended"] = False
        options.append(vault)

    return {
        "estimated_sqft": estimated_sqft,
        "duration_weeks": duration_weeks,
        "options": options,
    }


# =============================================================================
# SMS Communication Tools
# =============================================================================


def create_send_quote_sms_tool(tac: TAC, context: ConversationSession) -> Any:
    """
    Create a tool to send quote breakdown via SMS.

    This tool allows the AI to send a formatted quote summary to the customer
    via SMS while continuing the voice conversation.

    Args:
        tac: TAC instance for Twilio client access
        context: ConversationSession with conversation_id and participant info

    Returns:
        Function tool compatible with OpenAI Agents SDK
    """

    async def send_quote_sms_impl(
        quote_summary: str,
        tac_instance: Annotated[TAC, InjectedToolArg],
        conversation_id: Annotated[str, InjectedToolArg],
    ) -> str:
        """
        Send a quote summary via SMS to the customer.

        Args:
            quote_summary: Formatted quote text to send

        Returns:
            Confirmation message
        """
        logger.info(f"[TOOL:SMS_QUOTE] Sending quote via SMS: {quote_summary[:50]}...")

        try:
            # Get customer phone from Maestro participants
            participants = await tac_instance.maestro_client.list_participants(conversation_id)

            customer_phone = None
            for participant in participants:
                if participant.type == "CUSTOMER":
                    for address in participant.addresses:
                        customer_phone = address.address
                        break
                    if customer_phone:
                        break

            if not customer_phone:
                logger.error("[TOOL:SMS_QUOTE] Could not find customer phone number")
                return "Unable to send SMS - customer phone number not found in conversation."

            logger.info(f"[TOOL:SMS_QUOTE] Sending to {customer_phone}")

            # Send SMS using Twilio
            from twilio.rest import Client

            client = Client(
                tac_instance.config.twilio_account_sid,
                tac_instance.config.twilio_auth_token
            )

            message = client.messages.create(
                body=quote_summary,
                from_=tac_instance.config.twilio_phone_number,
                to=customer_phone,
            )

            logger.info(f"[TOOL:SMS_QUOTE] SMS sent successfully: {message.sid}")
            return f"Quote sent via SMS to the customer. They should receive it shortly."

        except Exception as e:
            logger.error(f"[TOOL:SMS_QUOTE] Failed to send SMS: {e}", exc_info=True)
            return f"Failed to send SMS: {str(e)}"

    # Create TAC tool with dependency injection
    tac_tool = function_tool()(send_quote_sms_impl)
    tac_tool.configure_injection(tac_instance=tac, conversation_id=context.conversation_id)

    # Wrap for OpenAI Agents SDK
    @agents_function_tool
    async def send_quote_sms(quote_summary: str) -> str:
        """
        Send a formatted quote summary via SMS to the customer.
        Use this to send quote details, breakdowns, or confirmation while on a voice call.

        Args:
            quote_summary: The formatted quote text to send via SMS

        Returns:
            Confirmation that SMS was sent
        """
        return await tac_tool.implementation(quote_summary=quote_summary)

    return send_quote_sms


def create_acknowledge_photo_sms_tool(tac: TAC, context: ConversationSession) -> Any:
    """
    Create a tool to acknowledge receipt of photo via SMS.

    This tool sends a quick acknowledgment when a customer texts a photo
    while on a voice call.

    Args:
        tac: TAC instance
        context: ConversationSession

    Returns:
        Function tool compatible with OpenAI Agents SDK
    """

    async def acknowledge_photo_impl(
        message: str,
        tac_instance: Annotated[TAC, InjectedToolArg],
        conversation_id: Annotated[str, InjectedToolArg],
    ) -> str:
        """Send photo acknowledgment via SMS."""
        logger.info(f"[TOOL:SMS_ACK] Acknowledging photo: {message[:50]}...")

        try:
            participants = await tac_instance.maestro_client.list_participants(conversation_id)

            customer_phone = None
            for participant in participants:
                if participant.type == "CUSTOMER":
                    for address in participant.addresses:
                        customer_phone = address.address
                        break
                    if customer_phone:
                        break

            if not customer_phone:
                return "Unable to send acknowledgment - phone not found."

            from twilio.rest import Client

            client = Client(
                tac_instance.config.twilio_account_sid,
                tac_instance.config.twilio_auth_token
            )

            client.messages.create(
                body=message,
                from_=tac_instance.config.twilio_phone_number,
                to=customer_phone,
            )

            logger.info(f"[TOOL:SMS_ACK] Acknowledgment sent to {customer_phone}")
            return "Photo acknowledgment sent via SMS."

        except Exception as e:
            logger.error(f"[TOOL:SMS_ACK] Failed: {e}", exc_info=True)
            return f"Failed to send acknowledgment: {str(e)}"

    tac_tool = function_tool()(acknowledge_photo_impl)
    tac_tool.configure_injection(tac_instance=tac, conversation_id=context.conversation_id)

    @agents_function_tool
    async def acknowledge_photo_sms(message: str) -> str:
        """
        Send a quick SMS acknowledgment when customer texts a photo.
        Use this to confirm photo receipt while continuing voice conversation.

        Args:
            message: Short acknowledgment message (e.g., "Got your photo! Analyzing now...")

        Returns:
            Confirmation
        """
        return await tac_tool.implementation(message=message)

    return acknowledge_photo_sms


# =============================================================================
# Company Information Tools
# =============================================================================


@agents_function_tool
async def get_company_info() -> dict[str, Any]:
    """
    Get All My Sons Moving & Storage company information.

    Returns:
        Company details including contact info, hours, and coverage
    """
    return COMPANY_INFO


@agents_function_tool
async def get_packing_options() -> list[dict[str, Any]]:
    """
    Get available packing service options.

    Returns:
        List of packing services with descriptions and pricing
    """
    return [
        {
            "key": key,
            "name": data["name"],
            "description": data["description"],
            "pricing": f"${data['rate_per_sqft']:.2f}/sqft" if data["rate_per_sqft"] > 0 else "Included",
        }
        for key, data in PACKING_SERVICES.items()
    ]
