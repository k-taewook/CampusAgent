import os
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, SystemMessage

from agent.state import AgentState

def build_graph():
    # 1. 그래프 빌더 초기화
    builder = StateGraph(AgentState)
    
    # 2. LLM 모델 초기화 (에러 회피 등 방어적 로직 포함)
    try:
        model = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    except Exception as e:
        model = None
        
    system_prompt = SystemMessage(content="""
당신은 'CampusAgent'입니다. 대학생들의 학교 공지사항과 개인 일정/과제를 관리해주는 친절한 로컬 AI 어시스턴트입니다.
현재 시스템은 3주차 (기초 뼈대 구축) 단계에 있으므로 모든 도구를 사용할 수는 없습니다.
인사를 건네면 반갑게 맞이하고, 초기 뼈대 시스템이 구동 중임을 알려주세요.
""")
        
    # 3. 모델 호출 노드 (가장 핵심)
    def call_model(state: AgentState):
        messages = state['messages']
        
        if model:
            # 시스템 프롬프트 주입
            response = model.invoke([system_prompt] + list(messages))
        else:
            response = AIMessage(content="환경변수(.env)에 OPENAI_API_KEY가 등록되지 않아 더미 텍스트로 응답합니다.")
            
        return {"messages": [response]}
        
    # 추후 MCP가 연결될 도구 실행 노드
    def tool_execution(state: AgentState):
        pass # 현재는 도구를 구현 전
        
    # 상태에 Tools 요청이 있으면 분기 처리
    def should_continue(state: AgentState):
        messages = state['messages']
        last_message = messages[-1]
        
        if last_message.tool_calls:
            return "tools"
        return END

    # 4. 노드 추가
    builder.add_node("agent", call_model)
    builder.add_node("tools", tool_execution)
    
    # 5. 엣지 연결
    builder.add_edge(START, "agent")
    
    builder.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END
        }
    )
    builder.add_edge("tools", "agent") 
    
    return builder.compile()
