import json
from typing import Any, Optional

from fastapi import WebSocket, WebSocketDisconnect

from taf.channels.base import BaseChannel
from taf.core.taf import TAF


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

        msg_type = data.get("type")
        if msg_type == "setup":
            self._handle_setup(conv_id)
        elif msg_type == "prompt":
            self._handle_prompt(conv_id, data)
        elif msg_type == "interrupt":
            self._handle_interrupt(conv_id)

    def _handle_setup(self, conv_id: str) -> None:
        self._start_conversation(
            conv_id,
            "default",  # todo: get profile
        )

    def _handle_prompt(self, conv_id: str, data: dict[str, Any]) -> None:
        """
        Handle incoming voice prompt (user speech).

        Args:
            conv_id: Conversation ID
            data: Message data containing voicePrompt
        """
        if conv_id not in self._conversations:
            self._start_conversation(conv_id, "default")  # todo: get profile

        message_body = data.get("voicePrompt")
        self._add_conversation_messages(conv_id, [{"role": "user", "content": message_body}])

        session = self._conversations[conv_id]

        # Retrieve memory and trigger callback using the session
        self.taf.retrieve_memory(session, query=message_body)

    def _handle_interrupt(self, conv_id: str) -> None:
        self.logger.info("Received interrupt signal from Twilio")

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
