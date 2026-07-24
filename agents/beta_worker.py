from langchain_community.chat_models import ChatOllama
from core.state import AgentState

beta_llm = ChatOllama(
    model="deepseek-coder:1.3b",
    temperature=0.3,
    base_url="http://localhost:11434"
)

def beta_node(state: AgentState):
    print(f"\n--- [BETA] Executing State (Loop: {state['loop_count']}) ---")
    response = beta_llm.invoke(state["messages"])
    return {
        "messages": [response],
        "completed_nodes": ["beta_worker"]
    }
