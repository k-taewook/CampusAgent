# CampusAgent 9~15주차 개발 계획 정리

작성 기준일: 2026-05-12 (최초 2026-05-09, 10주차 완료 반영 업데이트)
프로젝트 단계: 15주 진행 중 11주차 시작  
기준 자료: 8주차 중간발표 PPT, 9주차 실습일지, 10주차 구현 완료 결과, cleanup_plan.md

## 1. 현재 상황 정리

CampusAgent는 대학생의 과제, 일정, 공지사항 확인을 하나의 대화형 인터페이스에서 처리하는 로컬 AI 어시스턴트이다. 현재 프로젝트는 Streamlit UI, LangGraph Agent, LangChain Tool 기반 도구, SQLite, ChromaDB, 실시간 공지 크롤러를 중심으로 구성되어 있다.

8주차 중간발표 기준으로는 과제 관리, 일정 관리, 학교/학과 공지 검색, 4-Tabs UI, Gemini/OpenAI 연동, 세션 내 대화 기억 기능이 구현된 상태로 정리되었다. 이후 9주차 실습일지에는 장기기억 문제 해결 내용이 작성되어 있지만, 실제 프로젝트 구현은 아직 진행하지 못한 상태이다.

따라서 앞으로의 계획은 다음 전제를 기준으로 다시 정리한다.

- 9주차 실습일지는 장기기억 구현 방향과 결과를 먼저 문서화한 상태이다.
- 실제 코드에는 아직 9주차 장기기억 기능이 반영되지 않았다.
- 10주차에는 9주차 실습일지 내용을 실제 프로젝트에 반영하면서, 동시에 대학생 통합 정보 검색 기능의 1차 구현까지 진행하는 방향으로 잡는다.
- 11~15주차는 정보 수집 범위 확장, 개인화 추천, 테스트, 최종 발표 준비를 단계적으로 진행한다.

## 2. 9주차 실습일지 파악 결과

9주차 실습일지의 주제는 **장기기억 문제 해결 및 대화 세션 복원 기능 구현**이다. 문서에서는 8주차까지의 한계였던 `MemorySaver` 기반 세션 기억 문제를 해결하기 위해 SQLite 기반 장기기억 구조를 도입한 것으로 정리되어 있다.

9주차 실습일지에 작성된 핵심 내용은 다음과 같다.

### 2.1 8주차까지의 한계

기존 CampusAgent는 LangGraph `MemorySaver`를 사용하여 실행 중인 세션에서는 대화 맥락을 유지할 수 있었다. 하지만 앱을 재시작하면 이전 대화 내역이 사라지고, 사용자가 다시 전공, 학년, 과제 맥락, 공지 검색 이력을 설명해야 하는 문제가 있었다.

실습일지에서 정의한 문제는 다음과 같다.

- `MemorySaver`는 세션 내부 기억만 유지한다.
- 앱 재시작 시 대화 이력이 초기화된다.
- 사용자의 반복 관심사나 학습 맥락을 장기적으로 활용하기 어렵다.
- 긴 대화가 누적되면 LLM에 전달되는 토큰 부담이 커진다.
- Streamlit 세션 상태와 LangGraph 메모리 사이의 일관성이 깨질 수 있다.

### 2.2 9주차 구현 목표

9주차 실습일지는 다음 구현 목표를 제시하고 있다.

1. 대화 메시지를 SQLite에 영구 저장한다.
2. 앱 재실행 후에도 이전 대화 이력을 불러올 수 있게 한다.
3. 모든 대화 원문을 계속 LLM에 넣지 않고 요약 메모리를 함께 관리한다.
4. LangGraph의 세션 기억과 DB의 장기기억을 함께 사용할 수 있도록 흐름을 정리한다.
5. 장기기억 기능이 기존 과제, 일정, RAG 기능을 방해하지 않도록 통합한다.

### 2.3 9주차 실습일지의 설계 내용

실습일지에서는 기존 `campus_tasks.db`에 장기기억 전용 테이블을 추가하는 구조를 제안한다.

| 테이블 | 목적 |
|---|---|
| `conversation_sessions` | 대화 세션 단위 정보 저장 |
| `conversation_messages` | 사용자/AI/tool 메시지 원문 저장 |
| `memory_summaries` | 긴 대화를 압축한 요약 메모리 저장 |

문서상 흐름은 다음과 같다.

1. 사용자가 메시지를 입력한다.
2. Streamlit 세션 메시지에 추가한다.
3. `conversation_messages`에 user 메시지를 저장한다.
4. LangGraph Agent를 실행한다.
5. AI 응답을 생성한다.
6. Streamlit 세션 메시지에 assistant 응답을 추가한다.
7. `conversation_messages`에 assistant 메시지를 저장한다.
8. 앱 재실행 시 DB에서 최근 세션과 메시지를 불러와 채팅창을 복원한다.

