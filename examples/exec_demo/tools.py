"""
Order management and pricing tools for OpenAI Agents SDK.
"""

import logging
from typing import Any, Optional

from agents import function_tool as agents_function_tool
from business_data import COMPANY_INFO, INTERNET_PLANS

from taf import TAF
from taf.core.context import ConversationSession
from taf.tools.messaging import create_messaging_tools

logger = logging.getLogger(__name__)


@agents_function_tool
async def look_up_order_price(plan_speed: str) -> str:
    """Get pricing for internet plan upgrade.

    Args:
        plan_speed: Target internet speed (e.g., "1000 Mbps", "500 Mbps")

    Returns:
        Pricing information for the requested plan
    """
    logger.info(f"[TOOL:PRICING] Called with plan_speed: {plan_speed}")

    # Extract speed number from input
    speed_num = "".join(filter(str.isdigit, plan_speed))
    if not speed_num:
        # Handle text inputs like "gigabit"
        plan_key = plan_speed.lower().replace(" ", "").replace("mbps", "")
        if plan_key in INTERNET_PLANS:
            plan = INTERNET_PLANS[plan_key]
            message = f"The {plan['name']} plan is {plan['price']}/month for {plan_speed} speeds."
            logger.info(f"[TOOL:PRICING] Result: {message}")
            return message

    if speed_num in INTERNET_PLANS:
        plan = INTERNET_PLANS[speed_num]
        message = f"The {plan['name']} plan ({speed_num} Mbps) is {plan['price']}/month."
    else:
        message = f"Pricing for {plan_speed} plans: Contact customer service for custom enterprise pricing at {COMPANY_INFO['phone']}."

    logger.info(f"[TOOL:PRICING] Result: {message}")
    return message


@agents_function_tool
async def look_up_discounts(customer_type: str, current_plan_price: float = 59.99) -> str:
    """Look up available discounts for customer.

    Args:
        customer_type: Customer loyalty tier (loyal, premium, new)
        current_plan_price: Current monthly plan price

    Returns:
        Available discounts and promotions
    """
    logger.info(
        f"[TOOL:DISCOUNTS] Called with customer_type: {customer_type}, "
        f"current_plan_price: {current_plan_price}"
    )

    discounts = []

    # if customer_type.lower() in ["loyal", "premium"]:
    #     # Loyalty discount based on years
    #     if customer_type.lower() == "premium":
    #         discounts.append("20% loyalty discount (5+ year customer)")
    #     else:
    #         discounts.append("10% loyalty discount (2+ year customer)")

    # Autopay discount always available
    # discounts.append("$15/month off with autopay enrollment")

    # Competitor retention offer
    discounts.append("20% off first 6 months (retention offer)")

    if discounts:
        message = f"Available discounts: {', '.join(discounts)}. I can apply the best combination for you!"
    else:
        message = "Let me check for any current promotions that might apply to your account."

    logger.info(f"[TOOL:DISCOUNTS] Result: Found {len(discounts)} discounts")
    return message


def create_confirm_order_tool(taf: TAF, context: ConversationSession) -> Any:
    """
    Create confirm_order tool with injected TAF context for dynamic phone lookup.

    This wraps TAF's send_message tool, deriving the phone number from Maestro
    participants so the LLM doesn't need to provide it.

    Args:
        taf: TAF instance with maestro_client for participant lookup
        context: ConversationSession with conversation_id

    Returns:
        Function tool compatible with OpenAI Agents SDK
    """
    # Get TAF's send_message tool (TAFTool instance)
    messaging_tools = create_messaging_tools(taf.config)
    send_message_impl = messaging_tools[0].implementation  # Extract the actual function

    async def get_customer_phone() -> Optional[str]:
        """Derive customer phone number from Maestro participants."""
        try:
            participants = taf.maestro_client.list_participants(context.conversation_id)

            # Find customer participant with SMS address
            for participant in participants:
                if participant.type == "CUSTOMER":
                    for address in participant.addresses:
                        if address.channel == "SMS":
                            return address.address  # Phone number in E.164 format
            return None
        except Exception as e:
            logger.error(f"Failed to lookup customer phone: {e}")
            return None

    @agents_function_tool
    async def confirm_order(order_details: str = "") -> str:
        """Send order confirmation via SMS to the customer.

        Args:
            order_details: Details of the order to confirm

        Returns:
            Confirmation of message sent
        """
        logger.info(f"[TOOL:CONFIRM] Called with order_details: {order_details[:50]}...")

        # Derive phone number dynamically from Maestro participants
        phone_number = await get_customer_phone()

        logger.info(f"[TOOL:CONFIRM] Derived phone number {phone_number} for customer confirmation")

        if not phone_number:
            logger.error("[TOOL:CONFIRM] Unable to derive customer phone number")
            return "Unable to send confirmation - customer phone number not found."

        logger.info(f"[TOOL:CONFIRM] Sending SMS to: {phone_number}")

        # Use TAF's send_message implementation to send SMS
        success = send_message_impl(phone_number, order_details)

        if success:
            logger.info("[TOOL:CONFIRM] SMS sent successfully")
            return (
                f"Order confirmation sent via SMS! You should receive it shortly with order details"
                f"{f': {order_details}' if order_details else ''}."
            )
        else:
            logger.error("[TOOL:CONFIRM] Failed to send SMS")
            return "Failed to send order confirmation via SMS."

    return confirm_order
