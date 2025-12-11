"""Core TAC (Twilio Agent Connect) class for processing events and configuration."""

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import Any, Optional, Union

from fastapi import Response
from fastapi.datastructures import FormData
from pydantic import ValidationError

from tac.context.conversation import ConversationClient
from tac.context.memory import MemoryClient
from tac.core.config import TACConfig
from tac.core.logging import get_logger, setup_logging
from tac.models.memory import (
    MemoryRetrievalResponse,
    ProfileResponse,
)
from tac.models.session import ConversationSession


class TAC:
    _handoff_callback: Optional[Callable[[FormData], Awaitable[Response]]] = None

    def on_handoff(
        self,
        callback: Callable[[FormData], Awaitable[Response]],
    ) -> None:
        """
        Register a callback to be invoked when a handoff event occurs (e.g., Flex handoff).

        The callback will be triggered by the channel when a handoff is required.
        Supports both synchronous and asynchronous callbacks.
        """
        self._handoff_callback = callback

    """
    Main Twilio Agent Connect class for processing webhook events with configuration.

    This class accepts configuration and provides methods to process webhook events.
    """

    def __init__(self, config: Union[TACConfig, dict[str, Any]]):
        """
        Initialize TAC instance with configuration.

        Args:
            config: TACConfig instance or dictionary with configuration settings

        Raises:
            ValueError: If config is invalid
        """
        # Parse and validate configuration
        if isinstance(config, dict):
            try:
                self.config = TACConfig(**config)
            except ValidationError as e:
                raise ValueError(f"Invalid configuration: {e}") from e
        elif isinstance(config, TACConfig):
            self.config = config
        else:
            raise ValueError("Config must be TACConfig instance or dictionary")

        # Setup logging
        setup_logging(log_level=self.config.log_level, log_format="console")
        self.logger = get_logger(__name__)

        # Initialize Memora client only if memory config is provided
        self.memora_client: Optional[MemoryClient] = None
        if self.config.twilio_memory_config:
            self.memora_client = MemoryClient(
                base_url=self.config.memora_base_url,
                store_id=self.config.twilio_memory_config.memory_store_id,
                api_key=self.config.twilio_memory_config.api_key,
                api_token=self.config.twilio_memory_config.api_token,
            )
            self.logger.info("Twilio Memory client initialized")

        self.maestro_client = ConversationClient(
            base_url=self.config.maestro_base_url,
            account_sid=self.config.twilio_account_sid,
            auth_token=self.config.twilio_auth_token,
            service_id=self.config.conversation_service_sid,
        )

        # Callback for when message is ready (supports both sync and async)
        self._message_ready_callback: Optional[
            Union[
                Callable[[str, ConversationSession, Optional[MemoryRetrievalResponse]], None],
                Callable[
                    [str, ConversationSession, Optional[MemoryRetrievalResponse]], Awaitable[None]
                ],
            ]
        ] = None

        # Callback for when user interrupts the agent (supports both sync and async)
        self._interrupt_callback: Optional[
            Union[
                Callable[[ConversationSession, Any], None],
                Callable[[ConversationSession, Any], Awaitable[None]],
            ]
        ] = None

    def is_twilio_memory_enabled(self) -> bool:
        """
        Check if Twilio Memory functionality is enabled.

        Returns:
            True if twilio_memory_config is provided and memory client is initialized,
            False otherwise.
        """
        return self.config.twilio_memory_config is not None

    async def retrieve_memory(
        self,
        conversation_context: ConversationSession,
        query: Optional[str] = None,
    ) -> MemoryRetrievalResponse:
        """
        Retrieve memories from Memora or fallback to Maestro communications.

        Args:
            conversation_context: Conversation context containing profile_id and other info
            query: Optional query string for memory retrieval (used only with Memora)

        Returns:
            MemoryRetrievalResponse containing observations, summaries, communications, and metadata

        Behavior:
            - If Memora is configured (twilio_memory_config provided):
              Fetches full memory including observations, summaries, and communications
              Requires profile_id in conversation_context
            - If Memora is NOT configured:
              Falls back to Maestro Communications API to fetch only communications
              Observations and summaries arrays will be empty

        Raises:
            ValueError: If Memora is configured but profile_id is missing
            httpx.HTTPError: If the API request fails
        """
        # Check if Memora is configured
        if self.memora_client and self.config.twilio_memory_config:
            # Original Memora path - requires profile_id
            if not conversation_context.profile_id:
                raise ValueError(
                    "profile_id is required for memory retrieval but was not found in "
                    "conversation context. Ensure profile_id is provided when creating "
                    "the ConversationSession."
                )

            try:
                memory_response = await self.memora_client.retrieve_memory(
                    profile_id=conversation_context.profile_id,
                    conversation_id=conversation_context.conversation_id,
                    query=query,
                )
                return memory_response
            except Exception as e:
                self.logger.error(f"Failed to retrieve memory from Memora: {e}")
                raise

        else:
            # Fallback to Maestro Communications API
            self.logger.info(
                "Twilio Memory not configured, falling back to Maestro Communications API"
            )

            try:
                # Fetch communications from Maestro
                communications = await self.maestro_client.list_communications(
                    conversation_id=conversation_context.conversation_id
                )

                # Return MemoryRetrievalResponse with only communications populated
                return MemoryRetrievalResponse(
                    communications=communications,
                )
            except Exception as e:
                self.logger.error(f"Failed to retrieve communications from Maestro: {e}")
                raise

    async def fetch_profile(self, profile_id: str) -> Optional[ProfileResponse]:
        """
        Fetch profile information with traits for a given profile ID.

        This method retrieves profile data including traits from Twilio Memory.
        If trait_groups are configured in TwilioMemoryConfig, only those trait
        groups will be included in the response.

        Args:
            profile_id: Profile ID using Twilio Type ID (TTID) format

        Returns:
            ProfileResponse with id, created_at, and traits, or None if fetch fails
        """
        # Check if memory client is initialized
        if not self.memora_client or not self.config.twilio_memory_config:
            self.logger.warning(
                "Memory client is not initialized. Cannot fetch profile. "
                "Provide twilio_memory_config when creating TACConfig to enable profile fetching."
            )
            return None

        # Validate profile_id
        if not profile_id:
            self.logger.warning("profile_id is required for profile fetching but was not provided")
            return None

        try:
            # Get trait_groups from config if provided
            trait_groups = self.config.twilio_memory_config.trait_groups

            # Fetch profile
            profile_response = await self.memora_client.get_profile(
                profile_id=profile_id,
                trait_groups=trait_groups,
            )
            return profile_response

        except Exception as e:
            self.logger.error(f"Failed to fetch profile for {profile_id}: {e}")
            return None

    def on_message_ready(
        self,
        callback: Union[
            Callable[[str, ConversationSession, Optional[MemoryRetrievalResponse]], None],
            Callable[
                [str, ConversationSession, Optional[MemoryRetrievalResponse]], Awaitable[None]
            ],
        ],
    ) -> None:
        """
        Register a callback to be invoked when a message is ready to be processed.

        The callback will be triggered by channels when a new user message arrives,
        regardless of whether memory was fetched. This allows different channels
        (SMS, Voice) to handle memory retrieval differently.

        Supports both synchronous and asynchronous callbacks. Async callbacks
        will be scheduled as background tasks using asyncio.create_task().

        Args:
            callback: A callable that accepts:
                     - str: The user's message content
                     - ConversationSession: Contains conversation_id, profile_id, channel
                     - Optional[MemoryRetrievalResponse]: Retrieved memory data
                       (None for voice channel)

        Example (Synchronous):
            ```python
            from tac.core.context import ConversationSession
            from tac.models.memory import MemoryRetrievalResponse
            from typing import Optional


            def handle_message(
                user_message: str,
                context: ConversationSession,
                memory_response: Optional[MemoryRetrievalResponse],
            ):
                print(f"User message: {user_message}")
                print(f"Conversation {context.conversation_id} on {context.channel}")

                if memory_response:
                    print(f"Observations: {len(memory_response.observations)}")
                    print(f"Summaries: {len(memory_response.summaries)}")
                    print(f"Sessions: {len(memory_response.sessions)}")

                # Process user message with LLM
                # llm_response = llm.process(user_message, memory_response)

                # Send response back through the channel
                # channel.send_response(context.conversation_id, llm_response)


            tac = TAC(config)
            tac.on_message_ready(handle_message)
            ```

        Example (Asynchronous):
            ```python
            async def handle_message(
                user_message: str,
                context: ConversationSession,
                memory_response: Optional[MemoryRetrievalResponse],
            ):
                print(f"Message on {context.channel}: {user_message}")

                # Call async operations directly
                response = await call_llm(user_message, memory_response)
                await channel.send_response(context.conversation_id, response)


            tac = TAC(config)
            tac.on_message_ready(handle_message)
            ```
        """
        self._message_ready_callback = callback

    async def trigger_message_ready(
        self,
        user_message: str,
        conversation_context: ConversationSession,
        memory_response: Optional[MemoryRetrievalResponse] = None,
    ) -> None:
        """
        Trigger the registered message ready callback.

        This method is called by channels when a new message is ready to be processed.
        Different channels can call this with or without memory based on their needs.

        Args:
            user_message: The user's message content
            conversation_context: Conversation context with conversation_id, profile_id, channel
            memory_response: Optional memory retrieval response (None for voice channel)
        """
        if self._message_ready_callback:
            # Check if callback is async
            if inspect.iscoroutinefunction(self._message_ready_callback):
                # Await async callback
                await self._message_ready_callback(
                    user_message, conversation_context, memory_response
                )
            else:
                # Call sync callback directly
                self._message_ready_callback(user_message, conversation_context, memory_response)

    def on_interrupt(
        self,
        callback: Union[
            Callable[[ConversationSession, Any], None],
            Callable[[ConversationSession, Any], Awaitable[None]],
        ],
    ) -> None:
        """
        Register a callback to be invoked when user interrupts the agent.

        The callback will be triggered when the user interrupts the agent's response
        (e.g., in voice conversations when the user starts speaking while the agent
        is still talking). This allows developers to handle interruptions appropriately,
        such as canceling ongoing tool calls, stopping LLM generation, or logging events.

        Supports both synchronous and asynchronous callbacks. Async callbacks
        will be scheduled as background tasks using asyncio.create_task().

        Args:
            callback: A callable that accepts:
                     - ConversationSession: Contains conversation_id, profile_id, channel
                     - InterruptMessage: Details about the interruption (utterance_until_interrupt,
                       duration_until_interrupt_ms)

        Example (Synchronous):
            ```python
            from tac.core.context import ConversationSession
            from tac.models.voice import InterruptMessage


            def handle_interrupt(
                context: ConversationSession,
                interrupt_data: InterruptMessage,
            ):
                print(f"User interrupted conversation {context.conversation_id}")
                print(f"Interrupted at: {interrupt_data.utterance_until_interrupt}")
                print(f"Duration: {interrupt_data.duration_until_interrupt_ms}ms")

                # Cancel ongoing operations, stop LLM generation, etc.
                cancel_pending_operations(context.conversation_id)


            tac = TAC(config)
            tac.on_interrupt(handle_interrupt)
            ```

        Example (Asynchronous):
            ```python
            async def handle_interrupt(
                context: ConversationSession,
                interrupt_data: InterruptMessage,
            ):
                print(f"User interrupted on {context.channel}")

                # Cancel async operations
                await cancel_llm_generation(context.conversation_id)

                # Log to analytics
                await log_interrupt_event(context, interrupt_data)


            tac = TAC(config)
            tac.on_interrupt(handle_interrupt)
            ```
        """
        self._interrupt_callback = callback

    def trigger_interrupt(
        self,
        conversation_context: ConversationSession,
        interrupt_data: Any,
    ) -> None:
        """
        Trigger the registered interrupt callback.

        This method is called by channels when an interrupt event occurs.

        Args:
            conversation_context: Conversation context with conversation_id, profile_id, channel
            interrupt_data: Interrupt details (InterruptMessage for voice channel)
        """
        if self._interrupt_callback:
            # Check if callback is async
            if inspect.iscoroutinefunction(self._interrupt_callback):
                # Schedule async callback as a background task
                try:
                    asyncio.create_task(
                        self._interrupt_callback(conversation_context, interrupt_data)
                    )
                except RuntimeError:
                    # No event loop running, log warning
                    self.logger.warning(
                        "Async interrupt callback registered but no event loop running. "
                        "Callback will not be executed."
                    )
            else:
                # Call sync callback directly
                self._interrupt_callback(conversation_context, interrupt_data)
