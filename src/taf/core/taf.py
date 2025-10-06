"""Core TAF (Twilio Agentic Framework) class for processing events and configuration."""

from typing import Any, Callable, Dict, List, Optional, Union

from pydantic import ValidationError

from taf.context.conversation import ConversationClient
from taf.context.memory import MemoryClient, TwilioMemory
from taf.core.config import TAFConfig
from taf.core.context import ConversationSession
from taf.core.logging import get_logger, setup_logging


class TAF:
    """
    Main Twilio Agentic Framework class for processing webhook events with configuration.

    This class accepts configuration and provides methods to process webhook events.
    """

    def __init__(self, config: Union[TAFConfig, Dict[str, Any]]):
        """
        Initialize TAF instance with configuration.

        Args:
            config: TAFConfig instance or dictionary with configuration settings

        Raises:
            ValueError: If config is invalid
        """
        # Parse and validate configuration
        if isinstance(config, dict):
            try:
                self.config = TAFConfig(**config)
            except ValidationError as e:
                raise ValueError(f"Invalid configuration: {e}")
        elif isinstance(config, TAFConfig):
            self.config = config
        else:
            raise ValueError("Config must be TAFConfig instance or dictionary")

        # Setup logging
        setup_logging(log_level=self.config.log_level)
        self.logger = get_logger(__name__)

        # TODO comment here to change this to be f"{self.config.twilio_account_sid}:{self.config.twilio_auth_token}"
        # when memora can support this properly
        self.memora_client = MemoryClient(
            base_url=self.config.memora_base_url,
            auth_token=self.config.twilio_auth_token,
        )
        self.maestro_client = ConversationClient(
            base_url=self.config.maestro_base_url,
            account_sid=self.config.twilio_account_sid,
        )

        # Callback for when memory is ready
        self._memory_ready_callback: Optional[
            Callable[[ConversationSession, List[TwilioMemory]], None]
        ] = None

    def retrieve_memory(
        self,
        conversation_context: ConversationSession,
        query: Optional[str] = None,
    ) -> List[TwilioMemory]:
        """
        Retrieve memories from Memora and trigger callback with conversation context.

        Args:
            conversation_context: Conversation context containing profile_id and other info
            query: Optional query string for memory retrieval

        Returns:
            List of TwilioMemory objects (TraitMemory, ObservationMemory, or SessionMemory)
        """
        try:
            memories = self.memora_client.retrieve_memory(
                service_id=self.config.memory_service_sid,
                profile_id=conversation_context.profile_id,
                query=query,
            )

            # Trigger the memory ready callback if registered
            if self._memory_ready_callback:
                self._memory_ready_callback(conversation_context, memories)

            return memories
        except Exception as e:
            self.logger.error(f"Failed to retrieve memory: {e}")
            raise

    def on_memory_ready(
        self, callback: Callable[[ConversationSession, List[TwilioMemory]], None]
    ) -> None:
        """
        Register a callback to be invoked when memory context is ready.

        The callback will be triggered after memory retrieval is complete
        (after retrieve_memory on MemoryClient) and will receive both the
        conversation context and the retrieved memory data as typed Pydantic models.

        Args:
            callback: A callable that accepts a ConversationSession and a list of TwilioMemory objects.
                     The ConversationSession contains conversation_id, profile_id, needed to send responses.

        Example:
            ```python
            from taf.core.context import ConversationSession
            from taf.context.memory import TwilioMemory

            def handle_memory(context: ConversationSession, memories: List[TwilioMemory]):
                print(f"Conversation {context.conversation_id} on {context.channel}")
                print(f"Received {len(memories)} memory items")

                for memory in memories:
                    if memory.mem_type == 'TRAIT':
                        print(f"Trait: {memory.name} = {memory.value}")

                # Send response back through the channel
                # channel.send_response(context.conversation_id, llm_response)

            taf = TAF(config)
            taf.on_memory_ready(handle_memory)
            ```
        """
        self._memory_ready_callback = callback
        self.logger.info("Memory ready callback registered.")
