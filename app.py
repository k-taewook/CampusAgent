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
    update_subtask_status,
    get_assignments_with_progress,
    get_or_create_conversation_session,
    load_recent_conversation_messages,
    save_conversation_message,
    get_latest_memory_summary,
)
from rag.retriever import init_chromadb, get_notice_count
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

CONVERSATION_SESSION_ID = "streamlit_session"

if "db_initialized" not in st.session_state:
    init_sqlite_db()
    get_or_create_conversation_session(CONVERSATION_SESSION_ID, "Streamlit 기본 세션")
    st.session_state.db_initialized = True


def _format_chat_error(error: Exception) -> str:
    """채팅 처리 중 발생한 주요 오류를 사용자에게 친숙한 안내로 변환합니다."""
    raw_message = str(error)
    normalized = raw_message.lower()

    temporary_llm_unavailable = (
        "503" in normalized
        or "unavailable" in normalized
        or "high demand" in normalized
        or "overloaded" in normalized
    )
    if temporary_llm_unavailable:
        return (
            "⚠️ Gemini 모델이 현재 일시적으로 혼잡해서 요청을 처리하지 못했습니다.\n\n"
            "잠시 후 같은 요청을 다시 보내주세요. 과제나 일정이 실제로 등록됐는지 애매하면 "
            "대시보드에서 한 번 확인해주세요."
        )

    return f"❌ 오류가 발생했습니다: {raw_message}"


