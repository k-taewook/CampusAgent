"""
CampusAgent LangGraph 에이전트 그래프
- LLM + 전체 Tool 바인딩 (Task + Calendar + RAG)
- OpenAI / Gemini 자동 감지
- agent → should_continue → tools → agent 순환 구조
"""
import os
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage, SystemMessage

from agent.state import AgentState
from agent.prompts import SYSTEM_PROMPT
from config.settings import (
    LLM_TEMPERATURE, is_llm_available,
    get_llm_provider, get_llm_model,
)
from mcp_servers.task_server import TASK_TOOLS
from mcp_servers.calendar_server import CALENDAR_TOOLS
from mcp_servers.rag_server import RAG_TOOLS

# 전체 도구 리스트 통합
ALL_TOOLS = TASK_TOOLS + CALENDAR_TOOLS + RAG_TOOLS


def _create_llm():
    """LLM provider에 따라 적절한 Chat 모델 생성"""
    provider = get_llm_provider()
    model_name = get_llm_model()

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=LLM_TEMPERATURE,
        )
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_name,
            temperature=LLM_TEMPERATURE,
        )
    return None


def build_graph():
    """LangGraph 에이전트 그래프 생성"""

    # ── 1. 그래프 빌더 초기화 ──
    builder = StateGraph(AgentState)

    # ── 2. LLM 모델 초기화 (Gemini / OpenAI 자동 감지) ──
    model = None
    provider = get_llm_provider()
    model_name = get_llm_model()

    if is_llm_available():
        try:
            base_model = _create_llm()
            if base_model:
                # 전체 Tool 바인딩 — Agent가 모든 도구 호출 가능
                model = base_model.bind_tools(ALL_TOOLS)
                print(f"✅ LLM 초기화 완료 (provider: {provider}, 모델: {model_name}, 도구: {len(ALL_TOOLS)}개)")
        except Exception as e:
            print(f"⚠️ LLM 초기화 실패 ({provider}): {e}")

    system_message = SystemMessage(content=SYSTEM_PROMPT)

    # ── 3. Agent 노드: LLM 호출 ──
    def call_model(state: AgentState):
        messages = state["messages"]

        if model:
            response = model.invoke([system_message] + list(messages))
        else:
            response = AIMessage(
                content=(
                    "⚠️ LLM API 키가 설정되지 않았습니다.\n\n"
                    "`.env` 파일에 다음 중 하나를 추가해주세요:\n\n"
                    "**Gemini (권장):**\n"
                    "```\nGOOGLE_API_KEY=your-gemini-api-key\n```\n\n"
                    "**OpenAI:**\n"
                    "```\nOPENAI_API_KEY=sk-your-key-here\n```\n\n"
                    "설정 후 앱을 재실행하면 모든 기능을 사용할 수 있습니다! 🎓"
                )
            )

        return {"messages": [response]}

    # ── 4. 분기 함수: Tool 호출 여부 판단 ──
    def should_continue(state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]

        # AIMessage에 tool_calls가 있으면 도구 실행
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    # ── 5. 노드 등록 ──
    builder.add_node("agent", call_model)
    builder.add_node("tools", ToolNode(ALL_TOOLS))

    # ── 6. 엣지 연결 ──
    builder.add_edge(START, "agent")

    builder.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END,
        },
    )

    # 도구 실행 후 다시 에이전트로 (결과 해석)
    builder.add_edge("tools", "agent")

    return builder.compile()