### 2.4 요약 메모리 구조

실습일지에서는 모든 대화 원문을 계속 LLM에 전달하는 대신, 최근 대화는 원문으로 유지하고 오래된 대화는 요약하여 `memory_summaries`에 저장하는 구조를 제안한다.

이 구조의 목적은 다음과 같다.

- 앱 재시작 후에도 이전 대화 맥락 유지
- 토큰 사용량 감소
- 과제, 일정, 공지 검색 흐름의 연속성 확보
- 사용자 전공, 학년, 관심사 기반 개인화 응답 강화

### 2.5 실제 프로젝트 반영 상태

현재 코드 기준으로는 9주차 실습일지에 적힌 장기기억 기능이 아직 반영되어 있지 않다. `database/db.py`에는 `assignments`, `schedules`, `user_settings` 테이블만 생성되고 있으며, `conversation_sessions`, `conversation_messages`, `memory_summaries` 테이블은 아직 없다.

또한 `agent/graph.py`는 여전히 LangGraph `MemorySaver`를 사용하고 있고, Streamlit 앱의 대화 이력은 `st.session_state.messages` 중심으로 관리된다.

따라서 9주차 내용은 “완료된 기능”이 아니라 **10주차에 실제 구현으로 이어받아야 할 선행 문서/설계 내용**으로 보는 것이 정확하다.

## 3. 8주차 향후 계획 수정 방향

8주차 PPT의 향후 계획은 현재 상황에 맞게 다음처럼 수정한다.

| 기존 계획 | 수정 방향 | 현재 반영 방식 |
|---|---|---|
| 크롤러 범위 제한 | 대학생 정보 수집원 확장 | 편입학, 국가 제도, 공모전/대외활동 정보까지 확장 |
| 장기 기억 없음 | 9주차 실습일지 기반으로 10주차 실제 구현 | 문서상 설계는 완료, 실제 코드는 10주차에 반영 |
| MCP 프로토콜 미준수 | 최종 필수 구현이 아닌 구조 개선 후보 | 기능 완성도와 발표 안정성을 우선 |
| 테스트 커버리지 부족 | 12~15주차 기능별 테스트와 데모 검증으로 보강 | 장기기억, 정보검색, 일정 연동 중심 테스트 추가 |

특히 장기기억은 9주차 보고서에서 이미 다룬 핵심 주제이므로, 10주차 초반에 실제 코드로 반영하고 이후 정보 검색 확장 기능과 연결하는 방식이 가장 자연스럽다.

## 4. 10~15주차 주차별 구현 계획

### 10주차 ✅ 완료 (2026-05-09 ~ 2026-05-12): 장기기억 실제 반영 + 대학생 정보 검색 구현

9주차 설계 내용을 실제 코드로 반영하고, 외부 공공 소스 4개를 추가한 대학생 정보 검색 확장까지 완료했다.

완료된 구현 내용:

- SQLite에 `conversation_sessions`, `conversation_messages`, `memory_summaries` 테이블 추가
- 사용자 메시지/AI 응답 DB 저장 및 앱 재시작 시 대화 복원 흐름 구현
- `편입학(transfer)`, `국가제도(policy)`, `공모전/대외활동(contest)` 카테고리별 샘플 데이터 + ChromaDB 저장
- `search_student_info`, `search_student_info_live` 도구로 RAG 검색 및 실시간 크롤링 지원
- 외부 소스 4개 추가 (`rag/external_crawler.py` 신규 생성)
  - `search_transfer_by_school`: 어디가(adiga.kr) HTML 크롤링으로 타학교 편입학 정보
  - `search_scholarship_policy`: 온통청년 API로 국가장학금·청년정책 검색
  - `search_job_intern`: 워크넷 공채속보 API로 채용공고 검색
  - `search_contest_external`: K-스타트업 HTML 크롤링으로 공모전/창업 지원 정보
- 버전 v0.9.0 통일, 테스트 48개 전체 통과

현재 상태: LangChain 도구 20개, SQLite 테이블 6개, pytest 48 passed

---

### 11주차 (5/13 ~ 5/20): 과제 자동 분해 + 서브태스크 트리

큰 과제를 LLM이 단계별 서브태스크로 자동 분해하고, 트리 구조로 관리하는 기능을 추가한다.

구현 내용:

