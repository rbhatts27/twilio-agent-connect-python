"""Tests for ConversationClient and related models."""

from unittest.mock import Mock, patch

import pytest
import requests

from taf.context.conversation import (
    ConversationClient,
    ConversationRequest,
    ConversationResponse,
    ParticipantRequest,
    ParticipantResponse,
)


class TestConversationModels:
    """Test Pydantic models for conversation API."""

    def test_conversation_response_model(self):
        """Test ConversationResponse model with all fields."""
        response_data = {
            "id": "CH123456",
            "account_id": "AC123456",
            "service_id": "IS123456",
            "status": "active",
            "name": "Test Conversation",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T01:00:00Z",
            "layers": ["layer1", "layer2"],
            "intelligence_agents": ["agent1", "agent2"],
        }

        conversation = ConversationResponse(**response_data)

        assert conversation.id == "CH123456"
        assert conversation.account_id == "AC123456"
        assert conversation.service_id == "IS123456"
        assert conversation.status == "active"
        assert conversation.name == "Test Conversation"
        assert conversation.created_at == "2025-01-01T00:00:00Z"
        assert conversation.updated_at == "2025-01-01T01:00:00Z"
        assert conversation.layers == ["layer1", "layer2"]
        assert conversation.intelligence_agents == ["agent1", "agent2"]

    def test_conversation_response_minimal_fields(self):
        """Test ConversationResponse with only required fields."""
        response_data = {
            "id": "CH123456",
            "account_id": "AC123456",
        }

        conversation = ConversationResponse(**response_data)

        assert conversation.id == "CH123456"
        assert conversation.account_id == "AC123456"
        assert conversation.service_id is None
        assert conversation.status is None
        assert conversation.name is None
        assert conversation.created_at is None
        assert conversation.updated_at is None
        assert conversation.layers == []
        assert conversation.intelligence_agents == []

    def test_conversation_request_model(self):
        """Test ConversationRequest model with all fields."""
        request_data = {
            "name": "Test Conversation",
            "layers": ["layer1", "layer2"],
            "intelligence_agents": ["agent1", "agent2"],
        }

        request = ConversationRequest(**request_data)

        assert request.name == "Test Conversation"
        assert request.layers == ["layer1", "layer2"]
        assert request.intelligence_agents == ["agent1", "agent2"]

    def test_conversation_request_minimal(self):
        """Test ConversationRequest with no fields (all optional)."""
        request = ConversationRequest()

        assert request.name is None
        assert request.layers is None
        assert request.intelligence_agents is None

    def test_conversation_request_model_dump(self):
        """Test ConversationRequest model_dump excludes None values."""
        request = ConversationRequest(name="Test", layers=["layer1"])

        payload = request.model_dump(by_alias=True, exclude_none=True)

        assert payload == {"name": "Test", "layers": ["layer1"]}
        assert "intelligence_agents" not in payload

    def test_participant_request_model(self):
        """Test ParticipantRequest model with all fields."""
        request_data = {
            "name": "John Doe",
            "label": "customer",
            "profile_id": "profile_123",
            "addresses": [{"type": "sms", "address": "+15551234567"}],
        }

        request = ParticipantRequest(**request_data)

        assert request.name == "John Doe"
        assert request.label == "customer"
        assert request.profile_id == "profile_123"
        assert request.addresses == [{"type": "sms", "address": "+15551234567"}]

    def test_participant_request_minimal(self):
        """Test ParticipantRequest with no fields (all optional)."""
        request = ParticipantRequest()

        assert request.name is None
        assert request.label is None
        assert request.profile_id is None
        assert request.addresses == []

    def test_participant_request_model_dump(self):
        """Test ParticipantRequest model_dump excludes None values."""
        request = ParticipantRequest(name="John", profile_id="profile_123")

        payload = request.model_dump(by_alias=True, exclude_none=True)

        # addresses has default_factory=list, so it's included as empty list
        assert payload == {"name": "John", "profile_id": "profile_123", "addresses": []}
        assert "label" not in payload

    def test_participant_response_model(self):
        """Test ParticipantResponse model with all fields."""
        response_data = {
            "id": "MB123456",
            "conversation_id": "CH123456",
            "account_id": "AC123456",
            "service_id": "IS123456",
            "name": "John Doe",
            "label": "customer",
            "profile_id": "profile_123",
            "status": "active",
            "addresses": [{"type": "sms", "address": "+15551234567"}],
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T01:00:00Z",
        }

        participant = ParticipantResponse(**response_data)

        assert participant.id == "MB123456"
        assert participant.conversation_id == "CH123456"
        assert participant.account_id == "AC123456"
        assert participant.service_id == "IS123456"
        assert participant.name == "John Doe"
        assert participant.label == "customer"
        assert participant.profile_id == "profile_123"
        assert participant.status == "active"
        assert participant.addresses == [{"type": "sms", "address": "+15551234567"}]
        assert participant.created_at == "2025-01-01T00:00:00Z"
        assert participant.updated_at == "2025-01-01T01:00:00Z"

    def test_participant_response_minimal_fields(self):
        """Test ParticipantResponse with only required fields."""
        response_data = {
            "id": "MB123456",
            "conversation_id": "CH123456",
            "account_id": "AC123456",
            "name": "John Doe",
        }

        participant = ParticipantResponse(**response_data)

        assert participant.id == "MB123456"
        assert participant.conversation_id == "CH123456"
        assert participant.account_id == "AC123456"
        assert participant.name == "John Doe"
        assert participant.service_id is None
        assert participant.label is None
        assert participant.profile_id is None
        assert participant.status is None
        assert participant.addresses == []
        assert participant.created_at is None
        assert participant.updated_at is None


