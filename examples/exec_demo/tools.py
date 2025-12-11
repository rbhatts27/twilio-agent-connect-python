"""
Order management and pricing tools for OpenAI Agents SDK.
"""

import logging
from typing import Annotated, Any, Optional

from agents import function_tool as agents_function_tool
from business_data import COMPANY_INFO, INTERNET_PLANS

from tac import TAC
from tac.models.handoff_data import HandoffData
from tac.models.session import ConversationSession
from tac.tools.base import InjectedToolArg, function_tool

logger = logging.getLogger(__name__)


@agents_function_tool
async def get_available_plans() -> str:
    """Get all available internet plans with their details.

    Returns:
        A formatted string listing all available internet plans with speeds, prices, and descriptions
    """
    logger.info("[TOOL:PLANS] Called get_available_plans")

    plans_list = []
    for speed, plan in INTERNET_PLANS.items():
        # Skip duplicate entries (1gig, gigabit are aliases for 1000)
        if speed in ["1gig", "gigabit"]:
            continue

        plans_list.append(
            f"- {plan['name']} ({speed} Mbps): {plan['price']}/month - {plan['description']}"
        )

    message = "Available Internet Plans:\n" + "\n".join(plans_list)
    logger.info(f"[TOOL:PLANS] Returned {len(plans_list)} plans")
    return message


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
async def look_up_outage(zip_code: str) -> str:
    """Check if there was a recent internet outage in a specific zip code.

    Args:
        zip_code: The zip code to check for outages (e.g., "94103", "10001")

    Returns:
        Information about recent outages in the specified area
    """
    logger.info(f"[TOOL:OUTAGE] Called with zip_code: {zip_code}")

    # Hardcoded to return no outage for now
    has_outage = False

    if has_outage:
        message = f"Yes, we detected a recent internet outage in the {zip_code} area. Our team has resolved the issue and service should be fully restored."
    else:
        message = f"Good news! There are no reported outages in the {zip_code} area. Your service should be operating normally."

    logger.info(f"[TOOL:OUTAGE] Result: has_outage={has_outage}")
    return message


@agents_function_tool
async def run_diagnostic(internet_plan: str, router_model: str) -> str:
    """Run diagnostics to check if customer's router is compatible with their internet plan.

    Args:
        internet_plan: Customer's internet plan speed (e.g., "300", "500", "1000")
        router_model: Customer's router model (e.g., "OWL-R2021", "OWL-R2019", "OWL-X5")

    Returns:
        Diagnostic result indicating if router needs upgrade or is compatible
    """
    logger.info(f"[TOOL:DIAGNOSTIC] Called with plan: {internet_plan}, router: {router_model}")

    # Hardcoded diagnostic result for now
    diagnostic_result = "ROUTER_NEEDS_UPGRADE"

    if diagnostic_result == "ROUTER_NEEDS_UPGRADE":
        message = (
            f"Diagnostic complete: Your {router_model} router needs an upgrade to support "
            f"your {internet_plan} Mbps plan. The current router is limiting your speeds. "
            f"We recommend upgrading to our OWL-X5 router for optimal performance."
        )
    elif diagnostic_result == "ROUTER_COMPATIBLE":
        message = (
            f"Diagnostic complete: Your {router_model} router is fully compatible with "
            f"your {internet_plan} Mbps plan. No upgrade needed."
        )
    else:
        message = (
            "Diagnostic complete: Unable to determine router compatibility. Please contact support."
        )

    logger.info(f"[TOOL:DIAGNOSTIC] Result: {diagnostic_result}")
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


