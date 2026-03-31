# 🎓 CampusAgent

> 대학생 특화 LLM + MCP 로컬 AI 어시스턴트

## 📋 프로젝트 개요

CampusAgent는 대학생들의 **과제 관리**, **공지사항 검색**, **일정 관리**를 자연어로 처리하는 로컬 AI 어시스턴트입니다.

### 핵심 기술 스택
- **LLM**: OpenAI GPT (LangChain)
- **에이전트 프레임워크**: LangGraph (상태 기반 에이전트)
- **MCP 도구**: LangChain Tool 기반 과제 관리 도구
- **데이터베이스**: SQLite (과제/설정) + ChromaDB (벡터 검색)
- **UI**: Streamlit 채팅 인터페이스

---

## 🏗️ 아키텍처

```
사용자 입력 (Streamlit Chat)
       │
       ▼
┌─────────────────────┐
│   LangGraph Agent   │
│  (agent/graph.py)   │
│                     │
│  ┌──────────────┐   │
│  │  ChatOpenAI  │   │
│  │ + bind_tools │   │
│  └──────┬───────┘   │
│         │           │
│  ┌──────▼───────┐   │
│  │ should_continue│  │
│  └──┬───────┬───┘   │
│     │       │       │
│   END    tools      │
│         ┌──▼──┐     │
│         │ Tool│     │
│         │ Node│     │
│         └──┬──┘     │
│            │        │
│         ┌──▼──────┐ │
│         │MCP Tools│ │
│         └─────────┘ │
└─────────────────────┘
       │
       ▼
┌──────────────┐   ┌──────────────┐
│   SQLite DB  │   │  ChromaDB    │
│ (과제/설정)   │   │ (공지사항)    │
└──────────────┘   └──────────────┘
```

---

## 📂 프로젝트 구조

```
CampusAgent/
├── app.py                    # Streamlit 메인 앱
├── pyproject.toml            # 프로젝트 의존성
├── .env                      # 환경변수 (API 키 등)
│
├── agent/                    # LangGraph 에이전트
│   ├── graph.py              # 에이전트 그래프 정의
│   ├── state.py              # 에이전트 상태 정의
│   └── prompts.py            # 시스템 프롬프트
│
├── database/                 # 데이터베이스 레이어
│   ├── db.py                 # SQLite CRUD 함수
│   └── models.py             # Pydantic 데이터 모델
│
├── mcp_servers/              # MCP 도구 서버
│   ├── task_server.py        # 과제 관리 도구 (5종)
│   ├── rag_server.py         # RAG 검색 도구 (예정)
│   └── calendar_server.py    # 캘린더 도구 (예정)
│
├── rag/                      # RAG 파이프라인
│   ├── retriever.py          # ChromaDB 검색기
│   ├── loader.py             # 문서 로더 (예정)
│   ├── chunker.py            # 텍스트 청커 (예정)
│   └── embedder.py           # 임베딩 생성기 (예정)
│
├── config/                   # 설정
│   ├── settings.py           # 환경 설정 모듈
│   └── mcp_config.json       # MCP 서버 레지스트리
│
└── tests/                    # 테스트
    ├── test_task.py           # Task CRUD 테스트
    ├── test_rag.py            # RAG 테스트 (예정)
    ├── test_agent.py          # 에이전트 테스트 (예정)
    └── test_calendar.py       # 캘린더 테스트 (예정)
```

---

## 🚀 실행 방법

### 1. 환경 설정

```bash
# 가상환경 생성 & 활성화
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 의존성 설치
pip install -e .
pip install pytest           # 테스트용
```

### 2. API 키 설정

`.env` 파일에 OpenAI API 키를 추가합니다:

```
OPENAI_API_KEY=sk-your-api-key-here
```

### 3. 실행

```bash
streamlit run app.py
```

### 4. 테스트

```bash
python -m pytest tests/test_task.py -v
```

---

## 📋 현재 구현된 기능 (v0.2.0 — 4주차)

### ✅ 과제 관리 (Task Management)
| 기능 | 도구명 | 설명 |
|------|--------|------|
| 과제 추가 | `add_task` | 과목명, 마감일, 우선순위 포함 |
| 과제 조회 | `list_tasks` | 상태/과목별 필터링 |
| 상태 변경 | `update_task_status` | pending → in_progress → done |
| 과제 삭제 | `delete_task` | ID 기반 삭제 |
| 마감 알림 | `get_upcoming_deadlines` | N일 이내 마감 과제 |

### 🔜 개발 예정
- **5주차**: 공지사항 RAG 검색 (문서 로드 → 청킹 → 임베딩 → 검색)
- **6주차**: 캘린더 연동 + 에이전트 통합
- **7주차**: UI 고도화 + 최종 테스트 + 문서화

---

## 🧪 사용 예시

```
사용자: 자료구조 과제 추가해줘, 마감일은 4월 10일
Agent : ✅ 과제가 추가되었습니다!
        📋 [1] 자료구조 과제
        📚 과목: 자료구조
        📅 마감: 2026-04-10
        🟡 우선순위: medium
        상태: pending

사용자: 내 과제 목록 보여줘
Agent : 📚 과제 목록 (총 1건)
        ...

사용자: 1번 과제 완료 처리해줘
Agent : ✅ 과제 상태가 변경되었습니다!
        상태: done
```

---

## 📊 개발 일정

| 주차 | 기간 | 목표 | 상태 |
|------|------|------|------|
| 1-2주 | 3/17~3/23 | 요구사항 분석, 설계 | ✅ |
| 3주 | 3/24~3/30 | 프로젝트 뼈대 구축 | ✅ |
| **4주** | **3/31~4/6** | **MCP Tool + Task CRUD** | **🔄 진행중** |
| 5주 | 4/7~4/13 | RAG 파이프라인 | 📋 예정 |
| 6주 | 4/14~4/20 | 에이전트 통합 + 캘린더 | 📋 예정 |
| 7주 | 4/21~4/28 | UI 고도화 + 최종 테스트 | 📋 예정 |

---

## 라이선스

MIT License