st.markdown(
    """
    <style>
    header[data-testid="stHeader"],
    div[data-testid="stToolbar"] {
        display: none !important;
    }
    div[data-testid="stDecoration"],
    #MainMenu {
        display: none !important;
    }
    div.block-container {
        padding-top: 1.25rem !important;
    }
    section[data-testid="stSidebar"] > div:first-child,
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        padding-top: 0.75rem !important;
    }
    section[data-testid="stSidebar"] h2 {
        margin-top: -5rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
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

    # ── 🚨 긴급 알림 ──
    st.markdown("### 🚨 긴급 알림")
    has_urgent = False
    
    try:
        upcoming = get_upcoming_assignments(days=1)
        if upcoming:
            has_urgent = True
            for task in upcoming:
                st.error(f"⏰ 오늘 마감: {task.title}")
    except Exception: pass

    try:
        today_events = get_today_schedules()
        if today_events:
            has_urgent = True
            for event in today_events:
                st.warning(f"📅 오늘 일정: {event.title}")
    except Exception: pass
        
    try:
        dday_list = get_dday_schedules(category="exam")
        if dday_list:
            d = dday_list[0]
            if d["d_day"] <= 3:
                has_urgent = True
                st.error(f"📝 {d['display']}")
    except Exception: pass
        
    if not has_urgent:
        st.success("🎉 긴급한 일정이 없습니다! 평화로운 하루 되세요.")

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
        "- 편입학 정보 알려줘\n"
        "- 국가장학금 제도 찾아줘\n"
        "- 소프트웨어 공모전 추천해줘\n"
        "- 시험 D-day 확인\n"
        "- 이번 주 일정 보여줘"
    )

# ──────────────────────────────────────
# 메인 영역 (Tabs)
# ──────────────────────────────────────
st.markdown("### 🎓 CampusAgent")

# 세션 상태 초기화
if "messages" not in st.session_state:
    restored_messages = load_recent_conversation_messages(
        CONVERSATION_SESSION_ID,
        limit=20,
    )
    st.session_state.messages = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in restored_messages
        if msg["role"] in {"user", "assistant"}
    ]
    st.session_state.graph_memory_hydrated = not bool(st.session_state.messages)
if "graph" not in st.session_state:
    init_chromadb()
    st.session_state.graph = build_graph()

tab_chat, tab_dashboard, tab_calendar, tab_settings = st.tabs(["💬 챗봇", "📊 과제 대시보드", "📅 캘린더", "⚙️ 설정"])

with tab_chat:
    st.markdown(
        """
        <style>
        div.block-container {
            padding-top: 1.25rem;
            padding-bottom: 0;
        }
        div[data-testid="stChatInput"] {
            position: fixed;
            left: 23rem;
            right: 3rem;
            bottom: 0;
            z-index: 1000;
            padding: 0.75rem 0 1rem 0;
            background: var(--background-color);
            border-top: 1px solid rgba(128, 128, 128, 0.2);
        }
        div[data-testid="stChatInput"] > div {
            width: 100%;
            max-width: none;
            margin: 0 auto;
        }
        .campus-chat-bottom-spacer {
            height: 5rem;
        }
        @media (max-width: 900px) {
            div[data-testid="stChatInput"] {
                left: 1rem;
                right: 1rem;
            }

        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 대화 내용만 위에서 아래로 스크롤 가능하도록 컨테이너 지정
    chat_container = st.container(height=600, border=False)
    
    with chat_container:
        # 이전 메시지 출력
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # 사용자 입력
    user_input = st.chat_input("과제, 일정, 공지사항 등에 대해 편하게 물어보세요! 🎓")
    st.markdown('<div class="campus-chat-bottom-spacer"></div>', unsafe_allow_html=True)
    
    prompt = user_input
    if "quick_prompt" in st.session_state:
        prompt = st.session_state.quick_prompt
        del st.session_state["quick_prompt"]
        
    if prompt:
        with chat_container:
            # 사용자 메시지 표시
            st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        try:
            save_conversation_message(CONVERSATION_SESSION_ID, "user", prompt)
        except Exception:
            pass

        from datetime import datetime
        current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_major_ctx = get_user_setting("major", "미설정")
        user_grade_ctx = get_user_setting("grade", "미설정")
        memory_summary_ctx = get_latest_memory_summary(CONVERSATION_SESSION_ID) or "저장된 장기기억 요약 없음"
        config = {"configurable": {"thread_id": "streamlit_session"}}

        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("CampusAgent가 생각 중... 🤔"):
                    last_msg_content = ""
                    try:
                        if not st.session_state.get("graph_memory_hydrated", True):
                            graph_messages = [
                                (msg["role"], msg["content"])
                                for msg in st.session_state.messages
                                if msg["role"] in {"user", "assistant"}
                            ]
                        else:
                            graph_messages = [("user", prompt)]

                        # AgentState에 맞춰서 messages와 current_context 전달
                        # MemorySaver가 켜져 있으므로 이전 대화들은 그래프 내부에서 자동 누적됨
                        for event in st.session_state.graph.stream(
                            {
                                "messages": graph_messages,
                                "current_context": {
                                    "current_time": current_time_str,
                                    "user_major": user_major_ctx,
                                    "user_grade": user_grade_ctx,
                                    "memory_summary": memory_summary_ctx
                                }
                            }, 
                            config
                        ):
                            st.session_state.graph_memory_hydrated = True
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
                            # Actionable RAG 제안 버튼
                            actionable_keywords = [
                                "공지", "검색", "편입", "전공심화", "국가장학",
                                "국가근로", "학자금", "공모전", "대외활동", "인턴",
                            ]
                            if any(keyword in prompt for keyword in actionable_keywords):
                                if st.button("✅ 이 내용을 바탕으로 캘린더나 과제에 등록하기", key="rag_action"):
                                    st.session_state.quick_prompt = "방금 찾은 정보를 바탕으로 주요 마감일이나 일정을 내 캘린더/과제에 등록해줘."
                                    st.rerun()
                        else:
                            last_msg_content = "처리가 완료되었지만 응답 내용이 비어있습니다."
                            st.markdown(last_msg_content)

                        st.session_state.messages.append(
                            {"role": "assistant", "content": last_msg_content}
                        )
                        try:
                            save_conversation_message(
                                CONVERSATION_SESSION_ID,
                                "assistant",
                                last_msg_content,
                            )
                        except Exception:
                            pass
                    except Exception as e:
                        error_msg = _format_chat_error(e)
                        st.error(error_msg)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": error_msg}
                        )
                        try:
                            save_conversation_message(
                                CONVERSATION_SESSION_ID,
                                "assistant",
                                error_msg,
                            )
                        except Exception:
                            pass

with tab_dashboard:
    st.markdown("### 📊 과제 대시보드")
    
    urgent_only = st.toggle("🔥 긴급(High) 과제만 보기", value=False)
    
    try:
        task_items = get_assignments_with_progress()
        if urgent_only:
            task_items = [item for item in task_items if item.assignment.priority == 'high']
            
        if not task_items:
            st.info("📚 등록된 과제가 없습니다. 챗봇에게 과제를 추가해달라고 말해보세요!")
        else:
            summary_cols = st.columns(3)
            total_tasks = len(task_items)
            done_tasks = sum(1 for item in task_items if item.assignment.status == "done")
            total_subtasks = sum(item.total_subtasks for item in task_items)
            summary_cols[0].metric("전체 과제", f"{total_tasks}건")
            summary_cols[1].metric("완료 과제", f"{done_tasks}건")
            summary_cols[2].metric("서브태스크", f"{total_subtasks}개")

            for item in task_items:
                assignment = item.assignment
                status_label = assignment.status.value if hasattr(assignment.status, "value") else str(assignment.status)
                progress_label = f"{item.progress}% ({item.done_subtasks}/{item.total_subtasks})" if item.total_subtasks else "서브태스크 없음"
                expander_label = (
                    f"[{assignment.id}] {assignment.title} | {assignment.course_name} | "
                    f"{assignment.due_date} | {progress_label}"
                )

                with st.expander(expander_label, expanded=item.total_subtasks > 0):
                    meta_cols = st.columns([2, 2, 1])
                    meta_cols[0].markdown(f"**과목**: {assignment.course_name}")
                    meta_cols[1].markdown(f"**마감일**: {assignment.due_date}")
                    meta_cols[2].markdown(f"**상태**: `{status_label}`")
                    st.progress(item.progress / 100 if item.total_subtasks else (1.0 if status_label == "done" else 0.0))

                    if assignment.description:
                        st.caption(assignment.description)

                    if item.subtasks:
                        st.markdown("#### 서브태스크")
                        for subtask in item.subtasks:
                            subtask_done = subtask.status == "done"
                            checkbox_label = (
                                f"[{subtask.id}] {subtask.title}"
                                f"{f' · {subtask.due_date}' if subtask.due_date else ''}"
                            )
                            checked = st.checkbox(
                                checkbox_label,
                                value=subtask_done,
                                key=f"subtask_done_{subtask.id}",
                            )
                            if checked != subtask_done:
                                update_subtask_status(
                                    subtask.id,
                                    "done" if checked else "pending",
                                )
                                st.success(f"서브태스크 '{subtask.title}' 상태가 변경되었습니다.")
                                st.rerun()
                            if subtask.description:
                                st.caption(subtask.description)
                    else:
                        done = status_label == "done"
                        checked = st.checkbox(
                            "일반 과제 완료",
                            value=done,
                            key=f"assignment_done_{assignment.id}",
                        )
                        if checked != done:
                            update_assignment_status(
                                assignment.id,
                                "done" if checked else "pending",
                            )
                            st.success(f"과제 '{assignment.title}' 상태가 변경되었습니다.")
                            st.rerun()
    except Exception as e:
        st.error(f"대시보드 로딩 실패: {e}")

with tab_calendar:
    import calendar as _cal
    from datetime import date as _date

    # ── 세션 상태 초기화 ──
    _today = _date.today()
    if "cal_year" not in st.session_state:
        st.session_state.cal_year = _today.year
    if "cal_month" not in st.session_state:
        st.session_state.cal_month = _today.month

    # ── 상단: 필터 + 월 네비게이션 ──
    st.markdown("### 📅 캘린더")
    top_left, top_right = st.columns([4, 3])

    with top_left:
        filter_type = st.radio(
            "표시 항목",
            ["전체", "과제", "일정"],
            horizontal=True,
            label_visibility="collapsed",
            key="cal_filter",
        )

    with top_right:
        nav_prev, nav_title, nav_next = st.columns([1, 3, 1])
        with nav_prev:
            if st.button("◀", use_container_width=True, key="cal_prev"):
                if st.session_state.cal_month == 1:
                    st.session_state.cal_month = 12
                    st.session_state.cal_year -= 1
                else:
                    st.session_state.cal_month -= 1
                st.rerun()
        with nav_title:
            st.markdown(
                f"<p style='text-align:center; font-weight:700; font-size:1.05em; margin:6px 0'>"
                f"{st.session_state.cal_year}년 {st.session_state.cal_month}월</p>",
                unsafe_allow_html=True,
            )
        with nav_next:
            if st.button("▶", use_container_width=True, key="cal_next"):
                if st.session_state.cal_month == 12:
                    st.session_state.cal_month = 1
                    st.session_state.cal_year += 1
                else:
                    st.session_state.cal_month += 1
                st.rerun()

    # ── 데이터 수집 ──
    events_by_date = defaultdict(list)

    if filter_type in ("전체", "일정"):
        try:
            for s in get_schedules():
                events_by_date[s.date].append({
                    "type": "schedule",
                    "title": s.title,
                    "category": s.category,
                    "time": s.start_time or "",
                    "end_time": s.end_time or "",
                })
        except Exception:
            pass

    if filter_type in ("전체", "과제"):
        try:
            for a in get_assignments():
                events_by_date[a.due_date].append({
                    "type": "assignment",
                    "title": a.title,
                    "priority": a.priority,
                    "status": a.status,
                    "course": a.course_name,
                })
        except Exception:
            pass

    # ── CSS 주입: Streamlit CSS 변수 기반 테마 자동 대응 ──
    st.markdown("""
    <style>
    .cc-header {
        text-align: center;
        font-weight: 700;
        padding: 6px 0;
        border-bottom: 2px solid rgba(128,128,128,0.3);
        color: var(--text-color);
    }
    .cc-sat { color: #1565C0 !important; }
    .cc-sun { color: #E53935 !important; }
    .cc-cell {
        background: var(--background-color);
        border: 1px solid rgba(128,128,128,0.25);
        border-radius: 8px;
        padding: 5px 4px;
        min-height: 95px;
        margin: 1px 0;
    }
    .cc-today {
        background: var(--secondary-background-color) !important;
        border: 2px solid var(--primary-color) !important;
    }
    .cc-num {
        text-align: right;
        font-size: 0.88em;
        margin-bottom: 3px;
        color: var(--text-color);
        font-weight: 400;
    }
    .cc-today .cc-num { font-weight: 700; }
    .cc-badge {
        display: block;
        color: #fff;
        border-radius: 3px;
        padding: 1px 4px;
        margin: 2px 0;
        font-size: 0.67em;
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
    }
    /* 다크모드: 토·일 색상을 밝게 */
    @media (prefers-color-scheme: dark) {
        .cc-sat { color: #64B5F6 !important; }
        .cc-sun { color: #EF9A9A !important; }
    }
    </style>
    """, unsafe_allow_html=True)

    # ── 캘린더 그리드 ──
    _year  = st.session_state.cal_year
    _month = st.session_state.cal_month

    DAY_LABELS   = ["월", "화", "수", "목", "금", "토", "일"]
    DAY_CLASSES  = ["", "", "", "", "", "cc-sat", "cc-sun"]

    # 요일 헤더
    hcols = st.columns(7)
    for i, lbl in enumerate(DAY_LABELS):
        hcols[i].markdown(
            f"<div class='cc-header {DAY_CLASSES[i]}'>{lbl}</div>",
            unsafe_allow_html=True,
        )

    # 주 단위 렌더링
    SCHED_COLORS = {
        "class":    "#43A047",
        "exam":     "#E53935",
        "personal": "#1E88E5",
        "meeting":  "#FB8C00",
        "other":    "#8E24AA",
    }
    PRIORITY_COLORS = {"high": "#E53935", "medium": "#FB8C00", "low": "#43A047"}

    for week in _cal.monthcalendar(_year, _month):
        wcols = st.columns(7)
        for col_i, day in enumerate(week):
            with wcols[col_i]:
                if day == 0:
                    st.markdown("<div class='cc-cell' style='border-color:transparent;background:transparent'></div>",
                                unsafe_allow_html=True)
                    continue

                cur      = _date(_year, _month, day)
                date_str = cur.strftime("%Y-%m-%d")
                is_today = cur == _today
                today_cls = "cc-today" if is_today else ""

                badges = ""
                for ev in events_by_date.get(date_str, []):
                    if ev["type"] == "schedule":
                        bg_color = SCHED_COLORS.get(ev["category"], "#607D8B")
                        icon = "📅"
                    else:
                        bg_color = PRIORITY_COLORS.get(ev.get("priority", "medium"), "#FB8C00")
                        if ev.get("status") == "done":
                            bg_color = "#757575"
                        icon = "📋"
                    short = ev["title"][:8] + "…" if len(ev["title"]) > 8 else ev["title"]
                    badges += (
                        f"<span class='cc-badge' style='background:{bg_color}'>"
                        f"{icon} {short}</span>"
                    )

                st.markdown(
                    f"<div class='cc-cell {today_cls}'>"
                    f"<div class='cc-num {DAY_CLASSES[col_i]}'>{day}</div>"
                    f"{badges}</div>",
                    unsafe_allow_html=True,
                )

    # ── 범례 ──
    st.markdown("---")
    legend_cols = st.columns(7)
    legends = [
        ("📋 과제 (높음)", "#E53935"),
        ("📋 과제 (보통)", "#FB8C00"),
        ("📋 과제 (낮음)", "#43A047"),
        ("📅 수업",       "#43A047"),
        ("📝 시험",       "#E53935"),
        ("👥 회의",       "#FB8C00"),
        ("👤 개인",       "#1E88E5"),
    ]
    for col, (label, color) in zip(legend_cols, legends):
        col.markdown(
            f"<div style='background:{color};color:#fff;border-radius:4px;"
            f"padding:3px 6px;font-size:0.7em;text-align:center'>{label}</div>",
            unsafe_allow_html=True,
        )

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
