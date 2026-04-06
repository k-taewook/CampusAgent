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
    get_schedules,
    get_user_setting,
    set_user_setting,
    update_assignment_status,
)
from rag.retriever import init_chromadb, get_notice_count
import pandas as pd
from collections import defaultdict
from config.settings import APP_NAME, APP_VERSION, APP_DESCRIPTION, is_llm_available, get_llm_provider, get_llm_model

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
        provider = get_llm_provider()
        model_name = get_llm_model()
        provider_label = "Gemini" if provider == "gemini" else "OpenAI"
        st.success(f"✅ {provider_label} 연결됨 ({model_name})", icon="🤖")
    else:
        st.warning("⚠️ LLM API 키 미설정", icon="🔑")
        st.caption("`.env`에 `GOOGLE_API_KEY` 또는 `OPENAI_API_KEY`를 추가해주세요.")

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
# 메인 영역 (Tabs)
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

tab_chat, tab_dashboard, tab_calendar, tab_settings = st.tabs(["💬 챗봇", "📊 과제 대시보드", "📅 캘린더", "⚙️ 설정"])

with tab_chat:
    # 이전 메시지 출력
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 사용자 입력
    if prompt := st.chat_input("과제, 일정, 공지사항 등에 대해 편하게 물어보세요! 🎓"):
        # 사용자 메시지 표시
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        from datetime import datetime
        current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_major_ctx = get_user_setting("major", "미설정")
        user_grade_ctx = get_user_setting("grade", "미설정")
        config = {"configurable": {"thread_id": "streamlit_session"}}

        with st.chat_message("assistant"):
            with st.spinner("CampusAgent가 생각 중... 🤔"):
                last_msg_content = ""
                try:
                    # AgentState에 맞춰서 messages와 current_context 전달
                    # MemorySaver가 켜져 있으므로 이전 대화들은 그래프 내부에서 자동 누적됨
                    for event in st.session_state.graph.stream(
                        {
                            "messages": [("user", prompt)],
                            "current_context": {
                                "current_time": current_time_str,
                                "user_major": user_major_ctx,
                                "user_grade": user_grade_ctx
                            }
                        }, 
                        config
                    ):
                        for node_name, node_state in event.items():
                            if "messages" in node_state and node_state["messages"]:
                                last_message = node_state["messages"][-1]
                                if last_message.type == "ai" and last_message.content:
                                    last_msg_content = last_message.content

                    if isinstance(last_msg_content, list):
                        # Gemini 등 일부 모델이 텍스트를 [{"type": "text", "text": "..."}] 구조로 반환할 때의 처리
                        parsed_text = ""
                        for item in last_msg_content:
                            if isinstance(item, dict) and "text" in item:
                                parsed_text += item["text"]
                            elif isinstance(item, str):
                                parsed_text += item
                        last_msg_content = parsed_text

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

with tab_dashboard:
    st.markdown("### 📊 과제 대시보드")
    try:
        all_tasks = get_assignments()
        if not all_tasks:
            st.info("📚 등록된 과제가 없습니다. 챗봇에게 과제를 추가해달라고 말해보세요!")
        else:
            df_data = []
            for t in all_tasks:
                df_data.append({
                    "ID": t.id,
                    "완료": t.status == "done",
                    "상태": t.status,
                    "제목": t.title,
                    "과목": t.course_name,
                    "마감일": t.due_date,
                    "우선순위": t.priority,
                })
            df = pd.DataFrame(df_data)
            
            edited_df = st.data_editor(
                df,
                column_config={
                    "ID": None, # Hide ID
                    "완료": st.column_config.CheckboxColumn("완료", help="체크 시 즉시 완료 처리됩니다."),
                    "상태": st.column_config.TextColumn("상태", disabled=True),
                    "제목": st.column_config.TextColumn("과제 제목", disabled=True),
                    "과목": st.column_config.TextColumn("과목명", disabled=True),
                    "마감일": st.column_config.TextColumn("마감일", disabled=True),
                    "우선순위": st.column_config.TextColumn("우선순위", disabled=True),
                },
                disabled=["상태", "제목", "과목", "마감일", "우선순위"],
                hide_index=True,
                use_container_width=True,
                key="task_editor"
            )
            
            # 변경점 감지하여 DB 업데이트
            for i, row in edited_df.iterrows():
                was_done = df.iloc[i]["완료"]
                is_done = row["완료"]
                if was_done != is_done:
                    tid = row["ID"]
                    new_status = "done" if is_done else "pending"
                    update_assignment_status(int(tid), new_status)
                    st.success(f"과제 '{row['제목']}' 상태가 변경되었습니다!")
                    st.rerun()
    except Exception as e:
        st.error(f"대시보드 로딩 실패: {e}")

with tab_calendar:
    st.markdown("### 📅 일정 및 캘린더")
    try:
        schedules = get_schedules()
        if not schedules:
            st.info("📅 등록된 일정이 없습니다. 챗봇에게 일정을 추가해 보세요!")
        else:
            by_date = defaultdict(list)
            for s in schedules:
                by_date[s.date].append(s)
            
            for date_key, items in sorted(by_date.items()):
                with st.expander(f"📅 {date_key}", expanded=True):
                    for s in items:
                        cat_emoji = {"class": "📖", "exam": "📝", "personal": "👤", "meeting": "👥"}.get(s.category, "📌")
                        time_str = f"`{s.start_time}`" if s.start_time else "`하루종일`"
                        if s.start_time and s.end_time:
                            time_str += f" ~ `{s.end_time}`"
                        st.markdown(f"- {cat_emoji} **{s.title}** ({time_str})")
    except Exception as e:
        st.error(f"캘린더 로딩 실패: {e}")

with tab_settings:
    st.markdown("### ⚙️ 사용자 설정")
    st.caption("AI 어시스턴트가 답변할 때 참고할 개인화 정보를 설정하세요.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 👤 개인 정보")
        current_major = get_user_setting("major", "")
        major = st.text_input("🎓 전공 (예: 소프트웨어공학과)", value=current_major)
        
        current_grade = get_user_setting("grade", "1학년")
        grade_options = ["1학년", "2학년", "3학년", "4학년", "5학년 이상", "기타"]
        grade_idx = grade_options.index(current_grade) if current_grade in grade_options else 0
        grade = st.selectbox("📚 학년", grade_options, index=grade_idx)
        
    with col2:
        st.markdown("#### 🔔 개인화 조건")
        current_notify = int(get_user_setting("notify_days", "3"))
        notify_days = st.number_input("⏰ 마감(D-Day) 알림 기준일", min_value=1, max_value=14, value=current_notify)
        
        current_llm = get_user_setting("llm_pref", "Auto")
        llm_options = ["Auto", "Gemini", "OpenAI"]
        llm_idx = llm_options.index(current_llm) if current_llm in llm_options else 0
        llm_pref = st.selectbox("🤖 선호 LLM 엔진", llm_options, index=llm_idx, disabled=True, help="기존 .env 로직에 의해 자동감지 중입니다.")
        
    if st.button("💾 설정 저장", type="primary", use_container_width=True):
        set_user_setting("major", major)
        set_user_setting("grade", grade)
        set_user_setting("notify_days", str(notify_days))
        set_user_setting("llm_pref", llm_pref)
        st.success("설정이 성공적으로 저장되었습니다! 다음 챗봇 대화부터 즉시 반영됩니다.")
