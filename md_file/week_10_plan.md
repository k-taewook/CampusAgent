# CampusAgent 10주차 구현 계획

작성 기준일: 2026-05-09  
주차 목표: 9주차 장기기억 설계 실제 반영 + 대학생 정보 검색 기능 1차 확장  
핵심 방향: 기존 인하공업전문대학 공지사항 크롤링 기능은 그대로 유지하고, 별도의 대학생 정보 검색 기능을 추가한다.

## 1. 10주차 목표

10주차는 단순히 앞으로의 계획을 정리하는 단계가 아니라, 실제로 프로젝트에 반영할 수 있는 기능 구현 주차로 진행한다. 구현 목표는 크게 두 가지이다.

1. 9주차 실습일지에 먼저 작성했던 SQLite 기반 장기기억 기능을 실제 코드에 반영한다.
2. 기존 인하공업전문대학 공지사항 크롤링 기능을 유지하면서, 편입학/국가제도/공모전 정보를 검색하는 대학생 정보 검색 기능을 별도로 추가한다.

이때 기존 공지사항 검색 기능은 절대 새로 갈아엎지 않는다. 현재 완성된 학과 공지 검색과 학교 대표 공지 검색은 CampusAgent의 핵심 장점이므로 그대로 유지한다. 새 기능은 기존 RAG 파이프라인을 재사용하되, “학교/학과 공지”와 “외부 대학생 정보”를 역할상 분리해서 붙이는 방식으로 구현한다.

## 2. 현재 코드 상태 확인 결과

현재 프로젝트의 주요 구조는 다음과 같다.

- `app.py`: Streamlit 메인 UI, 채팅 메시지 관리, LangGraph 호출
- `agent/graph.py`: LangGraph Agent 구성, `MemorySaver` 기반 세션 기억 사용
- `database/db.py`: SQLite 과제/일정/사용자 설정 CRUD
- `mcp_servers/rag_server.py`: 인하공전 학과/학교 공지사항 검색 도구
- `rag/loader.py`: JSON/텍스트 문서 로더
- `rag/chunker.py`: 텍스트 청킹
- `rag/embedder.py`: ChromaDB 저장
- `rag/retriever.py`: ChromaDB 검색
- `data/sample_notices.json`: 공지사항 샘플 데이터

확인된 현재 상태는 다음과 같다.

| 항목 | 현재 상태 | 10주차 처리 방향 |
|---|---|---|
| 학과 공지 검색 | `search_university_notices` 구현됨 | 그대로 유지 |
| 학교 대표 공지 검색 | `search_school_notices` 구현됨 | 그대로 유지 |
| 공지 RAG 파이프라인 | loader → chunker → embedder → retriever 구현됨 | 재사용 |
| 장기기억 테이블 | 아직 없음 | 10주차에 추가 |
| 대화 저장/복원 | `st.session_state.messages` 중심 | SQLite 저장/복원 추가 |
| 대학생 정보 검색 | 아직 없음 | 별도 도구로 추가 |
| 대학생 정보 샘플 데이터 | 아직 없음 | `data/student_info_samples.json` 추가 |

## 3. 구현 원칙

10주차 구현은 다음 원칙을 따른다.

### 3.1 기존 공지사항 크롤러 유지

기존 인하공전 공지 검색은 그대로 둔다.

유지할 도구:

- `search_university_notices`: 컴퓨터시스템공학과 학과 공지 검색
- `search_school_notices`: 인하공업전문대학 대표 홈페이지 공지 검색
- `clear_notice_data`: 공지사항 벡터 데이터 초기화
- `load_notice_data`: 공지사항 JSON 데이터 로드
- `get_notice_stats`: 공지사항 RAG 상태 확인

기존 `rag/crawler.py`의 K2Web/combBbs 크롤링 로직도 건드리지 않는다. 이 기능은 최종 발표에서 “우리학교 특화 공지 검색”으로 보여줄 수 있는 중요한 완성 기능이다.

### 3.2 대학생 정보 검색은 별도 확장으로 추가

새 기능은 기존 공지 검색에 섞지 않고 별도 도구로 추가한다.