class TestConversationClient:
    """Test ConversationClient API interactions."""

    def test_client_initialization(self):
        """Test ConversationClient initialization."""
        client = ConversationClient(
            base_url="https://maestro.twilio.com/v1",
            account_sid="AC123456",
            service_id="IS123456",
        )

        assert client.base_url == "https://maestro.twilio.com/v1"
        assert client.account_sid == "AC123456"
        assert client.service_id == "IS123456"
        assert "I-Twilio-Auth-Account" in client.session.headers
        assert client.session.headers["I-Twilio-Auth-Account"] == "AC123456"

    def test_client_initialization_without_account_sid(self):
        """Test ConversationClient initialization without account_sid."""
        client = ConversationClient(base_url="https://maestro.twilio.com/v1")

        assert client.base_url == "https://maestro.twilio.com/v1"
        assert client.account_sid is None
        assert "I-Twilio-Auth-Account" not in client.session.headers

    @patch("requests.Session.post")
    def test_create_conversation_success(self, mock_post):
        """Test successful conversation creation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "CH123456",
            "account_id": "AC123456",
            "service_id": "IS123456",
            "status": "active",
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = ConversationClient(
            base_url="https://maestro.twilio.com/v1",
            account_sid="AC123456",
            service_id="IS123456",
        )

        result = client.create_conversation()

        # Verify API call (headers are set in session, not passed explicitly)
        mock_post.assert_called_once_with(
            "https://maestro.twilio.com/v1/Services/IS123456/Conversations",
            json={},
        )

        # Verify response
        assert isinstance(result, ConversationResponse)
        assert result.id == "CH123456"
        assert result.account_id == "AC123456"

    @patch("requests.Session.post")
    def test_create_conversation_with_parameters(self, mock_post):
        """Test conversation creation with optional parameters."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "CH123456",
            "account_id": "AC123456",
            "service_id": "IS123456",
            "name": "Customer Support",
            "layers": ["layer1", "layer2"],
            "intelligence_agents": ["agent1"],
            "status": "active",
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = ConversationClient(
            base_url="https://maestro.twilio.com/v1",
            account_sid="AC123456",
            service_id="IS123456",
        )

        result = client.create_conversation(
            name="Customer Support",
            layers=["layer1", "layer2"],
            intelligence_agents=["agent1"],
        )

        # Verify API call includes all parameters
        mock_post.assert_called_once_with(
            "https://maestro.twilio.com/v1/Services/IS123456/Conversations",
            json={
                "name": "Customer Support",
                "layers": ["layer1", "layer2"],
                "intelligence_agents": ["agent1"],
            },
        )

        # Verify response
        assert isinstance(result, ConversationResponse)
        assert result.id == "CH123456"
        assert result.name == "Customer Support"
        assert result.layers == ["layer1", "layer2"]
        assert result.intelligence_agents == ["agent1"]

    def test_create_conversation_missing_base_url(self):
        """Test create_conversation fails without base_url."""
        client = ConversationClient(account_sid="AC123456", service_id="IS123456")

        with pytest.raises(ValueError, match="base_url must be configured"):
            client.create_conversation()

    @patch("requests.Session.post")
    def test_create_conversation_api_error(self, mock_post):
        """Test create_conversation handles API errors."""
        mock_post.side_effect = requests.RequestException("API Error")

        client = ConversationClient(
            base_url="https://maestro.twilio.com/v1",
            account_sid="AC123456",
            service_id="IS123456",
        )

        with pytest.raises(requests.RequestException, match="API Error"):
            client.create_conversation()

    @patch("requests.Session.post")
    def test_add_participant_success(self, mock_post):
        """Test successful participant addition."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "MB123456",
            "conversation_id": "CH123456",
            "account_id": "AC123456",
            "service_id": "IS123456",
            "name": "John Doe",
            "profile_id": "profile_123",
            "status": "active",
            "addresses": [],
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T01:00:00Z",
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = ConversationClient(
            base_url="https://maestro.twilio.com/v1",
            account_sid="AC123456",
            service_id="IS123456",
        )

        result = client.add_participant(
            conversation_id="CH123456",
            name="John Doe",
            label="customer",
            profile_id="profile_123",
        )

        # Verify API call (headers are set in session, not passed explicitly)
        expected_url = (
            "https://maestro.twilio.com/v1/Services/IS123456/Conversations/CH123456/Participants"
        )
        mock_post.assert_called_once_with(
            expected_url,
            json={
                "name": "John Doe",
                "label": "customer",
                "profile_id": "profile_123",
                "addresses": [],
            },
        )

        # Verify response
        assert isinstance(result, ParticipantResponse)
        assert result.id == "MB123456"
        assert result.conversation_id == "CH123456"
        assert result.name == "John Doe"

    @patch("requests.Session.post")
    def test_add_participant_with_minimal_params(self, mock_post):
        """Test add_participant with only some optional parameters."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "MB123456",
            "conversation_id": "CH123456",
            "account_id": "AC123456",
            "name": "System",
            "profile_id": "profile_123",
            "status": "active",
            "addresses": [],
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T01:00:00Z",
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = ConversationClient(
            base_url="https://maestro.twilio.com/v1",
            account_sid="AC123456",
            service_id="IS123456",
        )

        result = client.add_participant(
            conversation_id="CH123456",
            name=None,
            label=None,
            profile_id="profile_123",
        )

        # Verify only non-None values are sent (addresses has default_factory so included)
        assert mock_post.call_args[1]["json"] == {"profile_id": "profile_123", "addresses": []}

        # Verify response
        assert isinstance(result, ParticipantResponse)
        assert result.id == "MB123456"

    def test_add_participant_missing_base_url(self):
        """Test add_participant fails without base_url."""
        client = ConversationClient(account_sid="AC123456", service_id="IS123456")

        with pytest.raises(ValueError, match="base_url must be configured"):
            client.add_participant(
                conversation_id="CH123456",
                name="John",
                label=None,
                profile_id="profile_123",
            )

    @patch("requests.Session.post")
    def test_add_participant_api_error(self, mock_post):
        """Test add_participant handles API errors."""
        mock_post.side_effect = requests.RequestException("API Error")

        client = ConversationClient(
            base_url="https://maestro.twilio.com/v1",
            account_sid="AC123456",
            service_id="IS123456",
        )

        with pytest.raises(requests.RequestException, match="API Error"):
            client.add_participant(
                conversation_id="CH123456",
                name="John",
                label=None,
                profile_id="profile_123",
            )

    def test_conversation_client_uses_correct_headers(self):
        """Test that ConversationClient uses correct authentication headers."""
        # Headers are set on the session during initialization, not passed to each call
        client = ConversationClient(
            base_url="https://maestro.twilio.com/v1",
            account_sid="AC123456",
            service_id="IS123456",
        )

        # Verify headers are set in the session
        assert client.session.headers["I-Twilio-Auth-Account"] == "AC123456"
        assert client.session.headers["Content-Type"] == "application/json"

    @patch("requests.Session.post")
    def test_conversation_client_constructs_correct_url(self, mock_post):
        """Test that ConversationClient constructs correct service-scoped URLs."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "CH123456",
            "account_id": "AC123456",
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = ConversationClient(
            base_url="https://maestro.twilio.com/v1",
            account_sid="AC123456",
            service_id="IS999999",
        )

        # Test create_conversation URL
        client.create_conversation()
        assert (
            mock_post.call_args[0][0]
            == "https://maestro.twilio.com/v1/Services/IS999999/Conversations"
        )

        # Test add_participant URL
        mock_response.json.return_value = {
            "id": "MB123456",
            "conversation_id": "CH123456",
            "account_id": "AC123456",
            "name": "Test",
            "profile_id": "profile_123",
            "status": "active",
            "addresses": [],
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T01:00:00Z",
        }

        client.add_participant(
            conversation_id="CH123456", name="Test", label=None, profile_id="profile_123"
        )

        expected_url = (
            "https://maestro.twilio.com/v1/Services/IS999999/Conversations/CH123456/Participants"
        )
        assert mock_post.call_args[0][0] == expected_url
