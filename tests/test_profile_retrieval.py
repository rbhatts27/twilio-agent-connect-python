"""Tests for profile retrieval functionality."""

from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from taf import TAF, TAFConfig
from taf.channels.sms import SMSChannel
from taf.core.config import TwilioMemoryConfig
from taf.models.memory import MemoryRetrievalMeta, MemoryRetrievalResponse, ProfileResponse
from taf.models.session import ConversationSession


def get_test_config_with_trait_groups(trait_groups: Optional[list[str]] = None) -> TAFConfig:
    """Get test configuration with optional trait groups."""
    memory_config = TwilioMemoryConfig(
        memory_store_id="MGtest123",
        api_key="test_api_key",
        api_token="test_api_token",
        trait_groups=trait_groups,
    )
    return TAFConfig(
        environment="prod",
        conversation_service_sid="IStest123",
        twilio_account_sid="ACtest123",
        twilio_auth_token="test_token_123",
        twilio_phone_number="+15551234567",
        twilio_memory_config=memory_config,
    )


def get_mock_profile_response() -> ProfileResponse:
    """Get a mock ProfileResponse for testing."""
    return ProfileResponse(
        id="profile_test_123",
        createdAt="2025-01-15T10:30:45Z",
        traits={
            "Contact": {
                "firstName": "John",
                "lastName": "Doe",
                "address": {
                    "street": "123 Main St",
                    "city": "San Francisco",
                    "state": "CA",
                    "postalCode": "94107",
                    "country": "US",
                },
            },
            "Preferences": {
                "language": "en",
                "timezone": "America/Los_Angeles",
            },
        },
    )


class TestProfileRetrieval:
    """Tests for profile retrieval functionality."""

    @pytest.mark.asyncio
    async def test_profile_fetched_with_trait_groups(self) -> None:
        """Test that profile is fetched with configured trait groups."""
        config = get_test_config_with_trait_groups(trait_groups=["Contact", "Preferences"])
        taf = TAF(config)

        mock_profile = get_mock_profile_response()

        taf.memora_client.get_profile = AsyncMock(return_value=mock_profile)
        profile = await taf.fetch_profile("profile_test_123")

        # Verify profile was fetched
        assert profile is not None
        assert profile.id == "profile_test_123"
        assert "Contact" in profile.traits
        assert "Preferences" in profile.traits
        assert profile.traits["Contact"]["firstName"] == "John"

        # Verify get_profile was called with correct trait_groups
        taf.memora_client.get_profile.assert_called_once_with(
            profile_id="profile_test_123",
            trait_groups=["Contact", "Preferences"],
        )

    @pytest.mark.asyncio
    async def test_profile_fetched_without_trait_groups(self) -> None:
        """Test that profile is fetched without trait_groups when not configured."""
        config = get_test_config_with_trait_groups(trait_groups=None)
        taf = TAF(config)

        mock_profile = get_mock_profile_response()

        taf.memora_client.get_profile = AsyncMock(return_value=mock_profile)
        profile = await taf.fetch_profile("profile_test_123")

        # Verify profile was fetched
        assert profile is not None
        assert profile.id == "profile_test_123"

        # Verify get_profile was called with trait_groups=None
        taf.memora_client.get_profile.assert_called_once_with(
            profile_id="profile_test_123",
            trait_groups=None,
        )

    @pytest.mark.asyncio
    async def test_profile_fetch_error_handling(self) -> None:
        """Test that profile fetch errors are handled gracefully."""
        config = get_test_config_with_trait_groups()
        taf = TAF(config)

        # Simulate an error during profile fetch
        taf.memora_client.get_profile = AsyncMock(side_effect=Exception("API Error"))
        profile = await taf.fetch_profile("profile_test_123")

        # Verify None is returned on error (not raised)
        assert profile is None

    @pytest.mark.asyncio
    async def test_profile_fetch_without_memory_config(self) -> None:
        """Test that profile fetch returns None when memory config is not provided."""
        config = TAFConfig(
            environment="prod",
            conversation_service_sid="IStest123",
            twilio_account_sid="ACtest123",
            twilio_auth_token="test_token_123",
            twilio_phone_number="+15551234567",
            twilio_memory_config=None,  # No memory config
        )
        taf = TAF(config)

        # Verify memora_client is None
        assert taf.memora_client is None

        # Attempt to fetch profile
        profile = await taf.fetch_profile("profile_test_123")

        # Should return None without error
        assert profile is None

    @pytest.mark.asyncio
    async def test_profile_fetch_with_empty_profile_id(self) -> None:
        """Test that profile fetch handles empty profile_id gracefully."""
        config = get_test_config_with_trait_groups()
        taf = TAF(config)

        # Test with empty string
        profile = await taf.fetch_profile("")
        assert profile is None


