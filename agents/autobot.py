import os
from langchain_community.chat_models import ChatOllama
from core.state import AgentState

MODEL_NAME = os.getenv("AUTOBOT_MODEL", "qwen3.5:4b")
FALLBACK_MODEL = os.getenv("AUTOBOT_FALLBACK_MODEL", "llama3.2:1b")

try:
    autobot_llm = ChatOllama(
        model=MODEL_NAME,
        temperature=0.2,
        base_url="http://localhost:11434"
    )
    autobot_llm.invoke([{"role": "user", "content": "test"}])
    print(f"[AUTOBOT] Using model: {MODEL_NAME}")
except Exception as e:
    print(f"[AUTOBOT] Primary model {MODEL_NAME} failed, using fallback: {FALLBACK_MODEL}")
    autobot_llm = ChatOllama(
        model=FALLBACK_MODEL,
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
