# 🎓 CampusAgent

> 대학생 특화 LLM + MCP 로컬 AI 어시스턴트 (Gemini / OpenAI 지원)

## 📋 프로젝트 개요

CampusAgent는 대학생들의 **과제 관리**, **캘린더/일정 관리**, **공지사항 RAG 검색**을 자연어 대화로 처리하는 로컬 AI 어시스턴트입니다.

### 핵심 기술 스택

| 기술 | 설명 |
|------|------|
| **LLM** | Google Gemini / OpenAI GPT (자동 감지) |
| **에이전트** | LangGraph (상태 기반 에이전트, Tool 순환 호출) |
| **MCP 도구** | LangChain Tool 기반 14개 도구 (과제 5 + 캘린더 6 + RAG 3) |
| **데이터베이스** | SQLite (과제/일정) + ChromaDB (벡터 검색) |
| **RAG** | 문서 로드 → 청킹 → 임베딩 → 유사도 검색 |
| **UI** | Streamlit 채팅 인터페이스 + 사이드바 대시보드 |

---

## 🏗️ 아키텍처

```
사용자 입력 (Streamlit Chat)
       │
       ▼
┌─────────────────────────────┐
│      LangGraph Agent        │
│                             │
│  ┌───────────────────────┐  │
│  │ Gemini / OpenAI LLM   │  │
│  │ + bind_tools(14개)    │  │
│  └──────────┬────────────┘  │
│             │               │
│  ┌──────────▼────────────┐  │
│  │   should_continue     │  │
│  └────┬──────────┬───────┘  │
│       │          │          │
│     END      tools          │
│           ┌──▼──────────┐   │
│           │  ToolNode    │   │
│           │  (14개 도구) │   │
│           └──────────────┘   │
└─────────────────────────────┘
       │
       ▼
┌──────────────┐  ┌──────────────┐
│   SQLite DB  │  │  ChromaDB    │
│ (과제/일정)   │  │ (공지사항)    │
└──────────────┘  └──────────────┘
```

---

## 📂 프로젝트 구조

```
CampusAgent/
├── app.py                      # Streamlit 메인 앱
├── pyproject.toml              # 프로젝트 의존성
├── .env                        # 환경변수 (API 키)
│
├── agent/                      # LangGraph 에이전트
│   ├── graph.py                # 에이전트 그래프 (Gemini/OpenAI 자동 감지)
│   ├── state.py                # 에이전트 상태 정의
│   └── prompts.py              # 시스템 프롬프트
│
├── database/                   # 데이터베이스 레이어
│   ├── db.py                   # SQLite CRUD (과제 + 캘린더)
│   └── models.py               # Pydantic 데이터 모델
│
├── mcp_servers/                # MCP 도구 서버
│   ├── task_server.py          # 과제 관리 도구 (5종)
│   ├── calendar_server.py      # 캘린더 도구 (6종)
│   └── rag_server.py           # RAG 검색 도구 (3종)
│
├── rag/                        # RAG 파이프라인
│   ├── loader.py               # JSON/텍스트 문서 로더
│   ├── chunker.py              # 텍스트 청커
│   ├── embedder.py             # 임베딩 생성기 (ChromaDB 내장)
│   └── retriever.py            # 유사도 검색기
│
├── config/                     # 설정
│   ├── settings.py             # 환경 설정 (Gemini/OpenAI 자동 감지)
│   └── mcp_config.json         # MCP 서버 레지스트리
│
├── data/                       # 데이터
│   └── sample_notices.json     # 테스트용 공지사항 10건
│
└── tests/                      # 테스트 (33개)
    ├── test_task.py             # 과제 CRUD 테스트 (13개)
    ├── test_calendar.py         # 캘린더 CRUD 테스트 (12개)
    └── test_rag.py              # RAG 파이프라인 테스트 (8개)
```

---

## 🚀 실행 방법

### 1단계: 가상환경 설정

```bash
# 이미 venv가 있으면 이 단계 건너뛰기
python -m venv venv

# 가상환경 활성화
venv\Scripts\activate           # Windows (PowerShell)
# source venv/bin/activate      # macOS/Linux

# 의존성 설치
pip install -e .
pip install pytest              # 테스트용
```

### 2단계: API 키 설정

