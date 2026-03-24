import streamlit as st
import os
from dotenv import load_dotenv

from agent.graph import build_graph
from database.db import init_sqlite_db
from rag.retriever import init_chromadb

# 환경변수 로딩
load_dotenv()

st.set_page_config(page_title="CampusAgent", page_icon="🎓")

st.title("🎓 CampusAgent UI")
st.subheader("대학생 특화 로컬 AI 어시스턴트")

# 세션 상태 초기화 (대화 기록 보존)
if "messages" not in st.session_state:
    st.session_state.messages = []
if "graph" not in st.session_state:
    st.session_state.graph = build_graph()
    # 데이터베이스 초기화
    init_sqlite_db()
    init_chromadb()

# 이전 메시지 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 사용자 입력
if prompt := st.chat_input("공지사항, 과제 등에 대해 편하게 물어보세요!"):
    # 사용자 메시지 UI에 추가
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # LangGraph 호출
    config = {"configurable": {"thread_id": "streamlit_session"}}
    
    with st.chat_message("assistant"):
        with st.spinner("Agent가 생각 중..."):
            last_msg_content = ""
            try:
                # 스트리밍 방식 처리
                for event in st.session_state.graph.stream({"messages": [("user", prompt)]}, config):
                    for node_name, node_state in event.items():
                        if "messages" in node_state and node_state["messages"]:
                            last_message = node_state["messages"][-1]
                            if last_message.type == "ai":
                                last_msg_content = last_message.content
                st.markdown(last_msg_content)
                st.session_state.messages.append({"role": "assistant", "content": last_msg_content})
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
