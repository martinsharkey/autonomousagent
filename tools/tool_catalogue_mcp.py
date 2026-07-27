import json
import os
from typing import Dict, List, Optional
from langchain_core.tools import tool

_CATALOGUE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "tool_catalogue.json")

_catalogue_cache: Optional[Dict] = None


def _load_catalogue() -> Dict:
    global _catalogue_cache
    if _catalogue_cache is None:
        with open(_CATALOGUE_PATH, "r", encoding="utf-8") as f:
            _catalogue_cache = json.load(f)
    return _catalogue_cache


def _reload_catalogue() -> Dict:
    global _catalogue_cache
    _catalogue_cache = None
    return _load_catalogue()


@tool
def search_tools_catalogue(query: str, category: Optional[str] = None) -> str:
    """Search the free tool catalogue by name, description, or use case.

    Args:
        query: Search string to match against tool name, description, or agent use case.
        category: Optional category filter. Use list_tool_categories() to see available categories.

    Returns:
        Matching tools as a formatted string with id, name, category, free tier, and access type.
    """
    catalogue = _load_catalogue()
    query_lower = query.lower()
    results = []

    for tool in catalogue.get("tools", []):
        if category and tool.get("category") != category:
            continue

        searchable_text = " ".join([
            tool.get("name", ""),
            tool.get("description", ""),
            tool.get("agent_use_case", ""),
            tool.get("id", "")
        ]).lower()

        if query_lower in searchable_text:
            results.append(tool)

    if not results:
        return f"No tools found matching query '{query}'" + (f" in category '{category}'" if category else "")

    output = f"Found {len(results)} tool(s):\n"
    for tool in results:
        output += (
            f"- {tool['id']}: {tool['name']} [{tool.get('category')}]\n"
            f"  Description: {tool.get('description', '')}\n"
            f"  Free tier: {tool.get('free_tier', 'N/A')}\n"
            f"  Access: {tool.get('access_type', 'N/A')}\n"
        )
    return output


@tool
def get_tool_details(tool_id: str) -> str:
    """Get full details for a specific tool in the catalogue.

    Args:
        tool_id: The tool identifier, e.g. 'vercel' or 'cloudflare-workers'.

    Returns:
        Full tool metadata including URL, auth requirements, rate limits, and agent use cases.
    """
    catalogue = _load_catalogue()
    for tool in catalogue.get("tools", []):
        if tool.get("id") == tool_id:
            return json.dumps(tool, indent=2)
    return f"Tool '{tool_id}' not found in catalogue. Use search_tools_catalogue() to discover tools."


@tool
def list_tool_categories() -> str:
    """List all available tool categories in the catalogue.

    Returns:
        A newline-separated list of categories.
    """
    catalogue = _load_catalogue()
    categories = catalogue.get("categories", [])
    return "Available categories:\n" + "\n".join(f"- {c}" for c in categories)


@tool
def discover_tools_by_use_case(use_case: str) -> str:
    """Discover tools relevant to a specific agent use case.

    Args:
        use_case: Use case keyword such as 'api_testing', 'serverless_functions', 'database', etc.

    Returns:
        Matching tools formatted with id, name, category, and free tier notes.
    """
    catalogue = _load_catalogue()
    use_case_lower = use_case.lower()
    results = []

    for tool in catalogue.get("tools", []):
        agent_use_case = tool.get("agent_use_case", "").lower()
        if use_case_lower in agent_use_case:
            results.append(tool)

    if not results:
        return f"No tools found for use case '{use_case}'."

    output = f"Found {len(results)} tool(s) for use case '{use_case}':\n"
    for tool in results:
        output += (
            f"- {tool['id']}: {tool['name']} [{tool.get('category')}]\n"
            f"  Use cases: {tool.get('agent_use_case', 'N/A')}\n"
            f"  Free tier: {tool.get('free_tier', 'N/A')}\n"
        )
    return output