- LLM이 큰 과제를 받으면 자동으로 서브태스크 5~7개로 분해
- 부모-자식 관계의 트리 구조로 SQLite에 저장
- 진행률 자동 계산 (서브태스크 완료 비율)
- UI에서 트리 뷰로 표시 + 개별 체크박스 토글

수정 파일:

- `database/db.py` — `assignments` 테이블에 `parent_id`, `progress` 컬럼 추가
- `database/models.py` — `AssignmentCreate`에 `parent_id` 필드 추가
- `mcp_servers/task_server.py` — `decompose_task(title, due_date)` 툴 신규 추가, `list_tasks`에 트리 옵션
- `agent/prompts.py` — 분해 가이드 섹션 추가
- `app.py` — 과제 대시보드 탭에 트리 뷰 (들여쓰기 + 진행률 바)

완료 기준:

- “기말 프로젝트 추가해줘 마감 6월 10일” → 5~7개 서브태스크가 자동 생성된다.
- 서브태스크 하나 완료 처리 시 부모 과제 진행률이 자동 갱신된다.
- `pytest tests/test_task.py` 전체 통과.

---

### 12주차 (5/20 ~ 5/27): Multi-Agent 아키텍처 재구조화

현재 단일 에이전트 + 20툴 구조를 Supervisor + 4 Specialist 패턴으로 재배치한다.

구현 내용:

- **Supervisor**: 사용자 입력을 보고 어느 Specialist로 라우팅할지 결정
- **TaskAgent**: 과제 관련 툴 전담
- **CalendarAgent**: 캘린더 관련 툴 전담
- **NoticeAgent**: 학과/학교 공지 검색 전담
- **InfoAgent**: 대학생 정보(편입/장학/공모전) 전담
- 기존 툴 로직은 그대로 두고 그래프 구조만 재배치 (LangGraph multi-agent 패턴 사용)

수정 파일:

- `agent/graph.py` — 전면 재작성, 노드를 5개로 분리, conditional edge로 라우팅
- `agent/state.py` — `next_agent: str` 필드 추가 (라우팅 결정용)
- 신규 `agent/specialists/` 디렉토리 — specialist 모듈 분리 (`task_agent.py`, `calendar_agent.py`, `notice_agent.py`, `info_agent.py`)
- `agent/prompts.py` — Supervisor 프롬프트 + 각 Specialist용 프롬프트 분리

완료 기준:

- “공지 검색하고 과제로 등록해줘” 같은 복합 요청 시 Supervisor가 NoticeAgent → TaskAgent 순서로 호출한다.
- 라우팅 로그 출력으로 어느 에이전트가 호출됐는지 확인 가능하다.
- 기존 기능 회귀 없음 (`pytest tests/` 전체 통과).

---

### 13주차 (5/27 ~ 6/3): 일일 자동 브리핑 + 백그라운드 스케줄러

APScheduler로 매일 아침 학과/학교 공지를 자동 크롤링하고 LLM으로 요약해 Streamlit 메인 화면에 표시한다.

구현 내용:

- `APScheduler`로 매일 아침 8시 (또는 사용자 지정 시간) 자동 실행
- 사용자 전공 키워드로 학과 + 학교 공지 자동 크롤링
- 결과를 LLM으로 3~5줄 요약
- Streamlit 메인 화면 상단에 “오늘의 브리핑” 카드 표시
- DB에 브리핑 히스토리 저장 (`briefing_history` 테이블)

수정 파일:

- 신규 `scheduler/briefing.py` — 스케줄러 작업 정의
- `database/db.py` — `briefing_history` 테이블 + CRUD
- `app.py` — 메인 페이지 상단에 브리핑 카드, 설정 탭에 알림 시간 토글
- `pyproject.toml` — `apscheduler>=3.10` 추가
- 신규 `mcp_servers/briefing_server.py` — `get_today_briefing`, `run_briefing_now` 툴

완료 기준:

- 설정 탭에서 “지금 브리핑 실행” 버튼 클릭 시 5~15초 후 브리핑 카드가 표시된다.
- 브리핑 히스토리 탭에서 과거 7일 브리핑을 조회할 수 있다.
- APScheduler가 Streamlit 재시작 후에도 유지된다 (`@st.cache_resource`로 감싸기).

---

### 14주차 (6/3 ~ 6/10): RAG 품질 평가 + 최종 발표 준비

정량 지표로 RAG 검색 품질을 측정하고, 발표 슬라이드용 차트를 생성한다. 기말 발표가 이 주차 말에 있다.

구현 내용:

- 정답이 있는 Q&A 평가셋 30~50건 구축
- RAGAS (또는 자체 평가 스크립트)로 4개 지표 측정
  - **Faithfulness** (답변이 검색 결과에 충실한가)
  - **Answer Relevancy** (답변이 질문과 관련 있는가)
  - **Context Precision** (검색된 컨텍스트가 정확한가)
  - **Context Recall** (필요한 컨텍스트를 다 가져왔는가)
- 결과를 Streamlit “평가” 탭에 차트로 시각화
- 발표 슬라이드용 캡처 + README 업데이트

수정 파일:

- 신규 `evaluation/rag_eval.py` — 평가 파이프라인
- 신규 `evaluation/qa_dataset.json` — 정답셋 (질문, 정답, 참조 공지)
- 신규 `tests/test_rag_quality.py` — pytest로 자동 평가 실행
- `app.py` — “평가” 탭 추가 (메트릭 카드 + bar chart)
- `README.md` — 측정 결과 섹션 추가

완료 기준:

- `pytest tests/test_rag_quality.py` 실행 시 4개 지표가 모두 출력된다.
- 발표 데모에서 “검색 정확도 XX%, Faithfulness XX%” 슬라이드를 사용할 수 있다.
- 평가 탭에서 카테고리별 비교 차트를 확인할 수 있다.

---

### 15주차 (6/10~): 최종 통합 테스트 및 발표 마무리

구현된 기능을 하나의 시연 흐름으로 통합하고 발표 자료를 완성한다.

구현 내용:

- 과제 자동 분해 → Multi-Agent 라우팅 → 오늘의 브리핑 → RAG 정량 지표의 4-step 데모 시나리오 구성
- 핵심 기능별 정상 동작 확인 테스트
- 예외 상황 테스트: API 키 없음, 크롤링 실패, 대화 복원 실패, 검색 결과 없음
- 최종 발표 PPT 보완 및 시연 영상 또는 라이브 데모용 질문 리스트 작성

발표 데모 시나리오:

1. “기말 프로젝트 추가해줘 마감 6/10” → **서브태스크 자동 분해** 시연
2. “오늘 학과 공지 뭐 있어?” → **NoticeAgent**로 라우팅되는 로그 표시 (Multi-Agent)
3. 메인 화면에 떠 있는 **오늘의 브리핑** 카드 → 자동 실행됨을 강조
4. “평가” 탭 열어서 **정량 지표 슬라이드** 표시

완료 기준:

- 주요 기능이 하나의 사용자 흐름으로 자연스럽게 연결된다.
- 발표 중 보여줄 질문과 기대 응답이 준비된다.
- 기능 실패 시에도 사용자에게 이해 가능한 안내 메시지가 출력된다.

## 5. 리스크 및 완화책

- **Multi-Agent 라우팅 정확도 저하**: 12주차 후반에 기존 시나리오 전부 회귀 테스트로 확인한다.
- **APScheduler가 Streamlit 재시작 시 종료**: `BackgroundScheduler`를 `@st.cache_resource`로 감싸서 유지한다.
- **RAGAS 의존성이 무거움**: 자체 구현 (cosine similarity + LLM-as-judge)으로 대체 가능하다.
- **워크넷 공채속보 API 응답 필드명 불확실**: API 키 등록 후 실제 응답으로 `rag/external_crawler.py`의 필드명을 조정한다.

## 6. 최종 발표 전 점검 항목

- 앱 재시작 후 대화 복원 여부 확인
- `conversation_sessions`, `conversation_messages`, `memory_summaries` 테이블 정상 동작 확인
- 과제 서브태스크 트리 시연 가능 여부
- Multi-Agent 라우팅 로그 출력 확인
- 오늘의 브리핑 카드 자동 표시 확인
- RAG 품질 지표 4개 수치 출력 확인
- API 키 없거나 크롤링 실패 시 안내 메시지 정상 출력
- 발표용 질문 리스트와 예상 응답 준비

## 7. 기대 결과

이 계획이 완료되면 CampusAgent는 기존의 “과제, 일정, 공지사항 관리 AI”에서 다음 모습으로 발전한다.

- 큰 과제를 입력하면 LLM이 서브태스크로 자동 분해하고 진행률을 추적한다.
- 단일 에이전트 대신 역할별 Specialist가 각 도메인을 전담해 응답 품질이 높아진다.
- 매일 아침 학과/학교 공지를 자동 수집하고 요약해 화면에 표시한다.
- RAG 검색 품질을 정량 지표로 측정해 발표에서 기술적 깊이를 어필할 수 있다.
- 편입학, 장학금, 공모전 등 외부 공공 소스 정보를 한 대화창에서 확인할 수 있다.
- 기능 실패 시에도 사용자에게 이해 가능한 안내 메시지를 제공한다.
