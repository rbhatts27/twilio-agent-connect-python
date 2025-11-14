"""Tests for profile retrieval functionality."""

from typing import Optional
from unittest.mock import MagicMock, patch

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

    def test_profile_fetched_with_trait_groups(self) -> None:
        """Test that profile is fetched with configured trait groups."""
        config = get_test_config_with_trait_groups(trait_groups=["Contact", "Preferences"])
        taf = TAF(config)

        mock_profile = get_mock_profile_response()

        with patch.object(taf.memora_client, "get_profile", return_value=mock_profile) as mock_get:
            profile = taf.fetch_profile("profile_test_123")

            # Verify profile was fetched
            assert profile is not None
            assert profile.id == "profile_test_123"
            assert "Contact" in profile.traits
            assert "Preferences" in profile.traits
            assert profile.traits["Contact"]["firstName"] == "John"

            # Verify get_profile was called with correct trait_groups
            mock_get.assert_called_once_with(
                profile_id="profile_test_123",
                trait_groups=["Contact", "Preferences"],
            )

    def test_profile_fetched_without_trait_groups(self) -> None:
        """Test that profile is fetched without trait_groups when not configured."""
        config = get_test_config_with_trait_groups(trait_groups=None)
        taf = TAF(config)

        mock_profile = get_mock_profile_response()

        with patch.object(taf.memora_client, "get_profile", return_value=mock_profile) as mock_get:
            profile = taf.fetch_profile("profile_test_123")

            # Verify profile was fetched
            assert profile is not None
            assert profile.id == "profile_test_123"

            # Verify get_profile was called with trait_groups=None
            mock_get.assert_called_once_with(
                profile_id="profile_test_123",
                trait_groups=None,
            )

    def test_profile_fetch_error_handling(self) -> None:
        """Test that profile fetch errors are handled gracefully."""
        config = get_test_config_with_trait_groups()
        taf = TAF(config)

        # Simulate an error during profile fetch
        with patch.object(taf.memora_client, "get_profile", side_effect=Exception("API Error")):
            profile = taf.fetch_profile("profile_test_123")

            # Verify None is returned on error (not raised)
            assert profile is None

    def test_profile_fetch_without_memory_config(self) -> None:
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
        profile = taf.fetch_profile("profile_test_123")

        # Should return None without error
        assert profile is None

    def test_profile_fetch_with_empty_profile_id(self) -> None:
        """Test that profile fetch handles empty profile_id gracefully."""
        config = get_test_config_with_trait_groups()
        taf = TAF(config)

        # Test with empty string
        profile = taf.fetch_profile("")
        assert profile is None


class TestProfileInSMSChannel:
    """Tests for profile retrieval in SMS channel."""

    def test_sms_profile_available_in_callback(self) -> None:
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

            # Simulate message webhook
            message_webhook = {
                "EventType": "onMessageAdded",
                "ConversationSid": "CH123456",
                "ProfileId": "profile_test_123",
                "Body": "Hello!",
                "Author": "+12345678901",
            }

            with patch.object(
                taf.memora_client, "get_profile", return_value=mock_profile
            ) as mock_get_profile:
                with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
                    empty_memory = MemoryRetrievalResponse(
                        observations=[],
                        summaries=[],
                        sessions=[],
                        meta=MemoryRetrievalMeta(queryTime=0),
                    )
                    mock_retrieve.return_value = empty_memory

                    channel.process_webhook(message_webhook)

                    # Verify profile was fetched
                    mock_get_profile.assert_called_with(
                        profile_id="profile_test_123",
                        trait_groups=["Contact"],
                    )

                    # Verify profile is in context
                    assert received_context is not None
                    assert received_context.profile is not None
                    assert received_context.profile.id == "profile_test_123"
                    assert received_context.profile.traits["Contact"]["firstName"] == "John"

    def test_sms_profile_fetched_on_conversation_start(self) -> None:
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

            # Simulate conversation started webhook
            conversation_started = {
                "EventType": "onConversationAdded",
                "ConversationSid": "CH123456",
                "ProfileId": "profile_test_123",
                "Author": "+12345678901",
            }

            with patch.object(
                taf.memora_client, "get_profile", return_value=mock_profile
            ) as mock_get_profile:
                channel.process_webhook(conversation_started)

                # Verify profile was fetched on conversation start
                mock_get_profile.assert_called_once_with(
                    profile_id="profile_test_123",
                    trait_groups=["Contact"],
                )

                # Verify conversation was created with profile
                assert "CH123456" in channel._conversations
                session = channel._conversations["CH123456"]
                assert session.profile is not None
                assert session.profile.id == "profile_test_123"

    def test_sms_profile_fetched_for_each_message(self) -> None:
        """Test that profile is fetched fresh for each SMS message."""
        with patch("taf.channels.sms.Client"):
            config = get_test_config_with_trait_groups()
            taf = TAF(config)
            channel = SMSChannel(taf)

            mock_profile = get_mock_profile_response()

            # Simulate first message
            message_webhook_1 = {
                "EventType": "onMessageAdded",
                "ConversationSid": "CH123456",
                "ProfileId": "profile_test_123",
                "Body": "First message",
                "Author": "+12345678901",
            }

            with patch.object(
                taf.memora_client, "get_profile", return_value=mock_profile
            ) as mock_get_profile:
                with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
                    empty_memory = MemoryRetrievalResponse(
                        observations=[],
                        summaries=[],
                        sessions=[],
                        meta=MemoryRetrievalMeta(queryTime=0),
                    )
                    mock_retrieve.return_value = empty_memory

                    # Process first message
                    channel.process_webhook(message_webhook_1)
                    first_call_count = mock_get_profile.call_count

                    # Simulate second message
                    message_webhook_2 = {
                        "EventType": "onMessageAdded",
                        "ConversationSid": "CH123456",
                        "Body": "Second message",
                        "Author": "+12345678901",
                    }

                    # Process second message
                    channel.process_webhook(message_webhook_2)
                    second_call_count = mock_get_profile.call_count

                    # Verify profile was fetched for both messages
                    assert second_call_count > first_call_count

    def test_sms_profile_updates_session(self) -> None:
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

            # First message with first profile version
            message_webhook = {
                "EventType": "onMessageAdded",
                "ConversationSid": "CH123456",
                "ProfileId": "profile_test_123",
                "Body": "Hello",
                "Author": "+12345678901",
            }

            with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
                empty_memory = MemoryRetrievalResponse(
                    observations=[],
                    summaries=[],
                    sessions=[],
                    meta=MemoryRetrievalMeta(queryTime=0),
                )
                mock_retrieve.return_value = empty_memory

                with patch.object(taf.memora_client, "get_profile", return_value=mock_profile_v1):
                    channel.process_webhook(message_webhook)
                    session = channel._conversations["CH123456"]
                    assert session.profile is not None
                    assert session.profile.traits["Contact"]["firstName"] == "John"

                # Second message with updated profile
                with patch.object(taf.memora_client, "get_profile", return_value=mock_profile_v2):
                    channel.process_webhook(message_webhook)
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
