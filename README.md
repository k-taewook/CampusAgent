# 🎓 CampusAgent

> 대학생 특화 LLM + LangGraph 로컬 AI 어시스턴트 (Gemini / OpenAI 지원)

## 📋 프로젝트 개요

CampusAgent는 대학생들의 **과제 관리**, **캘린더/일정 관리**, **공지사항 RAG 검색**, **대학생 정보 검색**을 자연어 대화로 처리하는 로컬 AI 어시스턴트입니다.

단순한 챗봇이 아닌, 학교 공지를 실시간 크롤링하고 대화 문맥을 기억하며 편입·장학·공모전 정보까지 통합 검색하는 **능동적 학사 어시스턴트**입니다.

### 핵심 기술 스택

| 기술 | 설명 |
|------|------|
| **LLM** | Google Gemini / OpenAI GPT (자동 감지) |
| **에이전트** | LangGraph 상태 기반 에이전트 + MemorySaver |
| **MCP 도구** | LangChain Tool 기반 20개 도구 |
| **데이터베이스** | SQLite (과제/일정/장기기억) + ChromaDB (벡터 검색) |
| **RAG** | 실시간 크롤링 → 청킹 → 임베딩 → 유사도 검색 |
| **크롤러** | 학과 공지 (K2Web BBS) + 대표 홈페이지 공지 (combBbs) |
| **UI** | Streamlit 채팅 인터페이스 + 4-Tabs 대시보드 |

---

## 🏗️ 아키텍처

```
사용자 입력 (Streamlit Chat)
       │
       ▼
┌──────────────────────────────────┐
│         LangGraph Agent          │
│                                  │
│  ┌────────────────────────────┐  │
│  │  Gemini / OpenAI LLM       │  │
│  │  + bind_tools(20개)        │  │
│  └────────────┬───────────────┘  │
│               │                  │
│  ┌────────────▼───────────────┐  │
│  │      should_continue       │  │
│  └──────┬──────────┬──────────┘  │
│         │          │             │
│        END      tools            │
│              ┌────▼──────────┐   │
│              │   ToolNode    │   │
│              │   (20개 도구) │   │
│              └───────────────┘   │
└──────────────────────────────────┘
       │
       ▼
┌──────────────┐  ┌──────────────┐
│   SQLite DB  │  │  ChromaDB    │
│  과제/일정/  │  │  공지사항/   │
│  장기기억    │  │  대학생정보  │
└──────────────┘  └──────────────┘
```

---

## 📂 프로젝트 구조

```
CampusAgent/
├── app.py                          # Streamlit 메인 앱
├── pyproject.toml                  # 프로젝트 의존성
├── .env                            # 환경변수 (API 키)
│
├── agent/                          # LangGraph 에이전트
│   ├── graph.py                    # 에이전트 그래프 + MemorySaver
│   ├── state.py                    # 에이전트 상태 정의
│   └── prompts.py                  # 시스템 프롬프트 (도구 사용 가이드 포함)
│
├── database/                       # 데이터베이스 레이어
│   ├── db.py                       # SQLite CRUD (과제 + 캘린더 + 장기기억)
│   └── models.py                   # Pydantic 데이터 모델
│
├── mcp_servers/                    # MCP 도구 서버
│   ├── task_server.py              # 과제 관리 도구 (5종)
│   ├── calendar_server.py          # 캘린더 도구 (6종)
│   ├── rag_server.py               # 공지 검색 도구 (5종)
│   └── student_info_server.py      # 대학생 정보 도구 (4종)
│
├── rag/                            # RAG 파이프라인 + 크롤러
│   ├── crawler.py                  # 웹 크롤러 (K2Web BBS + combBbs)
│   ├── loader.py                   # JSON/텍스트 문서 로더
│   ├── chunker.py                  # 텍스트 청커
│   ├── embedder.py                 # ChromaDB 임베딩 저장기
│   └── retriever.py                # 유사도 검색기
│
├── config/                         # 설정
│   ├── settings.py                 # 환경 설정 (Gemini/OpenAI 자동 감지)
│   └── mcp_config.json             # MCP 서버 레지스트리
│
├── data/                           # 데이터
│   ├── sample_notices.json         # 테스트용 학과 공지 샘플
│   └── student_info_samples.json   # 편입/장학/공모전 정보 샘플
│
└── tests/                          # 테스트 (44개)
    ├── test_task.py                 # 과제 CRUD 테스트
    ├── test_calendar.py             # 캘린더 CRUD 테스트
    ├── test_rag.py                  # RAG 파이프라인 테스트
    ├── test_student_info.py         # 대학생 정보 검색 테스트
    ├── test_memory.py               # 장기기억 SQLite 테스트
    └── test_agent.py                # 에이전트 통합 테스트
```