def create_confirm_order_tool(tac: TAC, context: ConversationSession) -> Any:
    """
    Create confirm_order tool with injected TAC context for dynamic phone lookup.

    Uses TAC's function_tool with dependency injection to send SMS via Twilio client,
    deriving the phone number from Maestro participants so the LLM doesn't need to provide it.

    Args:
        tac: TAC instance with maestro_client for participant lookup and Twilio client
        context: ConversationSession with conversation_id

    Returns:
        Function tool compatible with OpenAI Agents SDK
    """

    async def send_sms_via_twilio(
        order_details: str,
        tac_instance: Annotated[TAC, InjectedToolArg],
        conversation_id: Annotated[str, InjectedToolArg],
    ) -> str:
        """Send order confirmation via SMS to the customer.

        Args:
            order_details: Details of the order to confirm

        Returns:
            Confirmation of message sent
        """
        logger.info(f"[TOOL:CONFIRM] Called with order_details: {order_details[:50]}...")

        # Derive phone number dynamically from Maestro participants
        try:
            participants = await tac_instance.maestro_client.list_participants(conversation_id)

            # Find customer participant with SMS address
            customer_phone = None
            for participant in participants:
                if participant.type == "CUSTOMER":
                    for address in participant.addresses:
                        customer_phone = address.address  # Phone number in E.164 format
                        break
                    if customer_phone:
                        break

            if not customer_phone:
                logger.error("[TOOL:CONFIRM] Unable to derive customer phone number")
                return "Unable to send confirmation - customer phone number not found."

            logger.info(
                f"[TOOL:CONFIRM] Derived phone number {customer_phone} for customer confirmation"
            )
            logger.info(f"[TOOL:CONFIRM] Sending SMS to: {customer_phone}")

            # Send SMS using Twilio client directly
            from twilio.rest import Client

            client = Client(
                tac_instance.config.twilio_account_sid, tac_instance.config.twilio_auth_token
            )
            message = client.messages.create(
                body=order_details,
                from_=tac_instance.config.twilio_phone_number,
                to=customer_phone,
            )

            logger.info(f"[TOOL:CONFIRM] SMS sent successfully, SID: {message.sid}")
            return (
                f"Order confirmation sent via SMS! You should receive it shortly with order details"
                f"{f': {order_details}' if order_details else ''}."
            )

        except Exception as e:
            logger.error(f"[TOOL:CONFIRM] Failed to send SMS: {e}", exc_info=True)
            return f"Failed to send order confirmation via SMS: {str(e)}"

    # Create TAC tool with dependency injection
    tac_tool = function_tool()(send_sms_via_twilio)
    tac_tool.configure_injection(tac_instance=tac, conversation_id=context.conversation_id)

    # Wrap the TAC tool's implementation for OpenAI Agents SDK compatibility
    # The implementation property returns an async callable with clean signature
    @agents_function_tool
    async def confirm_order(order_details: str = "") -> str:
        """Send order confirmation via SMS to the customer.

        Args:
            order_details: Details of the order to confirm

        Returns:
            Confirmation of message sent
        """
        # Call the TAC tool implementation
        return await tac_tool.implementation(order_details=order_details)

    return confirm_order


def create_flex_escalation_tool(
    session: Optional[ConversationSession] = None,
) -> Any:
    """
    Create a Flex escalation tool with injected websocket and session context.
    Stores escalation data in session metadata for the channel to handle.
    Args:
        websocket: Active WebSocket connection (if any)
        session: Conversation session for storing escalation metadata
    Returns:
        TACTool instance for escalation
    """

    @agents_function_tool(
        name_override="flex_escalate_to_human",
        description_override="Escalate the conversation to a human agent in Flex with optional reason.",
    )
    def flex_escalate_to_human(reason: str = "User requested human help") -> dict[str, Any]:
        """
        Escalate the conversation to a human agent in Flex.
        Stores handoff data in session metadata for post-response processing.
        Args:
            reason: The reason for escalation (default: user requested human help).
        Returns:
            dict with escalation status and reason.
        """
        handoff_data = HandoffData(reason="handoff", call_summary=reason, sentiment="neutral")
        logger.info(f"[TOOL:FLEX_ESCALATE] Marking conversation for escalation: {handoff_data}")

        # Store escalation data in session metadata
        if session is not None:
            session.metadata["pending_handoff"] = {"handoff_data": handoff_data.model_dump_json()}

        return {"status": "escalated", "reason": reason}

    return flex_escalate_to_human
