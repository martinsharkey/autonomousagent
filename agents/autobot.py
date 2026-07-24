from langchain_community.chat_models import ChatOllama
from core.state import AgentState

autobot_llm = ChatOllama(
    model="qwen3.5:4b",
    temperature=0.2,
    base_url="http://localhost:11434"
)

def autobot_node(state: AgentState):
    print(f"\n--- [AUTOBOT] Analyzing State (Loop: {state['loop_count']}) ---")
    response = autobot_llm.invoke(state["messages"])
    return {
        "messages": [response],
        "completed_nodes": ["autobot"]
    }
