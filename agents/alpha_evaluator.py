import os
from langchain_community.chat_models import ChatOllama
from core.state import AgentState

MODEL_NAME = os.getenv("ALPHA_MODEL", "phi3:mini")
FALLBACK_MODEL = os.getenv("ALPHA_FALLBACK_MODEL", "llama3.2:1b")

try:
    alpha_llm = ChatOllama(
        model=MODEL_NAME,
        temperature=0.1,
        base_url="http://localhost:11434"
    )
    alpha_llm.invoke([{"role": "user", "content": "test"}])
    print(f"[ALPHA] Using model: {MODEL_NAME}")
except Exception as e:
    print(f"[ALPHA] Primary model {MODEL_NAME} failed, using fallback: {FALLBACK_MODEL}")
    alpha_llm = ChatOllama(
        model=FALLBACK_MODEL,
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