`.env` 파일에 **Gemini 또는 OpenAI** API 키를 추가합니다:

**Gemini 사용 (권장):**
```env
GOOGLE_API_KEY=여기에_Gemini_API_키_입력
```
> 💡 Gemini API 키는 [Google AI Studio](https://aistudio.google.com/)에서 무료로 발급 가능

**OpenAI 사용:**
```env
OPENAI_API_KEY=sk-여기에_OpenAI_키_입력
```

**선택 옵션 (기본값이 있으므로 생략 가능):**
```env
LLM_MODEL=gemini-1.5-flash     # 또는 gemini-1.5-pro, gpt-3.5-turbo 등
LLM_TEMPERATURE=0               # 응답 일관성 (0=결정적, 1=창의적)
```

### 3단계: 실행

```bash
# 가상환경 활성화 후
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 이 자동으로 열립니다.

### 4단계: 테스트 실행

```bash
# 전체 테스트 (33개)
python -m pytest tests/ -v

# 개별 테스트
python -m pytest tests/test_task.py -v       # 과제 CRUD
python -m pytest tests/test_calendar.py -v   # 캘린더 CRUD
python -m pytest tests/test_rag.py -v        # RAG 파이프라인
```

---

## 📋 구현된 기능 (v0.3.0)

### 📝 과제 관리 (Task Management)
| 도구 | 설명 | 예시 명령 |
|------|------|----------|
| `add_task` | 과제 추가 | "자료구조 과제 추가해줘, 마감일은 4월 10일" |
| `list_tasks` | 과제 목록 조회 | "내 과제 목록 보여줘" |
| `update_task_status` | 상태 변경 | "1번 과제 완료 처리해줘" |
| `delete_task` | 과제 삭제 | "2번 과제 삭제해줘" |
| `get_upcoming_deadlines` | 마감 임박 | "이번 주 마감인 과제 알려줘" |

### 📅 캘린더/일정 관리 (Calendar)
| 도구 | 설명 | 예시 명령 |
|------|------|----------|
| `add_calendar_event` | 일정 추가 | "내일 9시에 자료구조 수업 추가" |
| `list_calendar_events` | 일정 조회 | "내 일정 보여줘" |
| `get_today_schedule` | 오늘 일정 | "오늘 일정 알려줘" |
| `get_week_schedule` | 기간 일정 | "이번 주 일정 보여줘" |
| `delete_calendar_event` | 일정 삭제 | "3번 일정 삭제해줘" |
| `check_dday` | D-day 확인 | "시험 D-day 확인해줘" |

### 🔍 공지사항 검색 (RAG)
| 도구 | 설명 | 예시 명령 |
|------|------|----------|
| `search_university_notices` | 공지 검색 | "장학금 관련 공지 검색해줘" |
| `load_notice_data` | 데이터 로드 | "공지사항 데이터 로드해줘" |
| `get_notice_stats` | 현황 확인 | "공지 몇 건 저장되어 있어?" |

---

## 🗄️ 데이터베이스 확인 (DBeaver)

SQLite 데이터베이스를 DBeaver로 시각적으로 확인할 수 있습니다:

1. DBeaver 실행 → **Database > New Database Connection**
2. **SQLite** 선택 → Next
3. **Path** 에 입력: `c:\Users\kimka\OneDrive\Documents\GitHub\CampusAgent\campus_tasks.db`
4. **Finish** → 연결 완료

확인 가능한 테이블:
- `assignments` — 과제 데이터
- `schedules` — 일정 데이터
- `user_settings` — 사용자 설정

---

## 📊 개발 일정

| 주차 | 기간 | 목표 | 상태 |
|------|------|------|------|
| 1-2주 | 3/17~3/23 | 요구사항 분석, 설계 | ✅ |
| 3주 | 3/24~3/30 | 프로젝트 뼈대 구축 | ✅ |
| 4주 | 3/31~4/6 | Task + Calendar + RAG 구현 | ✅ |
| 5주 | 4/7~4/13 | 에이전트 통합 고도화 | 📋 예정 |
| 6주 | 4/14~4/20 | UI 고도화 + 추가 기능 | 📋 예정 |
| 7주 | 4/21~4/28 | 최종 테스트 + 발표 준비 | 📋 예정 |

---

## 라이선스

MIT License
