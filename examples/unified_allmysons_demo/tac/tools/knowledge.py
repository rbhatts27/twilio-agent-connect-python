"""Knowledge API tools for the Twilio Agent Connect."""

from typing import Annotated, Any, Optional

from pydantic import BaseModel

from tac.context.memory import MemoryClient
from tac.models.knowledge import KnowledgeBase
from tac.tools.base import InjectedToolArg, TACTool, function_tool


class KnowledgeToolConfig(BaseModel):
    """Optional configuration to customize the generated knowledge tool."""

    name: Optional[str] = None
    description: Optional[str] = None
    top_k: int = 5  # Number of knowledge chunks to return


async def search_knowledge(
    query: str,
    memory_client: Annotated[MemoryClient, InjectedToolArg],
    knowledge_base_id: Annotated[str, InjectedToolArg],
    top_k: Annotated[int, InjectedToolArg],
) -> list[dict[str, Any]]:
    """
    Search the knowledge base with the given query.
    Args:
        query: The search query string
    Returns:
        List of knowledge chunks with content and relevance scores
    """
    return await memory_client.search_knowledge_base(
        knowledge_base_id=knowledge_base_id,
        query=query,
        top_k=top_k,
    )


def create_knowledge_tool(
    memory_client: MemoryClient,
    knowledge_base: KnowledgeBase,
    tool_config: Optional[KnowledgeToolConfig] = None,
) -> TACTool:
    """
    Create a knowledge search tool for the given knowledge.
    Creates a function tool that searches the specified knowledge using Twilio's
    Knowledge Base Search API via MemoryClient. The tool uses dependency injection
    to hide the memory client and knowledge ID from the LLM schema.
    Args:
        memory_client: MemoryClient instance for searching knowledge bases
        knowledge: Knowledge object defining the knowledge resource to search
        tool_config: Optional configuration to override tool name, description, or top-K
    Returns:
        A configured TACTool that searches the specified knowledge with injected dependencies
    Example:
        >>> tool = create_knowledge_tool(
        ...     memory_client=tac.memory_client,
        ...     knowledge_base=knowledge_base
        ...     tool_config=KnowledgeToolConfig(top_k=3),
        ... )
        >>> # LLM only sees: search_knowledge(query: str)
        >>> result = await tool(query="What is TAC?")
    """
    tool_config = tool_config or KnowledgeToolConfig()

    # Use custom name/description or generate from knowledge
    tool_name = tool_config.name or f"search_{knowledge_base.name.lower().replace(' ', '_')}"
    tool_description = (
        tool_config.description
        or f"{knowledge_base.description}\n\nThe input MUST be a question in the form of a string."
    )

    # Wrap the standalone search_knowledge function with the tool decorator
    knowledge_tool = function_tool(name=tool_name, description=tool_description)(search_knowledge)

    # Configure injection
    return knowledge_tool.configure_injection(
        memory_client=memory_client,
        knowledge_base_id=knowledge_base.id,
        top_k=tool_config.top_k,
    )
