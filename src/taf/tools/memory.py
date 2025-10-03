"""Memory API tools for the Twilio Agentic Framework."""

from typing import Any, Dict, List

import requests

from taf.core.config import TAFConfig
from taf.core.context import SessionIdentity
from taf.tools.base import TAFTool, function_tool


def create_memory_tools(config: TAFConfig, session: SessionIdentity) -> List[TAFTool]:
    """
    Create memory tools with injected configuration and session context.

    Args:
        config: TAF configuration containing API URLs, auth tokens, and service SIDs
        session: Current session identity with profile and conversation IDs

    Returns:
        List of configured memory tools
    """

    @function_tool()
    def retrieve_profile_memory(query: str) -> Dict[str, Any]:
        """
        Search and retrieve relevant memories for the current profile.

        Performs semantic search across the user's conversation history, observations,
        and stored traits to find contextually relevant information.

        Args:
            query: What to search for in the user's memory (e.g., "preferences about food", "previous complaints", "contact information")

        Returns:
            Dictionary containing relevant memories, traits, and metadata
        """
        # Use injected config and session context
        url = f"{config.memora_base_url}/services/{config.memory_service_sid}/Profiles/{session.profile_id}/Recall"
        headers = {
            "Authorization": f"Bearer {config.twilio_auth_token}",
            "Content-Type": "application/json",
        }
        payload = {"conversationId": session.conversation_id, "query": query}

        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    return [retrieve_profile_memory]