권장 파일:

- `mcp_servers/student_info_server.py`
- `data/student_info_samples.json`

권장 도구:

- `search_student_info`
- `load_student_info_data`
- `get_student_info_stats`

이렇게 분리하면 공지 검색과 외부 정보 검색의 역할이 명확해지고, 기존 기능을 망가뜨릴 위험을 줄일 수 있다.

### 3.3 RAG 파이프라인은 재사용

새 기능을 위해 임베딩/검색 구조를 처음부터 다시 만들지 않는다. 기존 `rag` 모듈의 흐름을 그대로 사용한다.

재사용 흐름:

```text
student_info_samples.json
  -> load_notices_from_json 또는 student info 전용 로더
  -> SimpleTextChunker
  -> DocumentEmbedder
  -> ChromaDB
  -> search_notices
  -> search_student_info 응답
```

10주차에는 완성형 외부 사이트 실시간 크롤러까지 만들기보다, 샘플 데이터 기반 검색이 안정적으로 동작하는 1차 버전을 만드는 것이 목표이다. 실시간 편입학/국가제도/공모전 크롤러는 11~13주차에 단계적으로 확장한다.

## 4. 구현 범위 1: SQLite 기반 장기기억 실제 반영

9주차 실습일지에는 장기기억 기능을 구현한 것으로 작성되어 있지만, 현재 코드에는 아직 반영되어 있지 않다. 따라서 10주차 첫 번째 작업은 9주차 문서 내용을 실제 코드에 반영하는 것이다.

### 4.1 DB 테이블 추가

`database/db.py`의 `init_sqlite_db()`에 다음 테이블을 추가한다.

| 테이블 | 역할 |
|---|---|
| `conversation_sessions` | 대화 세션 기본 정보 저장 |
| `conversation_messages` | user/assistant/system/tool 메시지 저장 |
| `memory_summaries` | 오래된 대화의 요약 메모리 저장 |

권장 컬럼:

`conversation_sessions`

- `id TEXT PRIMARY KEY`
- `title TEXT`
- `created_at TEXT DEFAULT (datetime('now', 'localtime'))`
- `updated_at TEXT DEFAULT (datetime('now', 'localtime'))`

`conversation_messages`

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `session_id TEXT NOT NULL`
- `role TEXT NOT NULL`
- `content TEXT NOT NULL`
- `created_at TEXT DEFAULT (datetime('now', 'localtime'))`

`memory_summaries`

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `session_id TEXT NOT NULL`
- `summary TEXT NOT NULL`
- `created_at TEXT DEFAULT (datetime('now', 'localtime'))`
- `updated_at TEXT DEFAULT (datetime('now', 'localtime'))`

### 4.2 DB 함수 추가

`database/db.py`에 다음 함수를 추가한다.

- `get_or_create_conversation_session(session_id: str, title: str = "기본 세션")`
- `save_conversation_message(session_id: str, role: str, content: str)`
- `load_recent_conversation_messages(session_id: str, limit: int = 20)`
- `save_memory_summary(session_id: str, summary: str)`
- `get_latest_memory_summary(session_id: str)`
- `clear_conversation_history(session_id: str)`

10주차에는 완전한 자동 요약 생성까지 욕심내지 않는다. 우선 요약을 저장할 수 있는 DB 구조와 함수만 만들고, 실제 요약 품질 고도화는 14주차 개인화 추천 단계에서 다룬다.

### 4.3 Streamlit 앱 연동

`app.py`의 채팅 흐름에 장기기억 저장/복원을 연결한다.

앱 시작 시:

1. `init_sqlite_db()` 실행
2. `get_or_create_conversation_session("streamlit_session")` 실행
3. `load_recent_conversation_messages("streamlit_session", limit=20)` 실행
4. DB에서 불러온 메시지를 `st.session_state.messages`에 반영

사용자 입력 시:

1. 사용자 메시지를 `st.session_state.messages`에 추가
2. `save_conversation_message("streamlit_session", "user", prompt)` 실행
3. LangGraph Agent 실행
4. AI 응답을 `st.session_state.messages`에 추가
5. `save_conversation_message("streamlit_session", "assistant", last_msg_content)` 실행

