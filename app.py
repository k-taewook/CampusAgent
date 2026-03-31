"""
CampusAgent — Streamlit 메인 애플리케이션
"""
import streamlit as st
from dotenv import load_dotenv

from agent.graph import build_graph
from database.db import init_sqlite_db, get_assignments, get_upcoming_assignments
from rag.retriever import init_chromadb
from config.settings import APP_NAME, APP_VERSION, APP_DESCRIPTION, is_llm_available

# 환경변수 로딩
load_dotenv()

# ──────────────────────────────────────
# 페이지 설정
# ──────────────────────────────────────
st.set_page_config(
    page_title=f"{APP_NAME} v{APP_VERSION}",
    page_icon="🎓",
    layout="wide",
)

# ──────────────────────────────────────
# 사이드바: 시스템 정보 + 과제 대시보드
# ──────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎓 CampusAgent")
    st.caption(f"v{APP_VERSION} — {APP_DESCRIPTION}")
    st.divider()

    # API 키 상태 표시
    if is_llm_available():
        st.success("✅ LLM 연결됨", icon="🤖")
    else:
        st.warning("⚠️ OPENAI_API_KEY 미설정", icon="🔑")
        st.caption("`.env` 파일에 키를 추가해주세요.")

    st.divider()

    # 과제 대시보드 (미니)
    st.markdown("### 📋 과제 현황")
    try:
        all_tasks = get_assignments()
        pending = [t for t in all_tasks if t.status == "pending"]
        in_progress = [t for t in all_tasks if t.status == "in_progress"]
        done = [t for t in all_tasks if t.status == "done"]

        col1, col2, col3 = st.columns(3)
        col1.metric("대기", len(pending))
        col2.metric("진행중", len(in_progress))
        col3.metric("완료", len(done))

        # 마감 임박 과제
        upcoming = get_upcoming_assignments(days=3)
        if upcoming:
            st.divider()
            st.markdown("### ⏰ 3일 이내 마감")
            for task in upcoming:
                st.markdown(f"- **{task.title}** ({task.course_name})\n  📅 {task.due_date}")
    except Exception:
        st.caption("DB 초기화 후 표시됩니다.")

    st.divider()
    st.markdown(
        "### 💡 사용 예시\n"
        "- 자료구조 과제 추가해줘\n"
        "- 내 과제 목록 보여줘\n"
        "- 1번 과제 완료 처리해줘\n"
        "- 이번 주 마감인 과제 알려줘"
    )

# ──────────────────────────────────────
# 메인 영역
# ──────────────────────────────────────
st.title("🎓 CampusAgent")
st.subheader("대학생 특화 로컬 AI 어시스턴트")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "graph" not in st.session_state:
    init_sqlite_db()
    init_chromadb()
    st.session_state.graph = build_graph()

# 이전 메시지 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 사용자 입력
if prompt := st.chat_input("과제 관리, 공지사항 등에 대해 편하게 물어보세요! 🎓"):
    # 사용자 메시지 표시
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # LangGraph 호출
    config = {"configurable": {"thread_id": "streamlit_session"}}

    with st.chat_message("assistant"):
        with st.spinner("CampusAgent가 생각 중... 🤔"):
            last_msg_content = ""
            try:
                for event in st.session_state.graph.stream(
                    {"messages": [("user", prompt)]}, config
                ):
                    for node_name, node_state in event.items():
                        if "messages" in node_state and node_state["messages"]:
                            last_message = node_state["messages"][-1]
                            # AI 최종 응답만 추출
                            if last_message.type == "ai" and last_message.content:
                                last_msg_content = last_message.content

                if last_msg_content:
                    st.markdown(last_msg_content)
                else:
                    last_msg_content = "처리가 완료되었지만 응답 내용이 비어있습니다."
                    st.markdown(last_msg_content)

                st.session_state.messages.append(
                    {"role": "assistant", "content": last_msg_content}
                )
            except Exception as e:
                error_msg = f"❌ 오류가 발생했습니다: {e}"
                st.error(error_msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_msg}
                )
