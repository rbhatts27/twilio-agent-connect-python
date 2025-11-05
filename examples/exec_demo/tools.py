"""
Order management and pricing tools for OpenAI Agents SDK.
"""

import asyncio
import json
import logging
from typing import Any, Optional

from agents import function_tool
from business_data import COMPANY_INFO, INTERNET_PLANS
from fastapi import WebSocket

from taf.models.handoff_data import HandoffData
from taf.tools.base import TAFTool

logger = logging.getLogger(__name__)


@function_tool
async def look_up_order_price(plan_speed: str) -> str:
    """Get pricing for internet plan upgrade.

    Args:
        plan_speed: Target internet speed (e.g., "1000 Mbps", "500 Mbps")

    Returns:
        Pricing information for the requested plan
    """
    logger.info(f"Looking up pricing for: {plan_speed}")

    # Extract speed number from input
    speed_num = "".join(filter(str.isdigit, plan_speed))
    if not speed_num:
        # Handle text inputs like "gigabit"
        plan_key = plan_speed.lower().replace(" ", "").replace("mbps", "")
        if plan_key in INTERNET_PLANS:
            plan = INTERNET_PLANS[plan_key]
            message = f"The {plan['name']} plan is {plan['price']}/month for {plan_speed} speeds."
            return message

    if speed_num in INTERNET_PLANS:
        plan = INTERNET_PLANS[speed_num]
        message = f"The {plan['name']} plan ({speed_num} Mbps) is {plan['price']}/month."
    else:
        message = f"Pricing for {plan_speed} plans: Contact customer service for custom enterprise pricing at {COMPANY_INFO['phone']}."

    return message


@function_tool
async def look_up_discounts(customer_type: str, current_plan_price: float = 59.99) -> str:
    """Look up available discounts for customer.

    Args:
        customer_type: Customer loyalty tier (loyal, premium, new)
        current_plan_price: Current monthly plan price

    Returns:
        Available discounts and promotions
    """
    logger.info(f"Looking up discounts for: {customer_type}")

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

    return message


@function_tool
async def confirm_order(
    confirmation_channel: str, conversation_uid: str, order_details: str = ""
) -> str:
    """Send order confirmation via customer's preferred channel.

    Args:
        confirmation_channel: Preferred channel (SMS, email, phone)
        conversation_uid: Unique conversation identifier
        order_details: Details of the order to confirm

    Returns:
        Confirmation of message sent
    """
    logger.info(
        f"Sending confirmation via {confirmation_channel} for conversation {conversation_uid}"
    )

    # In a real implementation, this would integrate with Twilio's messaging APIs
    # For demo, we simulate cross-channel confirmation

    if confirmation_channel.lower() == "sms":
        message = (
            f"Order confirmation sent via SMS! You should receive it shortly with order details"
            f"{f': {order_details}' if order_details else ''}."
        )
    elif confirmation_channel.lower() == "email":
        message = (
            f"Order confirmation sent to your email address on file"
            f"{f' with details: {order_details}' if order_details else ''}."
        )
    else:
        message = f"Confirmation will be sent via {confirmation_channel} as requested."
    return message


def create_flex_escalation_tool(
    websocket: Optional[WebSocket] = None,
) -> TAFTool:
    """
    Create a Flex escalation tool with injected websocket context.
    This tool, when called, will end the websocket and signal handoff intent.
    Args:
        websocket: Active WebSocket connection (if any)
    Returns:
        TAFTool instance for escalation
    """

    @function_tool(
        name="flex_escalate_to_human",
        description="Escalate the conversation to a human agent in Flex with optional reason.",
    )
    def flex_escalate_to_human(reason: str = "User requested human help") -> dict[str, Any]:
        """
        Escalate the conversation to a human agent in Flex, ending websocket and signaling handoff
        Args:
            reason: The reason for escalation (default: user requested human help).
        Returns:
            dict with escalation status and reason.
        """
        if websocket is not None:
            handoff_data = HandoffData(reason="handoff", call_summary=reason, sentiment="neutral")
            asyncio.create_task(
                websocket.send_text(
                    json.dumps({"type": "end", "handoffData": handoff_data.model_dump_json()})
                )
            )
        return {"status": "escalated", "reason": reason}

    return flex_escalate_to_human