### 4.4 Agent 컨텍스트 반영

10주차에는 LangGraph의 `MemorySaver`를 제거하지 않는다. 대신 역할을 분리한다.

- `MemorySaver`: 현재 실행 중인 대화 흐름을 유지하는 단기 기억
- SQLite 장기기억: 앱 재시작 이후에도 남아야 하는 대화 기록 저장

추가로 `get_latest_memory_summary()` 결과를 `current_context`에 넣거나 시스템 프롬프트에 “이전 대화 요약”으로 주입할 수 있게 준비한다. 단, 10주차에는 최소 구현으로 최근 메시지 복원까지 우선 완료한다.

## 5. 구현 범위 2: 대학생 정보 검색 1차 구현

두 번째 작업은 기존 공지 검색과 별도로 대학생 정보 검색 기능을 추가하는 것이다.

### 5.1 샘플 데이터 추가

`data/student_info_samples.json` 파일을 만든다.

카테고리는 다음 3개로 시작한다.

| 카테고리 | 의미 | 예시 |
|---|---|---|
| `transfer` | 편입학/전공심화 | 전공심화 과정, 타학교 편입학 모집요강 |
| `policy` | 국가제도/장학/청년정책 | 국가장학금, 국가근로, 학자금대출 |
| `contest` | 공모전/대외활동/인턴십 | IT 공모전, 대외활동, 현장실습 |

각 카테고리별 최소 2건 이상 작성한다.

권장 필드:

- `title`
- `content`
- `category`
- `source`
- `url`
- `deadline`
- `target`
- `date`

샘플 데이터는 실제 서비스 수준의 최신성보다 10주차 기능 시연을 우선한다. 다만 공식 출처를 적을 수 있는 항목은 `source`와 `url`을 명확히 넣는다.

### 5.2 로더 처리

기존 `load_notices_from_json()`은 `title`, `content`, `date`, `category`, `source` 중심으로 문서를 표준화한다. `student_info_samples.json`도 이 구조에 맞게 작성하면 기존 로더를 그대로 사용할 수 있다.

필요하면 10주차 후반에 `load_student_info_from_json()`을 추가할 수 있지만, 1차 구현에서는 기존 로더 재사용을 우선한다.

### 5.3 새 도구 추가

`mcp_servers/student_info_server.py`를 새로 만들고 다음 도구를 정의한다.

#### `load_student_info_data`

목적:

- `data/student_info_samples.json`을 로드한다.
- 청킹 후 ChromaDB에 저장한다.
- 저장된 문서 수를 반환한다.

기본 인자:

- `filepath: str = "data/student_info_samples.json"`

응답 예시:

```text
✅ 대학생 정보 데이터 로드 완료!

📄 원본 문서: 6건
✂️ 청크 분할: 6건
💾 ChromaDB 저장: 6건
📚 카테고리: transfer / policy / contest
```

#### `search_student_info`

목적:

- 편입학, 국가제도, 공모전/대외활동 관련 정보를 검색한다.
- 기존 학교/학과 공지 검색과 구분되는 응답을 제공한다.

인자:

- `query: str`
- `category: str = ""`
- `n_results: int = 5`

카테고리 처리:

- `transfer`: 편입학/전공심화
- `policy`: 국가제도/장학/청년정책
- `contest`: 공모전/대외활동/인턴십
- 빈 값이면 전체 카테고리 검색

응답에는 다음을 포함한다.

- 제목
- 카테고리
- 요약
- 대상
- 마감일 후보
- 출처
- 다음 추천 행동

#### `get_student_info_stats`

목적:

- 현재 대학생 정보 데이터가 저장되어 있는지 확인한다.

주의:

- 현재 ChromaDB 컬렉션이 공지사항과 같은 컬렉션이면 통계가 섞일 수 있다.
- 10주차 1차 구현에서는 최소 구현으로 전체 ChromaDB 문서 수를 활용한다.
- 11주차 이후에는 공지사항과 대학생 정보를 컬렉션 또는 metadata 기준으로 더 명확히 분리하는 것을 검토한다.

