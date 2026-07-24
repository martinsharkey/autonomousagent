from typing import TypedDict, Annotated, List
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
import operator


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    loop_count: int
    recent_tool_invocations: Annotated[list[str], operator.add]
    completed_nodes: Annotated[list[str], operator.add]
    codebase_hash: str
