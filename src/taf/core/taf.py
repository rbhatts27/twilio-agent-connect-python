"""Core TAF (Twilio Agentic Framework) class for processing events and configuration."""

from typing import Any, Callable, Dict, List, Optional, Union

from pydantic import ValidationError

from taf.context.maestro import MaestroClient
from taf.context.memora import MemoraClient, MemoraMemory
from taf.core.config import TAFConfig
from taf.core.context import ConversationContext
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

        self.memora_client = MemoraClient(
            base_url=self.config.memora_base_url,
            auth_token=self.config.twilio_auth_token,
        )
        self.maestro_client = MaestroClient(
            base_url=self.config.maestro_base_url,
            account_sid=self.config.twilio_account_sid,
        )

        # Callback for when memory is ready
        self._memory_ready_callback: Optional[
            Callable[[ConversationContext, List[MemoraMemory]], None]
        ] = None

    def retrieve_memory(
        self,
        conversation_context: ConversationContext,
        query: Optional[str] = None,
    ) -> List[MemoraMemory]:
        """
        Retrieve memories from Memora and trigger callback with conversation context.

        Args:
            conversation_context: Conversation context containing profile_id and other info
            query: Optional query string for memory retrieval

        Returns:
            List of MemoraMemory objects (TraitMemory, ObservationMemory, or SessionMemory)
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
        self, callback: Callable[[ConversationContext, List[MemoraMemory]], None]
    ) -> None:
        """
        Register a callback to be invoked when memory context is ready.

        The callback will be triggered after memory retrieval is complete
        (after retrieve_memory on MemoraClient) and will receive both the
        conversation context and the retrieved memory data as typed Pydantic models.

        Args:
            callback: A callable that accepts a ConversationContext and a list of MemoraMemory objects.
                     The ConversationContext contains conversation_id, profile_id, needed to send responses.

        Example:
            ```python
            from taf.core.context import ConversationContext
            from taf.context.memora import MemoraMemory

            def handle_memory(context: ConversationContext, memories: List[MemoraMemory]):
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