### 5.4 Agent에 도구 연결

`agent/graph.py`에서 기존 `RAG_TOOLS`에 새 `STUDENT_INFO_TOOLS`를 합친다.

권장 방식:

```python
from mcp_servers.student_info_server import STUDENT_INFO_TOOLS

ALL_TOOLS = TASK_TOOLS + CALENDAR_TOOLS + RAG_TOOLS + STUDENT_INFO_TOOLS
```

기존 `RAG_TOOLS` 자체를 공지사항 도구 목록으로 유지하면 역할이 명확하다.

### 5.5 프롬프트 수정

`agent/prompts.py`에 대학생 정보 검색 도구 안내를 추가한다.

추가할 도구 설명:

- `search_student_info`: 편입학, 국가 제도, 공모전/대외활동 정보를 검색
- `load_student_info_data`: 대학생 정보 샘플 데이터를 RAG 시스템에 로드
- `get_student_info_stats`: 대학생 정보 검색 데이터 상태 확인

사용 규칙:

- “학과 공지”, “학교 공지”는 기존 공지 검색 도구 사용
- “편입학”, “전공심화”, “국가장학금”, “국가근로”, “학자금대출”, “공모전”, “대외활동”, “인턴십”은 `search_student_info` 사용
- 검색 결과에 마감일이 있으면 캘린더/과제 등록을 추천

## 6. 구현 순서

10주차 구현은 다음 순서로 진행한다.

1. 현재 실행 환경 복구 또는 사용할 Python 환경 확정
2. `database/db.py`에 장기기억 테이블 생성 SQL 추가
3. 대화 세션/메시지/요약 CRUD 함수 추가
4. `app.py`에 최근 대화 복원 로직 추가
5. `app.py`에 user/assistant 메시지 DB 저장 로직 추가
6. 앱 재시작 후 대화 복원 수동 확인
7. `data/student_info_samples.json` 작성
8. `mcp_servers/student_info_server.py` 추가
9. `agent/graph.py`에 `STUDENT_INFO_TOOLS` 연결
10. `agent/prompts.py`에 새 도구 사용 규칙 추가
11. `load_student_info_data`로 샘플 데이터 저장 확인
12. `search_student_info`로 3개 카테고리 검색 확인
13. 기존 `search_university_notices`, `search_school_notices`가 그대로 동작하는지 확인
14. 최종 테스트 결과를 10주차 실습일지 또는 보고서에 정리

## 7. 예상 파일 변경

10주차 구현에서 변경 또는 추가될 파일은 다음과 같다.

| 파일 | 변경 내용 |
|---|---|
| `database/db.py` | 장기기억 테이블 및 CRUD 함수 추가 |
| `app.py` | 대화 복원 및 메시지 저장 흐름 추가 |
| `mcp_servers/student_info_server.py` | 대학생 정보 검색 도구 신규 추가 |
| `data/student_info_samples.json` | 편입학/국가제도/공모전 샘플 데이터 추가 |
| `agent/graph.py` | 새 도구 목록을 Agent에 연결 |
| `agent/prompts.py` | 새 도구 사용 규칙 추가 |
| `config/mcp_config.json` | 대학생 정보 도구 레지스트리 항목 추가 |
| `tests/test_student_info.py` | 대학생 정보 로드/검색 테스트 추가 |
| `tests/test_memory.py` | 장기기억 저장/복원 테스트 추가 |

10주차에서는 기존 `rag/crawler.py`를 수정하지 않는다. 외부 대학생 정보 실시간 크롤러는 11~13주차에 정보 영역별로 추가한다.

## 8. 테스트 및 검증 시나리오

### 8.1 장기기억 검증

시나리오 1: 메시지 저장

1. 앱에서 “안녕, 내 전공은 컴퓨터시스템공학과야” 입력
2. AI 응답 생성
3. `conversation_messages`에 user/assistant 메시지가 저장되었는지 확인

성공 기준:

- user 메시지와 assistant 메시지가 같은 `session_id`로 저장된다.
- 저장 순서가 대화 순서와 일치한다.

시나리오 2: 앱 재시작 후 복원

