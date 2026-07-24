import os
from langchain_community.chat_models import ChatOllama
from core.state import AgentState

MODEL_NAME = os.getenv("BETA_MODEL", "deepseek-coder:1.3b")
FALLBACK_MODEL = os.getenv("BETA_FALLBACK_MODEL", "llama3.2:1b")

try:
    beta_llm = ChatOllama(
        model=MODEL_NAME,
        temperature=0.3,
        base_url="http://localhost:11434"
    )
    beta_llm.invoke([{"role": "user", "content": "test"}])
    print(f"[BETA] Using model: {MODEL_NAME}")
except Exception as e:
    print(f"[BETA] Primary model {MODEL_NAME} failed, using fallback: {FALLBACK_MODEL}")
    beta_llm = ChatOllama(
        model=FALLBACK_MODEL,
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
