"""Knowledge API tools for the Twilio Agentic Framework."""

import os
from typing import Any, Optional

import requests
from pydantic import BaseModel

from taf.core.config import TAFConfig
from taf.models.knowledge import Knowledge
from taf.tools.base import TAFTool, function_tool


def get_knowledge(config: TAFConfig, knowledge_id: str) -> Knowledge:
    """
    Fetch knowledge metadata from the Knowledge API.

    Args:
        config: TAF configuration containing Twilio auth credentials
        knowledge_id: The knowledge ID to fetch

    Returns:
        Knowledge object with metadata from the API

    Raises:
        requests.HTTPError: If the API request fails
    """
    base_url = os.getenv("KNOWLEDGE_BASE_URL", "https://knowledge.twilio.com")
    url = f"{base_url}/v1/Knowledge/{knowledge_id}"
    headers = {"Content-Type": "application/json"}

    response = requests.get(
        url,
        headers=headers,
        auth=(config.twilio_account_sid, config.twilio_auth_token),
    )
    response.raise_for_status()

    data = response.json()
    return Knowledge(
        id=data["id"],
        name=data["name"],
        description=data.get("description", ""),
        type=data["type"],
    )


class KnowledgeToolConfig(BaseModel):
    """Optional configuration to customize the generated knowledge tool."""

    name: Optional[str] = None  # Override tool name shown to LLM
    description: Optional[str] = None  # Override tool description shown to LLM
    top_k: int = 5  # Number of knowledge chunks to return


def create_knowledge_tool(
    config: TAFConfig,
    knowledge: Knowledge,
    tool_config: Optional[KnowledgeToolConfig] = None,
) -> TAFTool:
    """
    Create a knowledge search tool for the given knowledge.

    Creates a function tool that searches the specified knowledge using Twilio's
    Knowledge Search API. The tool name and description can be customized via
    tool_config, or will default to values derived from the knowledge object.

    Args:
        config: TAF configuration containing Twilio auth credentials
        knowledge: Knowledge object defining the knowledge resource to search
        tool_config: Optional configuration to override tool name, description, or top-K

    Returns:
        A configured TAFTool that searches the specified knowledge
    """
    tool_config = tool_config or KnowledgeToolConfig()

    # Use custom name/description or generate from knowledge
    tool_name = tool_config.name or f"Knowledge: {knowledge.name}"
    tool_description = (
        tool_config.description
        or f"{knowledge.description}\n\nThe input MUST be a question in the form of a string."
    )

    @function_tool(name=tool_name, description=tool_description)
    def search_knowledge(query: str) -> list[dict[str, Any]]:
        """
        Search the knowledge with the given query.

        Args:
            query: The search query string

        Returns:
            List of knowledge chunks with content and relevance scores
        """
        # Support overriding base URL via environment variable for local development
        base_url = os.getenv("KNOWLEDGE_BASE_URL", "https://knowledge.twilio.com")
        url = f"{base_url}/v1/Knowledge/Search"
        headers = {"Content-Type": "application/json"}
        payload = {
            "query": query,
            "knowledge_ids": [knowledge.id],
            "top": tool_config.top_k,  # Map top_k to API's "top" field
        }

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            auth=(config.twilio_account_sid, config.twilio_auth_token),
        )
        response.raise_for_status()
        result: list[dict[str, Any]] = response.json()["chunks"]
        return result

    return search_knowledge


def create_knowledge_tool_from_id(
    config: TAFConfig,
    knowledge_id: str,
    tool_config: Optional[KnowledgeToolConfig] = None,
) -> TAFTool:
    """
    Convenience function to fetch knowledge and create tool in one step.

    Args:
        config: TAF configuration containing Twilio auth credentials
        knowledge_id: The knowledge ID to fetch and create a tool for
        tool_config: Optional configuration to override tool name, description, or top-K

    Returns:
        A configured TAFTool that searches the specified knowledge

    Raises:
        requests.HTTPError: If the API request to fetch knowledge fails

    Example:
        >>> tool = create_knowledge_tool_from_id(
        ...     config, "KN123", KnowledgeToolConfig(name="search_faq", top_k=3)
        ... )
    """
    knowledge = get_knowledge(config, knowledge_id)
    return create_knowledge_tool(config, knowledge, tool_config)


def create_knowledge_tools(
    config: TAFConfig,
    knowledge_list: list[Knowledge],
    tool_configs: Optional[dict[str, KnowledgeToolConfig]] = None,
) -> list[TAFTool]:
    """
    Create multiple knowledge search tools at once.

    Convenience function for creating tools for multiple knowledge resources.
    Each knowledge gets its own dedicated search tool.

    Args:
        config: TAF configuration containing Twilio auth credentials
        knowledge_list: List of Knowledge objects to create tools for
        tool_configs: Optional dict mapping knowledge.id to KnowledgeToolConfig
                     for customizing individual tools

    Returns:
        List of configured TAFTools, one per knowledge

    Example:
        >>> knowledges = [
        ...     Knowledge(id="KN1", name="FAQ", description="FAQs", type="Web"),
        ...     Knowledge(id="KN2", name="Docs", description="Documentation", type="Text"),
        ... ]
        >>> configs = {
        ...     "KN1": KnowledgeToolConfig(name="search_faq", top_k=3),
        ...     "KN2": KnowledgeToolConfig(top_k=10),
        ... }
        >>> tools = create_knowledge_tools(config, knowledges, configs)
    """
    tool_configs = tool_configs or {}
    return [
        create_knowledge_tool(config, knowledge, tool_configs.get(knowledge.id))
        for knowledge in knowledge_list
    ]


def create_knowledge_tools_from_ids(
    config: TAFConfig,
    knowledge_ids: list[str],
    tool_configs: Optional[dict[str, KnowledgeToolConfig]] = None,
) -> list[TAFTool]:
    """
    Convenience function to fetch multiple knowledges and create tools in one step.

    Args:
        config: TAF configuration containing Twilio auth credentials
        knowledge_ids: List of knowledge IDs to fetch and create tools for
        tool_configs: Optional dict mapping knowledge_id to KnowledgeToolConfig
                     for customizing individual tools

    Returns:
        List of configured TAFTools, one per knowledge

    Raises:
        requests.HTTPError: If any API request to fetch knowledge fails

    Example:
        >>> tool_configs = {
        ...     "KN123": KnowledgeToolConfig(name="search_faq", top_k=3),
        ...     "KN456": KnowledgeToolConfig(top_k=10),
        ... }
        >>> tools = create_knowledge_tools_from_ids(config, ["KN123", "KN456"], tool_configs)
    """
    knowledge_list = [get_knowledge(config, kid) for kid in knowledge_ids]
    return create_knowledge_tools(config, knowledge_list, tool_configs)