1. 앱에서 대화 2~3개 진행
2. 앱 종료
3. 앱 재실행
4. 이전 대화가 채팅창에 다시 표시되는지 확인

성공 기준:

- 최근 대화가 `st.session_state.messages`에 복원된다.
- 새 질문을 이어서 입력할 수 있다.

시나리오 3: 기존 기능 영향 확인

1. 과제 추가
2. 일정 추가
3. 학과 공지 검색
4. 학교 공지 검색

성공 기준:

- 장기기억 기능 추가 후에도 기존 기능이 깨지지 않는다.

### 8.2 대학생 정보 검색 검증

시나리오 1: 데이터 로드

1. `load_student_info_data` 실행
2. `data/student_info_samples.json` 로드
3. ChromaDB 저장 결과 확인

성공 기준:

- 최소 6건 이상의 샘플 정보가 저장된다.
- `transfer`, `policy`, `contest` 카테고리가 모두 포함된다.

시나리오 2: 편입학 검색

질문:

```text
편입학 정보 알려줘
```

성공 기준:

- `transfer` 카테고리 결과가 반환된다.
- 학교명, 지원 조건, 마감일 후보, 출처가 표시된다.

시나리오 3: 국가 제도 검색

질문:

```text
국가장학금 제도 찾아줘
```

성공 기준:

- `policy` 카테고리 결과가 반환된다.
- 신청 대상, 신청 기간, 공식 출처가 표시된다.

시나리오 4: 공모전 검색

질문:

```text
소프트웨어 공모전 추천해줘
```

성공 기준:

- `contest` 카테고리 결과가 반환된다.
- 마감일과 다음 추천 행동이 표시된다.

### 8.3 기존 공지 검색 유지 검증

질문:

```text
학과 장학금 공지 찾아줘
학교 공지사항 검색해줘
```

성공 기준:

- 기존 `search_university_notices`와 `search_school_notices`가 계속 사용된다.
- 대학생 정보 검색 도구와 혼동되지 않는다.

## 9. 10주차 완료 기준

10주차는 다음 기준을 만족하면 완료로 본다.

- 기존 인하공전 학과/학교 공지 크롤러가 유지된다.
- SQLite 장기기억 테이블 3개가 생성된다.
- 사용자/AI 대화가 DB에 저장된다.
- 앱 재실행 후 최근 대화가 복원된다.
- 대학생 정보 샘플 데이터가 추가된다.
- `search_student_info`로 편입학, 국가제도, 공모전 정보를 검색할 수 있다.
- Agent가 기존 공지 검색과 새 대학생 정보 검색을 구분해서 사용할 수 있다.
- 검색 결과에 제목, 요약, 출처, 마감일 후보, 다음 행동이 포함된다.
- 테스트 또는 수동 검증 결과를 10주차 실습일지에 기록할 수 있다.

## 10. 10주차 산출물

10주차가 끝났을 때 남아야 하는 산출물은 다음과 같다.

- 장기기억 DB 테이블 및 저장/복원 기능
- 대학생 정보 검색 도구 1차 버전
- 편입학/국가제도/공모전 샘플 데이터
- 기존 공지 검색 유지 확인 결과
- 10주차 테스트 결과
- 10주차 실습일지에 넣을 구현 내용 정리

## 11. 발표/보고서 작성 포인트

10주차 실습일지나 발표 자료에는 다음처럼 정리하면 좋다.

핵심 문장:

> 10주차에는 기존 인하공업전문대학 공지사항 크롤링 기능을 유지하면서, 9주차에 문서화했던 장기기억 기능을 실제 코드에 반영하고, 편입학/국가제도/공모전 정보를 검색할 수 있는 대학생 정보 검색 기능을 1차 구현하였다.

강조할 점:

- 기존 기능을 폐기하지 않고 확장했다.
- 학교 특화 공지 검색은 그대로 유지했다.
- 장기기억으로 앱 재시작 후에도 대화 맥락을 이어갈 수 있게 했다.
- 대학생 정보 검색으로 CampusAgent의 활용 범위를 넓혔다.
- 11~13주차에는 각 정보 영역의 실시간 수집 범위를 점진적으로 확장할 계획이다.

