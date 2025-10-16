"""Core TAF (Twilio Agentic Framework) class for processing events and configuration."""

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import Any, Optional, Union

from pydantic import ValidationError

from taf.context.conversation import ConversationClient
from taf.context.memory import MemoryClient, TraitQuery, TwilioMemory
from taf.core.config import TAFConfig
from taf.core.context import ConversationSession
from taf.core.logging import get_logger, setup_logging


class TAF:
    """
    Main Twilio Agentic Framework class for processing webhook events with configuration.

    This class accepts configuration and provides methods to process webhook events.
    """

    def __init__(self, config: Union[TAFConfig, dict[str, Any]]):
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
                raise ValueError(f"Invalid configuration: {e}") from e
        elif isinstance(config, TAFConfig):
            self.config = config
        else:
            raise ValueError("Config must be TAFConfig instance or dictionary")

        # Setup logging
        setup_logging(log_level=self.config.log_level)
        self.logger = get_logger(__name__)

        # TODO: Change this to use account_sid:auth_token format when Memora supports it
        # f"{self.config.twilio_account_sid}:{self.config.twilio_auth_token}"
        self.memora_client = MemoryClient(
            base_url=self.config.memora_base_url,
            auth_token=self.config.twilio_auth_token,
        )
        self.maestro_client = ConversationClient(
            base_url=self.config.maestro_base_url,
            account_sid=self.config.twilio_account_sid,
            service_id=self.config.conversation_service_sid,
        )

        # Callback for when memory is ready (supports both sync and async)
        self._memory_ready_callback: Optional[
            Union[
                Callable[[ConversationSession, list[TwilioMemory], str], None],
                Callable[[ConversationSession, list[TwilioMemory], str], Awaitable[None]],
            ]
        ] = None

    def retrieve_memory(
        self,
        conversation_context: ConversationSession,
        query: Optional[str] = None,
        traits: Optional[list[TraitQuery]] = None,
    ) -> list[TwilioMemory]:
        """
        Retrieve memories from Memora and trigger callback with conversation context.

        Args:
            conversation_context: Conversation context containing profile_id and other info
            query: Optional query string for memory retrieval (typically the user's message)
            traits: Optional list of specific traits to retrieve (trait group + names)

        Returns:
            List of TwilioMemory objects (TraitMemory, ObservationMemory, or SessionMemory)
        """
        try:
            memories = self.memora_client.retrieve_memory(
                service_id=self.config.memory_service_sid,
                profile_id=conversation_context.profile_id,
                query=query,
                traits=traits,
            )

            # Trigger the memory ready callback if registered
            if self._memory_ready_callback:
                # Check if callback is async
                if inspect.iscoroutinefunction(self._memory_ready_callback):
                    # Schedule async callback as a background task
                    try:
                        asyncio.create_task(
                            self._memory_ready_callback(conversation_context, memories, query or "")
                        )
                    except RuntimeError:
                        # No event loop running, log warning
                        self.logger.warning(
                            "Async callback registered but no event loop running. "
                            "Callback will not be executed."
                        )
                else:
                    # Call sync callback directly
                    self._memory_ready_callback(conversation_context, memories, query or "")

            return memories
        except Exception as e:
            self.logger.error(f"Failed to retrieve memory: {e}")
            raise

    def on_memory_ready(
        self,
        callback: Union[
            Callable[[ConversationSession, list[TwilioMemory], str], None],
            Callable[[ConversationSession, list[TwilioMemory], str], Awaitable[None]],
        ],
    ) -> None:
        """
        Register a callback to be invoked when memory context is ready.

        The callback will be triggered after memory retrieval is complete
        (after retrieve_memory on MemoryClient) and will receive the conversation context,
        retrieved memory data, and the user's message that triggered the retrieval.

        Supports both synchronous and asynchronous callbacks. Async callbacks
        will be scheduled as background tasks using asyncio.create_task().

        Args:
            callback: A callable that accepts:
                     - ConversationSession: Contains conversation_id, profile_id for responses
                     - list[TwilioMemory]: Retrieved memories (traits, observations, sessions)
                     - str: The user's message (query) that triggered memory retrieval

        Example (Synchronous):
            ```python
            from taf.core.context import ConversationSession
            from taf.context.memory import TwilioMemory


            def handle_memory(
                context: ConversationSession, memories: List[TwilioMemory], user_message: str
            ):
                print(f"Conversation {context.conversation_id} on {context.channel}")
                print(f"User message: {user_message}")
                print(f"Received {len(memories)} memory items")

                for memory in memories:
                    if memory.mem_type == "TRAIT":
                        print(f"Trait: {memory.name} = {memory.value}")

                # Process user message with LLM using memories
                # llm_response = llm.process(user_message, memories)

                # Send response back through the channel
                # channel.send_response(context.conversation_id, llm_response)


            taf = TAF(config)
            taf.on_memory_ready(handle_memory)
            ```

        Example (Asynchronous):
            ```python
            async def handle_memory(context: ConversationSession, memories: list[TwilioMemory]):
                print(f"Conversation {context.conversation_id} on {context.channel}")

                # Call async operations directly
                response = await call_llm(context.messages)
                await voice_channel.send_response(context.conversation_id, response)


            taf = TAF(config)
            taf.on_memory_ready(handle_memory)
            ```
        """
        self._memory_ready_callback = callback
