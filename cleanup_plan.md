# CampusAgent 11~14주 로드맵 (기술 깊이 중심)

## Context

현재 CampusAgent는 v0.9.0 상태로, 16개 LangChain 도구를 단일 LangGraph 에이전트에 바인딩하는 구조다. 14주차(6/3~6/10)에 기말 발표가 있어 실질적으로 4주 안에 발표 가능한 수준까지 끌어올려야 한다. 사용자는 **기술 깊이**를 우선시하며, 바이브코딩 기반이라 난이도가 높아도 무방하다.

선택된 4가지 확장 축은 다음과 같다.
1. **과제 자동 분해 (서브태스크 트리)** — 큰 과제를 LLM이 단계별로 쪼갬
2. **Multi-Agent 아키텍처 재구조화** — Supervisor + Specialist 패턴
3. **일일 자동 브리핑/알림** — 백그라운드 스케줄러 기반
4. **RAG 품질 평가 시스템** — 정량 지표로 발표 어필

목표는 "단순한 챗봇"에서 "능동적이고 측정 가능한 학사 어시스턴트"로의 전환이다.

---

## Week 11 (5/13 ~ 5/20): 과제 자동 분해 + 서브태스크 트리

### 구현 내용
- LLM이 큰 과제를 받으면 자동으로 서브태스크 5~7개로 분해
- 부모-자식 관계의 트리 구조로 SQLite에 저장
- 진행률 자동 계산 (서브태스크 완료 비율)
- UI에서 트리 뷰로 표시 + 개별 체크박스 토글

### 수정 파일
- `database/db.py` — `assignments` 테이블에 `parent_id`, `progress` 컬럼 추가
- `database/models.py` — `AssignmentCreate`에 `parent_id` 필드 추가
- `mcp_servers/task_server.py` — `decompose_task(title, due_date)` 툴 신규 추가, `list_tasks`에 트리 옵션
- `agent/prompts.py` — 분해 가이드 섹션 추가 (예: "기말 프로젝트면 주제선정→자료조사→초안→완성 식으로")
- `app.py` — 과제 대시보드 탭에 트리 뷰 (들여쓰기 + 진행률 바)

### 재사용 가능한 기존 자산
- `database/db.py:add_assignment` — parent_id 인자만 추가하면 그대로 사용
- `agent/graph.py`의 LLM 인스턴스 — 분해 로직에 그대로 호출 (`llm.invoke([HumanMessage(...)])`)
- `mcp_servers/task_server.py:TASK_TOOLS` 리스트에 새 툴만 추가

### 검증
- 챗봇에 "기말 프로젝트 추가해줘 마감 6월 10일" → 5~7개 서브태스크가 자동 생성되는지
- 서브태스크 하나 완료 처리 → 부모 과제 진행률 자동 갱신
- `pytest tests/test_task.py` 전부 통과

---

## Week 12 (5/20 ~ 5/27): Multi-Agent 아키텍처 재구조화

### 구현 내용
현재 단일 에이전트 + 16툴 구조를 **Supervisor + 4 Specialist** 패턴으로 재배치.
- **Supervisor**: 사용자 입력을 보고 어느 Specialist로 라우팅할지 결정
- **TaskAgent**: 과제 5툴 전담
- **CalendarAgent**: 캘린더 6툴 전담
- **NoticeAgent**: 학과/학교 공지 검색 전담
- **InfoAgent**: 대학생 정보(편입/장학/공모전) 전담

기존 툴 로직은 그대로 두고 그래프 구조만 재배치한다. LangGraph의 multi-agent 패턴 사용.

### 수정 파일
- `agent/graph.py` — 전면 재작성. 노드를 5개로 분리, conditional edge로 라우팅
- `agent/state.py` — `next_agent: str` 필드 추가 (라우팅 결정용)
- 신규 `agent/specialists/` 디렉토리 — 각 specialist 모듈 분리 (`task_agent.py`, `calendar_agent.py`, `notice_agent.py`, `info_agent.py`)
- `agent/prompts.py` — Supervisor 프롬프트 + 각 Specialist용 프롬프트 분리

### 재사용 가능한 기존 자산
- `mcp_servers/*` 의 모든 툴 — 그대로 각 Specialist에 바인딩
- `MemorySaver` 기반 세션 메모리 — Supervisor 레벨에서 유지
- 현재 `system_prompt_template`의 도구 사용 가이드 — 각 Specialist 프롬프트로 분배

### 검증
- "공지 검색하고 과제로 등록해줘" 같은 복합 요청 → Supervisor가 NoticeAgent → TaskAgent 순차 호출
- 라우팅 로그 출력으로 어느 에이전트가 호출됐는지 확인 가능
- 기존 기능 회귀 없음 (`pytest tests/test_agent.py`)

---

## Week 13 (5/27 ~ 6/3): 일일 자동 브리핑 + 백그라운드 스케줄러