---

## 12. 10주차 현재 상태 (2026-05-11 기준)

이 문서(§1~§11)는 구현 전 계획서로 작성된 상태이다. 실제 작업 결과 아래 항목들이 이미 코드에 반영되어 있음을 확인하였다.

| 항목 | 실제 위치 | 상태 |
|---|---|---|
| `conversation_sessions / messages / summaries` 테이블 3개 | `database/db.py:65-94` | ✅ 구현됨 |
| 장기기억 CRUD 함수 6개 | `database/db.py:128-267` | ✅ 구현됨 |
| 앱 시작 시 최근 메시지 복원 | `app.py:131-139` | ✅ 구현됨 |
| user/assistant 메시지 DB 저장 | `app.py:183, 257-264` | ✅ 구현됨 |
| `memory_summary`를 시스템 프롬프트에 주입 | `agent/graph.py:88,94`, `agent/prompts.py:67` | ✅ 구현됨 |
| `mcp_servers/student_info_server.py` + 3개 도구 | 파일 전체 | ✅ 구현됨 |
| `data/student_info_samples.json` (3개 카테고리, 각 2건 이상) | 파일 존재 | ✅ 구현됨 |
| `agent/graph.py`에 `STUDENT_INFO_TOOLS` 연결 | `agent/graph.py:23,26` | ✅ 구현됨 |
| `agent/prompts.py`에 새 도구 사용 규칙 + v0.9.0 표기 | `agent/prompts.py:40-43,76-81,84` | ✅ 구현됨 |
| `config/mcp_config.json` 도구 목록 동기화 | `student_info_server` 항목 포함 | ✅ 구현됨 |

## 13. 10주차 체크리스트

### 코드 보강

- [x] `tests/test_memory.py` 추가 (7개 테스트, 2026-05-11 통과)
- [x] `tests/test_student_info.py` 추가 (2개 테스트, 2026-05-11 통과)
- [x] 버전 표기 통일: `pyproject.toml` / `config/settings.py` / `agent/prompts.py` 모두 0.9.0

### 수동 검증 (앱 실행 필요)

- [ ] 앱 부팅 후 SQLite 3개 테이블 자동 생성 확인
- [ ] 채팅 2~3턴 진행 후 `conversation_messages` row 누적 확인
- [ ] 앱 종료 → 재실행 → 이전 대화 복원 확인
- [ ] `load_student_info_data` 호출 후 ChromaDB 카운트 증가 확인
- [ ] "편입학 정보 알려줘" → transfer 결과 포함 확인
- [ ] "국가장학금 제도 찾아줘" → policy 결과 포함 확인
- [ ] "소프트웨어 공모전 추천해줘" → contest 결과 포함 확인
- [ ] `search_university_notices` / `search_school_notices` 회귀 미발생 확인

## 14. Context Notes (의사결정 기록)

**2026-05-11**

- **요약 메모리 자동 트리거 미구현**: `save_memory_summary` 함수와 DB 테이블은 완성되어 있으나, 어떤 코드도 이를 호출하지 않는다. 따라서 현재는 `memory_summary`가 항상 "저장된 장기기억 요약 없음"으로 시스템 프롬프트에 주입된다. 자동 요약 생성(메시지 N개 누적 시 LLM 요약 → `save_memory_summary` 호출) 설계는 14주차 개인화 추천 단계로 명시적으로 미뤘다. 발표 시 "요약 메모리는 설계 완료, 활성화는 14주차"로 설명한다.
- **버전 0.9.0으로 통일**: 9주차 실습일지 기준 장기기억 설계 + 10주차 student_info 검색 1차 구현까지 반영된 상태이므로 0.9.0이 가장 적합하다고 판단. `pyproject.toml`(0.6.0→0.9.0), `config/settings.py`(0.7.0→0.9.0), `agent/prompts.py`(이미 v0.9.0) 세 곳을 맞췄다.
- **MemorySaver와 SQLite 장기기억 역할 분리**: `MemorySaver`는 현재 실행 중인 LangGraph 세션의 단기 메모리(앱이 살아 있는 동안), SQLite는 앱 재시작 이후에도 유지되는 장기 기록. 두 계층은 `app.py`의 `graph_memory_hydrated` 플래그를 통해 첫 번째 turn에만 DB 메시지를 그래프에 주입하고 이후는 MemorySaver가 자동 누적하도록 역할을 나눴다.
- **ChromaDB 컬렉션 분리 미결**: 공지사항(`search_university_notices`)과 대학생 정보(`search_student_info`)가 같은 `university_notices` 컬렉션을 공유한다. 현재는 `category` metadata 필드로 구분하지만 완전한 분리는 아니다. 11주차 이후 검토 항목으로 남긴다.