---

## 🚀 실행 방법

### 1단계: 가상환경 설정

```bash
python -m venv venv

# Windows (PowerShell)
venv\Scripts\activate

# macOS / Linux
# source venv/bin/activate

pip install -e .
pip install pytest   # 테스트용
```

### 2단계: API 키 설정

`.env` 파일에 **Gemini 또는 OpenAI** API 키를 추가합니다.

**Gemini 사용 (권장, 무료 티어 있음):**
```env
GOOGLE_API_KEY=여기에_Gemini_API_키_입력
```
> Gemini API 키는 [Google AI Studio](https://aistudio.google.com/)에서 발급 가능합니다.

**OpenAI 사용:**
```env
OPENAI_API_KEY=sk-여기에_OpenAI_키_입력
```

**선택 옵션 (기본값이 있으므로 생략 가능):**
```env
LLM_MODEL=gemini-1.5-flash     # 모델 지정
LLM_TEMPERATURE=0               # 0=결정적, 1=창의적
```

### 3단계: 실행

```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 이 열립니다.

### 4단계: 테스트 실행

```bash
# 전체 테스트 (44개)
python -m pytest tests/ -v

# 개별 테스트
python -m pytest tests/test_task.py -v           # 과제
python -m pytest tests/test_calendar.py -v       # 캘린더
python -m pytest tests/test_rag.py -v            # RAG
python -m pytest tests/test_student_info.py -v   # 대학생 정보
python -m pytest tests/test_memory.py -v         # 장기기억
```

---

## 📋 구현된 기능 (v0.9.0)

### 📝 과제 관리 (5종)

| 도구 | 설명 | 예시 명령 |
|------|------|----------|
| `add_task` | 과제 추가 | "자료구조 과제 추가해줘, 마감일은 6월 10일" |
| `list_tasks` | 과제 목록 조회 | "내 과제 목록 보여줘" |
| `update_task_status` | 상태 변경 | "1번 과제 완료 처리해줘" |
| `delete_task` | 과제 삭제 | "2번 과제 삭제해줘" |
| `get_upcoming_deadlines` | 마감 임박 조회 | "이번 주 마감인 과제 알려줘" |

### 📅 캘린더/일정 관리 (6종)

| 도구 | 설명 | 예시 명령 |
|------|------|----------|
| `add_calendar_event` | 일정 추가 | "내일 9시에 자료구조 수업 추가" |
| `list_calendar_events` | 일정 조회 | "내 일정 보여줘" |
| `get_today_schedule` | 오늘 일정 | "오늘 일정 알려줘" |
| `get_week_schedule` | 기간 일정 | "이번 주 일정 보여줘" |
| `delete_calendar_event` | 일정 삭제 | "3번 일정 삭제해줘" |
| `check_dday` | D-day 확인 | "기말고사 D-day 확인해줘" |

### 🔍 공지사항 검색 (5종, 실시간 크롤링)

| 도구 | 설명 | 예시 명령 |
|------|------|----------|
| `search_university_notices` | 학과 공지 검색 (K2Web BBS) | "학과 장학금 공지 검색해줘" |
| `search_school_notices` | 학교 대표 공지 검색 (combBbs) | "학교 공지사항 보여줘" |
| `load_notice_data` | 로컬 JSON 데이터 로드 | "공지사항 데이터 로드해줘" |
| `clear_notice_data` | ChromaDB 데이터 초기화 | "공지 데이터 초기화해줘" |
| `get_notice_stats` | 저장 현황 확인 | "공지 몇 건 저장되어 있어?" |

### 🌐 대학생 정보 검색 (4종)

편입학/전공심화, 국가장학금, 공모전/대외활동/인턴십 정보를 통합 검색합니다.

| 도구 | 설명 | 예시 명령 |
|------|------|----------|
| `search_student_info` | 저장된 데이터에서 의미 기반 검색 | "국가장학금 신청 방법 알려줘" |
| `search_student_info_live` | 학교 공지에서 **실시간 크롤링** 후 검색 | "최신 편입학 모집요강 찾아줘" |
| `load_student_info_data` | 샘플 데이터 로드 | "대학생 정보 데이터 로드해줘" |
| `get_student_info_stats` | 저장 현황 확인 | "대학생 정보 몇 건 있어?" |

> `search_student_info_live`는 학교 공지 게시판(combBbs)을 카테고리 키워드로 직접 검색하므로 별도 API 키 없이 동작하며, 결과는 ChromaDB에 자동 저장되어 이후 검색에도 재활용됩니다.

### 🧠 에이전트 고도화

| 기능 | 설명 |
|------|------|
| **대화 문맥 기억** | `MemorySaver`로 동일 세션 내 이전 대화를 완벽히 기억 |
| **장기기억 SQLite 저장** | 세션 간 대화 요약을 SQLite에 저장·복원하여 다음 실행 시에도 맥락 유지 |
| **동적 시간 주입** | 실시간 타임스탬프로 "내일", "다음 주" 등 상대적 날짜 계산 |
| **에러 자동 복구** | 도구 실행 실패 시 에이전트가 파라미터를 수정해 자동 재시도 |
| **Pydantic 검증** | 무효한 제목·날짜 형식을 에이전트 단에서 강제 차단 |

### 🎨 UI/UX

| 기능 | 설명 |
|------|------|
| **4-Tabs UI** | 챗봇 / 과제 대시보드 / 캘린더 / 설정 탭 분리 |
| **Quick Action 버튼** | 자주 쓰는 명령어를 상단 버튼으로 원클릭 실행 |
| **Actionable RAG 버튼** | 공지 검색 후 "캘린더/과제로 등록하기" 버튼 자동 노출 |
| **인터랙티브 대시보드** | Pandas DataEditor로 UI에서 즉시 과제 완료 처리 |
| **RAG 개인화** | 설정 탭의 전공·학년을 프롬프트에 실시간 주입 |

---

## 🗄️ 데이터베이스 확인

SQLite 데이터베이스를 DBeaver로 확인할 수 있습니다.

1. DBeaver 실행 → **Database > New Database Connection**
2. **SQLite** 선택 → Next
3. Path 입력: `<프로젝트경로>\campus_tasks.db`
4. **Finish** → 연결 완료

확인 가능한 테이블:

| 테이블 | 설명 |
|--------|------|
| `assignments` | 과제 데이터 |
| `schedules` | 일정 데이터 |
| `user_settings` | 사용자 설정 |
| `conversation_sessions` | 대화 세션 목록 |
| `conversation_messages` | 세션별 대화 내역 |
| `memory_summaries` | 세션 간 장기기억 요약 |

---

## 📊 개발 일정

| 주차 | 기간 | 목표 | 상태 |
|------|------|------|------|
| 1-2주 | 3/17~3/23 | 요구사항 분석, 설계 | ✅ |
| 3주 | 3/24~3/30 | 프로젝트 뼈대 구축 | ✅ |
| 4주 | 3/31~4/6 | Task + Calendar + RAG 구현 | ✅ |
| 5주 | 4/7~4/13 | 에이전트 통합 고도화 | ✅ |
| 6주 | 4/14~4/20 | UI 고도화 (4-Tabs) + Quick Action | ✅ |
| 7주 | 4/21~4/27 | 실시간 크롤링 + 학교 대표 공지 확장 | ✅ |
| 8-9주 | 4/28~5/11 | 장기기억 + 대학생 정보 검색 | ✅ |
| 10주 | 5/12~5/19 | 대학생 정보 실시간 크롤링 완성 | ✅ |
| 11주 | 5/13~5/20 | 과제 자동 분해 + 서브태스크 트리 | 📋 |
| 12주 | 5/20~5/27 | Multi-Agent 아키텍처 재구조화 | 📋 |
| 13주 | 5/27~6/3 | 일일 자동 브리핑 + 백그라운드 스케줄러 | 📋 |
| 14주 | 6/3~6/10 | RAG 품질 평가 + 최종 발표 | 📋 |

---

## 라이선스

MIT License