### 구현 내용
- `APScheduler`로 매일 아침 8시 (또는 사용자 지정) 자동 실행
- 사용자 전공 키워드로 학과 + 학교 공지 자동 크롤링
- 결과를 LLM으로 3~5줄 요약
- Streamlit 메인 화면 상단에 "오늘의 브리핑" 카드 표시
- DB에 브리핑 히스토리 저장 (`briefing_history` 테이블)

### 수정 파일
- 신규 `scheduler/briefing.py` — 스케줄러 작업 정의
- `database/db.py` — `briefing_history` 테이블 + CRUD
- `app.py` — 메인 페이지 상단에 브리핑 카드, 설정 탭에 알림 시간 토글
- `pyproject.toml` — `apscheduler>=3.10` 추가
- 신규 `mcp_servers/briefing_server.py` — `get_today_briefing`, `run_briefing_now` 툴

### 재사용 가능한 기존 자산
- `rag/crawler.py` — 학과/학교 크롤러 그대로 호출
- `agent/graph.py`의 LLM — 요약 작업에 그대로 활용
- `config/settings.py:USER_MAJOR` — 필터링 키워드

### 검증
- 설정 탭에서 "지금 브리핑 실행" 버튼 → 5~15초 후 카드 표시
- 다음날 아침 자동 실행 (시간을 5분 뒤로 임시 설정하여 확인)
- 브리핑 히스토리 탭에서 과거 7일 브리핑 조회

---

## Week 14 (6/3 ~ 6/10): RAG 품질 평가 + 최종 발표 준비

### 구현 내용
- 정답이 있는 Q&A 평가셋 30~50건 구축
- RAGAS (또는 자체 평가 스크립트)로 4개 지표 측정
  - **Faithfulness** (답변이 검색 결과에 충실한가)
  - **Answer Relevancy** (답변이 질문과 관련 있는가)
  - **Context Precision** (검색된 컨텍스트가 정확한가)
  - **Context Recall** (필요한 컨텍스트를 다 가져왔는가)
- 결과를 Streamlit "평가" 탭에 차트로 시각화
- 발표 슬라이드용 캡처 + README 업데이트

### 수정 파일
- 신규 `evaluation/rag_eval.py` — 평가 파이프라인
- 신규 `evaluation/qa_dataset.json` — 정답셋 (질문, 정답, 참조 공지)
- 신규 `tests/test_rag_quality.py` — pytest로 자동 평가 가능하게
- `app.py` — "평가" 탭 추가 (메트릭 카드 + bar chart)
- `pyproject.toml` — `ragas>=0.2` 또는 자체 구현 시 생략
- `README.md` — 측정 결과 섹션 추가

### 재사용 가능한 기존 자산
- `rag/retriever.py:search_notices` — 평가 대상 함수
- `mcp_servers/rag_server.py` — 평가 대상 도구
- `data/sample_notices.json` + `data/student_info_samples.json` — 평가셋 생성 베이스

### 검증
- `pytest tests/test_rag_quality.py` → 4개 지표 모두 출력
- 발표 데모에서 "검색 정확도 XX%, Faithfulness XX%" 슬라이드 사용
- 평가 탭에서 모델별/카테고리별 비교 차트 확인

---

## 발표 데모 시나리오 (14주차 말)

이 4주를 거치면 발표 때 다음 흐름이 가능해진다.
1. 음성 또는 텍스트로 "기말 프로젝트 추가해줘 마감 6/10" → **서브태스크 자동 분해** 시연
2. "오늘 학과 공지 뭐 있어?" → **NoticeAgent**로 라우팅되는 로그 보여줌 (Multi-Agent)
3. 메인 화면에 떠 있는 **오늘의 브리핑** 카드 → 자동 실행됨을 강조
4. "평가" 탭 열어서 **정량 지표 슬라이드** 보여줌

---

## 리스크 및 완화책

- **Multi-Agent 라우팅 정확도 저하 가능성** → 12주차 후반에 회귀 테스트로 기존 시나리오 전부 통과 확인
- **APScheduler가 Streamlit 재시작 시 죽음** → `BackgroundScheduler`를 `app.py`의 `@st.cache_resource`로 감싸서 유지
- **RAGAS 의존성이 무거움** → 자체 구현 (cosine similarity + LLM-as-judge)로 대체 가능

---

## 진행 순서 권장

각 주차 작업이 누적되므로 의존성을 고려한 순서:
- **11주 → 12주**: 서브태스크 툴이 추가된 상태에서 Multi-Agent로 묶이는 게 자연스러움
- **12주 → 13주**: 브리핑은 결국 NoticeAgent를 호출하는 백그라운드 작업이므로 Multi-Agent가 먼저
- **13주 → 14주**: 평가셋은 기존 RAG 기능 전체를 대상으로 하므로 모든 기능 안정화 후