## 15. 검증 결과

### 자동 테스트 (2026-05-11)

```
42 passed, 1 warning in 9.39s
```

| 파일 | 테스트 수 | 결과 |
|---|---|---|
| `test_task.py` | 13 | ✅ 통과 |
| `test_calendar.py` | 12 | ✅ 통과 |
| `test_memory.py` | 7 | ✅ 통과 |
| `test_rag.py` | 8 | ✅ 통과 |
| `test_student_info.py` | 2 | ✅ 통과 |

DeprecationWarning 1건: Python 3.14와 chromadb의 `asyncio.iscoroutinefunction` 사용 차이. 기능에 영향 없음.

### 수동 검증

*앱 실행 후 결과를 여기에 기록한다.*

## 16. 11주차로 넘기는 항목

- `tests/test_agent.py` 작성: LangGraph tool routing, API 키 없음 fallback, `current_context` 반영 여부
- 자동 요약 메모리 트리거 설계: 메시지 N개 누적 시 LLM 요약 생성 → `save_memory_summary` 호출
- ChromaDB 컬렉션 분리 검토: `university_notices` 컬렉션을 공지/대학생 정보로 구분
- `research.md` 경로 갱신: `C:\workspace\CampusAgent` → `C:\Users\kimka\OneDrive\Documents\GitHub\CampusAgent`
- 편입학 고도화 (`md_file/week_11_plan.md` 신규 작성)

## 17. 10주차 추가 작업: 외부 소스 대학생 정보 확장 ✅ 완료 (2026-05-12)

추가 작업 기준일: 2026-05-12  
배경: `search_student_info_live`가 인하공전 학교 공지만 크롤링하므로 타학교 편입학·외부 장학·취업·공모전 정보를 실제 해당 소스에서 가져오는 확장을 진행한다.

### 17.1 추가할 외부 소스

| 소스 | 접근 방식 | API 키 | 법적 안전성 |
|------|---------|--------|-----------|
| 어디가(adiga.kr) — 편입학 모집요강 | HTML 크롤링 | 불필요 | 공공기관 ✅ |
| 온통청년(youthcenter.go.kr) — 장학/청년정책 | REST API | `YOUTH_CENTER_API_KEY` | 공공기관 ✅ |
| 워크넷(work.go.kr) — 채용/인턴십 | REST API | `WORKNET_API_KEY` | 공공기관 ✅ |
| K-스타트업(k-startup.go.kr) — 공모전 | HTML 크롤링 | 불필요 | 공공기관 ✅ |

기존 `search_student_info_live`(인하공전 학교 공지 기반)는 그대로 유지한다.

### 17.2 신규 생성 파일

**`rag/external_crawler.py`**

4개 외부 소스 크롤러를 담는 전용 파일. 각 함수는 `List[dict]` (title, content, date, url, source, category) 반환.

```python
def crawl_transfer_by_school(school_name: str, max_results: int = 5) -> List[dict]:
    """어디가 편입학 검색 페이지를 HTML 파싱."""

def fetch_youth_policy(query: str, api_key: str, page: int = 1, display: int = 5) -> List[dict]:
    """온통청년 API: https://www.youthcenter.go.kr/opi/youthPlcyList.do"""

def fetch_worknet_jobs(query: str, api_key: str, page: int = 1, display: int = 5) -> List[dict]:
    """워크넷 API: https://openapi.work.go.kr/opi/opi/opia/wantedApi.do"""

def crawl_kstartup_contest(query: str = "", max_results: int = 5) -> List[dict]:
    """K-스타트업 공모전 목록 HTML 크롤링."""
```