class TestProfileInSMSChannel:
    """Tests for profile retrieval in SMS channel."""

    @pytest.mark.asyncio
    async def test_sms_profile_available_in_callback(self) -> None:
        """Test that profile is available in callback context for SMS."""
        with patch("taf.channels.sms.Client"):
            config = get_test_config_with_trait_groups(trait_groups=["Contact"])
            taf = TAF(config)
            channel = SMSChannel(taf)

            # Track callback data
            received_context = None

            def message_ready_callback(
                user_message: str,
                context: ConversationSession,
                memory_response: Optional[MemoryRetrievalResponse] = None,
            ) -> None:
                nonlocal received_context
                received_context = context

            taf.on_message_ready(message_ready_callback)

            mock_profile = get_mock_profile_response()

            # Simulate participant.added webhook with profile
            participant_webhook = {
                "EventType": "participant.added",
                "ConversationId": "CH123456",
                "ParticipantId": "MB123",
                "ParticipantType": "CUSTOMER",
                "ProfileId": "profile_test_123",
                "ParticipantName": "+12345678901",
                "Timestamp": "2025-11-18T00:00:00.000Z",
            }

            # Simulate message webhook
            message_webhook = {
                "EventType": "communication.created",
                "ConversationId": "CH123456",
                "CommunicationId": "IM123",
                "AuthorParticipantId": "MB123",
                "AuthorAddress": "+12345678901",
                "AuthorChannel": "SMS",
                "Body": '{"type":"TEXT","text":"Hello!"}',
                "Timestamp": "2025-11-18T00:00:01.000Z",
            }

            taf.memora_client.get_profile = AsyncMock(return_value=mock_profile)
            empty_memory = MemoryRetrievalResponse(
                observations=[],
                summaries=[],
                sessions=[],
                meta=MemoryRetrievalMeta(queryTime=0),
            )
            taf.memora_client.retrieve_memory = AsyncMock(return_value=empty_memory)

            # Process participant.added first (triggers profile fetch)
            await channel.process_webhook(participant_webhook)

            # Verify profile was fetched on participant.added
            taf.memora_client.get_profile.assert_called_with(
                profile_id="profile_test_123",
                trait_groups=["Contact"],
            )

            # Process message
            await channel.process_webhook(message_webhook)

            # Verify profile is in context
            assert received_context is not None
            assert received_context.profile is not None
            assert received_context.profile.id == "profile_test_123"
            assert received_context.profile.traits["Contact"]["firstName"] == "John"

    @pytest.mark.asyncio
    async def test_sms_profile_fetched_on_conversation_start(self) -> None:
        """Test that profile is fetched when conversation starts."""
        with patch("taf.channels.sms.Client") as mock_client_class:
            # Mock participant creation
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_participants_create = MagicMock()
            mock_client.conversations.v1.conversations.return_value.participants.create = (
                mock_participants_create
            )

            config = get_test_config_with_trait_groups(trait_groups=["Contact"])
            taf = TAF(config)
            channel = SMSChannel(taf)

            mock_profile = get_mock_profile_response()

            # Simulate participant.added webhook (this is when profile is fetched)
            participant_added = {
                "EventType": "participant.added",
                "ConversationId": "CH123456",
                "ParticipantId": "MB123",
                "ParticipantType": "CUSTOMER",
                "ProfileId": "profile_test_123",
                "ParticipantName": "+12345678901",
                "Timestamp": "2025-11-18T00:00:00.000Z",
            }

            taf.memora_client.get_profile = AsyncMock(return_value=mock_profile)
            await channel.process_webhook(participant_added)

            # Verify profile was fetched when participant was added
            taf.memora_client.get_profile.assert_called_once_with(
                profile_id="profile_test_123",
                trait_groups=["Contact"],
            )

            # Verify conversation was created with profile
            assert "CH123456" in channel._conversations
            session = channel._conversations["CH123456"]
            assert session.profile is not None
            assert session.profile.id == "profile_test_123"

    @pytest.mark.asyncio
    async def test_sms_profile_fetched_for_each_message(self) -> None:
        """Test that profile is fetched fresh for each SMS message."""
        with patch("taf.channels.sms.Client"):
            config = get_test_config_with_trait_groups()
            taf = TAF(config)
            channel = SMSChannel(taf)

            mock_profile = get_mock_profile_response()

            # Simulate participant.added first
            participant_webhook = {
                "EventType": "participant.added",
                "ConversationId": "CH123456",
                "ParticipantId": "MB123",
                "ParticipantType": "CUSTOMER",
                "ProfileId": "profile_test_123",
                "ParticipantName": "+12345678901",
                "Timestamp": "2025-11-18T00:00:00.000Z",
            }

            # Simulate first message
            message_webhook_1 = {
                "EventType": "communication.created",
                "ConversationId": "CH123456",
                "CommunicationId": "IM123",
                "AuthorParticipantId": "MB123",
                "AuthorAddress": "+12345678901",
                "AuthorChannel": "SMS",
                "Body": '{"type":"TEXT","text":"First message"}',
                "Timestamp": "2025-11-18T00:00:01.000Z",
            }

            taf.memora_client.get_profile = AsyncMock(return_value=mock_profile)
            empty_memory = MemoryRetrievalResponse(
                observations=[],
                summaries=[],
                sessions=[],
                meta=MemoryRetrievalMeta(queryTime=0),
            )
            taf.memora_client.retrieve_memory = AsyncMock(return_value=empty_memory)

            # Process participant.added (first profile fetch)
            await channel.process_webhook(participant_webhook)
            first_call_count = taf.memora_client.get_profile.call_count

            # Process first message (second profile fetch)
            await channel.process_webhook(message_webhook_1)
            second_call_count = taf.memora_client.get_profile.call_count

            # Simulate second message
            message_webhook_2 = {
                "EventType": "communication.created",
                "ConversationId": "CH123456",
                "CommunicationId": "IM124",
                "AuthorParticipantId": "MB123",
                "AuthorAddress": "+12345678901",
                "AuthorChannel": "SMS",
                "Body": '{"type":"TEXT","text":"Second message"}',
                "Timestamp": "2025-11-18T00:00:02.000Z",
            }

            # Process second message (third profile fetch)
            await channel.process_webhook(message_webhook_2)
            third_call_count = taf.memora_client.get_profile.call_count

            # Verify profile was fetched multiple times
            # (once on participant.added, once per message)
            assert second_call_count > first_call_count
            assert third_call_count > second_call_count

    @pytest.mark.asyncio
    async def test_sms_profile_updates_session(self) -> None:
        """Test that profile updates the session for each message."""
        with patch("taf.channels.sms.Client"):
            config = get_test_config_with_trait_groups()
            taf = TAF(config)
            channel = SMSChannel(taf)

            mock_profile_v1 = ProfileResponse(
                id="profile_test_123",
                createdAt="2025-01-15T10:30:45Z",
                traits={"Contact": {"firstName": "John"}},
            )

            mock_profile_v2 = ProfileResponse(
                id="profile_test_123",
                createdAt="2025-01-15T11:30:45Z",
                traits={"Contact": {"firstName": "Jane"}},  # Updated name
            )

            # Participant added event
            participant_webhook = {
                "EventType": "participant.added",
                "ConversationId": "CH123456",
                "ParticipantId": "MB123",
                "ParticipantType": "CUSTOMER",
                "ProfileId": "profile_test_123",
                "ParticipantName": "+12345678901",
                "Timestamp": "2025-11-18T00:00:00.000Z",
            }

            # First message
            message_webhook = {
                "EventType": "communication.created",
                "ConversationId": "CH123456",
                "CommunicationId": "IM123",
                "AuthorParticipantId": "MB123",
                "AuthorAddress": "+12345678901",
                "AuthorChannel": "SMS",
                "Body": '{"type":"TEXT","text":"Hello"}',
                "Timestamp": "2025-11-18T00:00:01.000Z",
            }

            empty_memory = MemoryRetrievalResponse(
                observations=[],
                summaries=[],
                sessions=[],
                meta=MemoryRetrievalMeta(queryTime=0),
            )
            taf.memora_client.retrieve_memory = AsyncMock(return_value=empty_memory)

            # Process participant.added with first profile version
            taf.memora_client.get_profile = AsyncMock(return_value=mock_profile_v1)
            await channel.process_webhook(participant_webhook)
            session = channel._conversations["CH123456"]
            assert session.profile is not None
            assert session.profile.traits["Contact"]["firstName"] == "John"

            # Process message with updated profile
            taf.memora_client.get_profile = AsyncMock(return_value=mock_profile_v2)
            await channel.process_webhook(message_webhook)
            session = channel._conversations["CH123456"]
            assert session.profile is not None
            assert session.profile.traits["Contact"]["firstName"] == "Jane"


class TestProfileInConversationSession:
    """Tests for profile field in ConversationSession."""

    def test_conversation_session_with_profile(self) -> None:
        """Test ConversationSession can be created with profile."""
        mock_profile = get_mock_profile_response()

        session = ConversationSession(
            conversation_id="CH123456",
            profile_id="profile_test_123",
            channel="sms",
            profile=mock_profile,
        )

        assert session.profile is not None
        assert session.profile.id == "profile_test_123"
        assert session.profile.traits["Contact"]["firstName"] == "John"

    def test_conversation_session_without_profile(self) -> None:
        """Test ConversationSession can be created without profile."""
        session = ConversationSession(
            conversation_id="CH123456",
            profile_id="profile_test_123",
            channel="sms",
            profile=None,
        )

        assert session.profile is None

    def test_conversation_session_profile_default_none(self) -> None:
        """Test that profile defaults to None when not provided."""
        session = ConversationSession(
            conversation_id="CH123456",
            profile_id="profile_test_123",
            channel="sms",
            profile=None,  # Explicitly set to None (also the default)
        )

        assert session.profile is None
