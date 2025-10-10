import logging

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from taf.core.config import TAFConfig
from taf.tools import TAFTool
from taf.tools.base import function_tool

logger = logging.getLogger(__name__)


def create_messaging_tools(config: TAFConfig) -> list[TAFTool]:
    client = Client(config.twilio_account_sid, config.twilio_auth_token)

    @function_tool()
    def send_message(phone_number: str, message: str) -> bool:
        """
        Sends a message to a user.

        Args:
            phone_number (str): The phone number of the user to send the message to.
            message (str): The message content.

        Returns:
            bool: True on success, False on failure.
        """
        logger.debug(f"Sending message to {phone_number}: {message}")
        try:
            client.messages.create(to=phone_number, from_=config.twilio_phone_number, body=message)
            logger.info(f"Message sent to {phone_number}: {message}")
            return True
        except TwilioRestException as e:
            logger.error(f"Failed to send message to {phone_number}: {e}")
            return False

    return [send_message]