공통 처리:
- robots.txt 허용 경로만 접근
- 요청 간 1초 딜레이 (기존 `REQUEST_DELAY` 패턴 그대로)
- API 키 미설정 시 빈 리스트 반환 (호출 측에서 안내 메시지 처리)

### 17.3 수정 파일

**`config/settings.py`**
```python
YOUTH_CENTER_API_KEY: str = os.getenv("YOUTH_CENTER_API_KEY", "")
WORKNET_API_KEY: str = os.getenv("WORKNET_API_KEY", "")
```

**`mcp_servers/student_info_server.py`** — 도구 4개 추가

| 도구 | 설명 |
|------|------|
| `search_transfer_by_school(school_name)` | 어디가에서 특정 학교 편입학 정보 크롤링 |
| `search_scholarship_policy(query)` | 온통청년 API로 장학금·청년정책 검색 |
| `search_job_intern(query)` | 워크넷 API로 채용·인턴십 검색 |
| `search_contest_external(query)` | K-스타트업에서 공모전·대외활동 크롤링 |

각 도구 공통:
- API 키 미설정 시 에러 대신 설정 안내 문자열 반환
- 결과를 ChromaDB에 upsert (category 메타데이터 포함)
- 출처 URL 포함 + "원문 재확인 권장" footer

**`agent/prompts.py`** — 새 도구 사용 가이드 4줄 추가

### 17.4 API 키 발급 방법 (사용자 안내)

| 키 이름 | 발급처 | 소요 시간 |
|---------|------|---------|
| `YOUTH_CENTER_API_KEY` | youthcenter.go.kr → 마이페이지 → 오픈API 신청 | 즉시~1일 |
| `WORKNET_API_KEY` | openapi.work.go.kr → 회원가입 후 신청 | 즉시~1일 |

### 17.5 검증 시나리오

1. API 키 없이 `search_scholarship_policy("국가장학금")` → 키 설정 안내 메시지 반환 (에러 없음)
2. API 키 설정 후 동일 요청 → 온통청년 결과 반환
3. `search_transfer_by_school("연세대")` → 어디가 결과 반환
4. `search_job_intern("소프트웨어 인턴")` → 워크넷 결과 반환
5. `search_contest_external("창업 공모전")` → K-스타트업 결과 반환
6. `pytest tests/test_student_info.py` → 기존 4개 테스트 포함 전체 통과
7. `pytest tests/` → 전체 44건 이상 통과 (회귀 없음)

### 17.6 실제 검증 결과 (2026-05-12)

| 항목 | 결과 |
|------|------|
| `pytest tests/test_student_info.py` | ✅ 8건 통과 (기존 4 + 신규 4) |
| `pytest tests/` 전체 | ✅ 48건 통과 (회귀 없음) |
| K-스타트업 실시간 크롤링 | ✅ 3건 정상 수집 확인 |
| API 키 없이 온통청년 도구 호출 | ✅ 에러 없이 설정 안내 반환 |
| API 키 없이 워크넷 도구 호출 | ✅ 에러 없이 설정 안내 반환 |
| 어디가 편입학: 학교 레지스트리 없을 때 | ✅ fallback 안내 항목 반환 |

**미완료 항목**: 온통청년 API 키, 워크넷 API 키 발급 후 실제 API 응답 검증 필요. 키 발급은 각 사이트에서 별도 진행.

### 17.7 추가된 파일

| 파일 | 내용 |
|------|------|
| `rag/external_crawler.py` (신규) | 어디가/온통청년/워크넷/K-스타트업 크롤러 |
| `config/settings.py` | `YOUTH_CENTER_API_KEY`, `WORKNET_API_KEY` 추가 |
| `mcp_servers/student_info_server.py` | 도구 4개 추가 (총 8종), 헬퍼 함수 2개 |
| `agent/prompts.py` | 새 도구 안내 + 사용 가이드 추가 |
| `tests/test_student_info.py` | 신규 테스트 4건 추가 |
