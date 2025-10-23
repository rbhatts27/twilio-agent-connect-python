import json
from typing import Any, Optional

from fastapi import WebSocket, WebSocketDisconnect

from taf.channels.base import BaseChannel
from taf.core.taf import TAF
from taf.models.voice import (
    InterruptMessage,
    PromptMessage,
    SetupMessage,
)


class VoiceChannel(BaseChannel):
    """
    Voice Channel for handling voice-based conversations.

    Inherits conversation lifecycle management from BaseChannel and provides
    voice-specific metadata extraction.
    """

    def __init__(
        self,
        taf: TAF,
    ):
        """
        Initialize Voice channel for websocket protocol handling.

        Args:
            taf: TAF instance for memory/context operations
        """
        super().__init__(taf)

        # Connection tracking (single connection for first version)
        # TODO: Support multiple concurrent calls
        self._active_websocket: Optional[WebSocket] = None
        self._current_conversation_id: Optional[str] = None

    def handle_incoming_call(
        self, websocket_url: str, welcome_greeting: str = "Hello! How can I assist you today?"
    ) -> str:
        """
        Generate TwiML response for incoming voice calls.

        This method creates a new conversation and returns TwiML that connects
        the call to a ConversationRelay WebSocket endpoint.

        Args:
            websocket_url: WebSocket URL for ConversationRelay (e.g., 'wss://example.ngrok.io/ws')
            welcome_greeting: Initial greeting message for the caller.
                            Defaults to "Hello! How can I assist you today?"

        Returns:
            TwiML XML string for call connection
        """
        # Create conversation for this call
        conversation = self.taf.maestro_client.create_conversation()

        # Generate TwiML response
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <ConversationRelay
            url="{websocket_url}"
            welcomeGreeting="{welcome_greeting}"
            debug="debugging">
            <Parameter name="conversationId" value="{conversation.id}" />
        </ConversationRelay>
    </Connect>
</Response>"""

        return twiml

    async def handle_websocket(self, websocket: WebSocket) -> None:
        """
        Handle voice streaming WebSocket connection lifecycle.

        This method manages the entire websocket connection:
        - Accepts the connection
        - Processes incoming messages
        - Cleans up on disconnect

        Args:
            websocket: FastAPI WebSocket instance
        """
        await websocket.accept()
        self.logger.info("WebSocket connection established")

        # Store active websocket
        self._active_websocket = websocket

        try:
            while True:
                # Receive data from Twilio
                data = await websocket.receive_json()
                self.logger.debug(f"Received WebSocket data: {data}")

                # Extract conversation ID
                conv_id = data.get("conversationId") or data.get("callSid")
                if conv_id:
                    self._current_conversation_id = conv_id

                # Route to handler
                self.handle_message(data)

        except WebSocketDisconnect:
            self.logger.info("WebSocket connection closed")
        except Exception as e:
            self.logger.error(f"WebSocket error: {str(e)}")
        finally:
            # Clean up
            self._active_websocket = None
            if self._current_conversation_id:
                self._end_conversation(self._current_conversation_id)
                self._current_conversation_id = None

    # todo: voice does not support webhooks yet
    def process_webhook(self, webhook_data: dict[str, Any]) -> None:
        pass

    async def send_response(
        self, conversation_id: str, response: str, role: Optional[str] = None
    ) -> None:
        """
        Send voice response through the active websocket connection.

        Args:
            conversation_id: Conversation ID
            response: Response text to send
            role: Optional message role (e.g., 'assistant', 'user', 'system')
        """
        if not self._active_websocket:
            self.logger.error(f"No active websocket connection for conversation {conversation_id}")
            return

        self._add_conversation_messages(conversation_id, [{"role": role, "content": response}])

        await self._active_websocket.send_text(
            json.dumps({"type": "text", "token": response, "last": True})
        )

    def get_channel_name(self) -> str:
        return "voice"

    def handle_message(self, data: dict[str, Any]) -> None:
        """
        Handle incoming WebSocket message from Twilio ConversationRelay.

        Args:
            data: Raw message data from Twilio (setup, prompt, interrupt, etc.)
        """
        conv_id = self._current_conversation_id

        if not conv_id:
            self.logger.error("No conversation ID available for message handling")
            return

        # Parse message using Pydantic schemas for validation
        msg_type = data.get("type")
        try:
            if msg_type == "setup":
                setup_msg = SetupMessage(**data)
                self._handle_setup(conv_id, setup_msg)
            elif msg_type == "prompt":
                prompt_msg = PromptMessage(**data)
                self._handle_prompt(conv_id, prompt_msg)
            elif msg_type == "interrupt":
                interrupt_msg = InterruptMessage(**data)
                self._handle_interrupt(conv_id, interrupt_msg)
            else:
                self.logger.warning(f"Unknown message type: {msg_type}")
        except Exception as e:
            self.logger.error(f"Failed to parse message: {str(e)}")

    def _handle_setup(self, conv_id: str, message: SetupMessage) -> None:
        """
        Handle WebSocket setup message.

        Args:
            conv_id: Conversation ID
            message: Parsed SetupMessage containing call metadata
        """
        # Extract profile ID from custom parameters if available
        profile_id = "default"  # Default fallback
        if message.custom_parameters and message.custom_parameters.profile_id:
            profile_id = message.custom_parameters.profile_id

        self._start_conversation(conv_id, profile_id)

    def _handle_prompt(self, conv_id: str, message: PromptMessage) -> None:
        """
        Handle incoming voice prompt (user speech).

        Args:
            conv_id: Conversation ID
            message: Parsed PromptMessage containing user's transcribed speech
        """
        if conv_id not in self._conversations:
            self._start_conversation(conv_id, "default")  # todo: get profile

        message_body = message.voice_prompt or ""
        self._add_conversation_messages(conv_id, [{"role": "user", "content": message_body}])

        session = self._conversations[conv_id]

        # Retrieve memory and trigger callback using the session
        self.taf.retrieve_memory(session, query=message_body)

    def _handle_interrupt(self, conv_id: str, message: InterruptMessage) -> None:
        """
        Handle interrupt message when user interrupts the agent.

        Args:
            conv_id: Conversation ID
            message: Parsed InterruptMessage with interruption details
        """
        self.logger.info(
            f"Received interrupt signal from Twilio - "
            f"utterance: {message.utterance_until_interrupt}, "
            f"duration: {message.duration_until_interrupt_ms}ms"
        )

        # Trigger interrupt callback if conversation exists
        if conv_id in self._conversations:
            session = self._conversations[conv_id]
            self.taf.trigger_interrupt(session, message)
        else:
            self.logger.warning(
                f"Received interrupt for unknown conversation {conv_id}, skipping callback"
            )

    def _add_conversation_messages(self, conv_id: str, messages: list[dict]) -> None:
        """
        Add messages to an existing conversation.

        Args:
            conv_id: Conversation ID
            messages: List of messages to add
        """
        if conv_id not in self._conversations:
            self.logger.warning(f"Conversation {conv_id} does not exist, skipping message addition")
            return
        existing_conv = self._conversations[conv_id]
        existing_conv.messages.extend(messages)

    def _end_conversation(self, conv_id: str) -> None:
        """
        Clean up conversation session and clear websocket connection.

        Args:
            conv_id: Conversation ID
        """
        # Call parent implementation to clean up conversation
        super()._end_conversation(conv_id)

        # Clear active websocket if this was the current conversation
        if self._current_conversation_id == conv_id:
            self._active_websocket = None
            self._current_conversation_id = None
