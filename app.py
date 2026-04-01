"""
CampusAgent — Streamlit 메인 애플리케이션
"""
import streamlit as st
from dotenv import load_dotenv

from agent.graph import build_graph
from database.db import (
    init_sqlite_db,
    get_assignments,
    get_upcoming_assignments,
    get_today_schedules,
    get_dday_schedules,
)
from rag.retriever import init_chromadb, get_notice_count
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
# 사이드바: 시스템 정보 + 대시보드
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

    # ── 과제 대시보드 ──
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
            st.markdown("**⏰ 3일 이내 마감:**")
            for task in upcoming:
                st.markdown(f"- {task.title} ({task.due_date})")
    except Exception:
        st.caption("DB 초기화 후 표시됩니다.")

    st.divider()

    # ── 오늘 일정 ──
    st.markdown("### 📅 오늘 일정")
    try:
        today_events = get_today_schedules()
        if today_events:
            for event in today_events:
                time_str = f" {event.start_time}" if event.start_time else ""
                st.markdown(f"- {event.title}{time_str}")
        else:
            st.caption("오늘 일정이 없습니다.")
    except Exception:
        st.caption("DB 초기화 후 표시됩니다.")

    # ── D-day ──
    try:
        dday_list = get_dday_schedules(category="exam")
        if dday_list:
            st.markdown("**📝 시험 D-day:**")
            for d in dday_list[:3]:
                st.markdown(f"- {d['display']}")
    except Exception:
        pass

    st.divider()

    # ── 공지사항 현황 ──
    st.markdown("### 🔍 공지사항 RAG")
    try:
        notice_count = get_notice_count()
        st.metric("저장된 문서", f"{notice_count}건")
    except Exception:
        st.caption("ChromaDB 초기화 후 표시됩니다.")

    st.divider()

    st.markdown(
        "### 💡 사용 예시\n"
        "- 자료구조 과제 추가해줘\n"
        "- 내일 9시에 수업 추가\n"
        "- 장학금 공지 검색해줘\n"
        "- 시험 D-day 확인\n"
        "- 이번 주 일정 보여줘"
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
if prompt := st.chat_input("과제, 일정, 공지사항 등에 대해 편하게 물어보세요! 🎓"):
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
