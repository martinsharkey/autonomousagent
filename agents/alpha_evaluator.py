from langchain_community.chat_models import ChatOllama
from core.state import AgentState

alpha_llm = ChatOllama(
    model="phi4-mini",
    temperature=0.1,
    base_url="http://localhost:11434"
)

def alpha_node(state: AgentState):
    print(f"\n--- [ALPHA] Evaluating State (Loop: {state['loop_count']}) ---")
    response = alpha_llm.invoke(state["messages"])
    return {
        "messages": [response],
        "completed_nodes": ["alpha_evaluator"]
    }
