# CampusAgent 10주차 실습일지

작성일: 2026-05-11
주차: 10주차 (전체 15주 중)
작성자: 김태욱

---

## 1. 이번 주 목표

10주차 목표는 크게 두 가지였다.

1. 9주차 실습일지에 먼저 문서화했던 SQLite 기반 장기기억 기능을 실제 코드에 반영한다.
2. 기존 인하공업전문대학 공지사항 크롤링 기능은 그대로 유지하면서, 편입학/국가제도/공모전 정보를 검색할 수 있는 대학생 정보 검색 기능을 별도로 추가한다.

구현 원칙은 **기존 기능을 갈아엎지 않고 확장한다**는 것이었다. 학과/학교 공지 검색은 CampusAgent의 핵심 장점이므로 그대로 유지하고, 새 기능은 기존 RAG 파이프라인을 재사용하여 역할만 분리하는 방식으로 붙였다.

---

## 2. 구현 내용

### 2.1 SQLite 기반 장기기억

9주차 설계 문서에 따라 기존 `campus_tasks.db`에 장기기억 전용 테이블 3개를 추가했다.

| 테이블 | 역할 |
|---|---|
| `conversation_sessions` | 대화 세션 단위 정보 저장 |
| `conversation_messages` | user/assistant/system/tool 메시지 원문 저장 |
| `memory_summaries` | 오래된 대화를 압축한 요약 메모리 저장 |

`database/db.py`에 다음 함수를 추가하여 대화 기록의 저장, 복원, 삭제를 처리할 수 있도록 했다.

- `get_or_create_conversation_session(session_id, title)`: 세션 생성 또는 조회
- `save_conversation_message(session_id, role, content)`: 메시지 저장
- `load_recent_conversation_messages(session_id, limit)`: 최근 메시지 복원
- `save_memory_summary(session_id, summary)`: 요약 메모리 저장
- `get_latest_memory_summary(session_id)`: 최신 요약 조회
- `clear_conversation_history(session_id)`: 대화 이력 초기화

`app.py`에는 앱 시작 시 최근 대화를 불러와 `st.session_state.messages`에 복원하는 로직과, 사용자 입력 및 AI 응답마다 DB에 저장하는 로직을 추가했다.

**MemorySaver와 SQLite 장기기억의 역할 분리**

LangGraph의 `MemorySaver`는 앱이 살아 있는 동안의 단기 세션 기억을 담당한다. SQLite는 앱 재시작 이후에도 유지되어야 하는 장기 기록을 담당한다. 두 계층은 `graph_memory_hydrated` 플래그를 통해 역할을 나눴다. 앱 첫 실행 시 DB에서 복원한 메시지를 그래프에 1회 주입하고, 이후 turn부터는 MemorySaver가 자동으로 누적하는 방식이다.

**요약 메모리 활성화 상태**

테이블과 함수는 구현되어 있으나, 자동 요약 생성 트리거(메시지 N개 누적 시 LLM 요약 → `save_memory_summary` 호출)는 14주차 개인화 추천 단계로 미뤘다. 현재는 `memory_summary`가 시스템 프롬프트에 "저장된 장기기억 요약 없음"으로 주입된다.

### 2.2 대학생 정보 검색 기능 1차 구현

기존 인하공전 공지 검색과 완전히 분리된 별도 도구로 대학생 정보 검색 기능을 추가했다.

**추가 파일**

- `mcp_servers/student_info_server.py`: 도구 3개 구현
- `data/student_info_samples.json`: 샘플 데이터 6건 이상

**도구 목록**

| 도구 | 역할 |
|---|---|
| `load_student_info_data` | 샘플 JSON을 청킹·임베딩하여 ChromaDB에 저장 |
| `search_student_info` | 편입학/국가제도/공모전 정보 검색. 질문 키워드로 카테고리 자동 추정 |
| `get_student_info_stats` | 카테고리별 검색 가능 문서 수 확인 |

**카테고리 구성**

| 카테고리 | 내용 |
|---|---|
| `transfer` | 편입학/전공심화 |
| `policy` | 국가장학금/국가근로/학자금대출/청년정책 |
| `contest` | 공모전/대외활동/현장실습/인턴십 |

검색 결과에는 제목, 카테고리, 대상, 마감일, 출처, 요약, 다음 추천 행동이 포함된다.

**Agent 연결**

`agent/graph.py`의 `ALL_TOOLS`에 `STUDENT_INFO_TOOLS`를 추가했고, `agent/prompts.py`에 새 도구 사용 규칙을 포함하여 Agent가 질문 유형에 따라 기존 공지 검색과 대학생 정보 검색을 구분해서 호출하도록 했다.

### 2.3 버전 표기 통일

구현 결과를 반영하여 세 곳의 버전 표기를 `0.9.0`으로 통일했다.

| 위치 | 변경 전 | 변경 후 |
|---|---|---|
| `pyproject.toml` | 0.6.0 | **0.9.0** |
| `config/settings.py` | 0.7.0 | **0.9.0** |
| `agent/prompts.py` | v0.9.0 | (이미 일치) |

---

## 3. 테스트 결과

자동 테스트 42개 전체 통과, 회귀 없음.

```
42 passed, 1 warning in 9.39s
```

| 파일 | 테스트 수 | 결과 |
|---|---|---|
| `tests/test_task.py` | 13 | ✅ 통과 |
| `tests/test_calendar.py` | 12 | ✅ 통과 |
| `tests/test_memory.py` | 7 | ✅ 통과 |
| `tests/test_rag.py` | 8 | ✅ 통과 |
| `tests/test_student_info.py` | 2 | ✅ 통과 |

**`tests/test_memory.py` 검증 범위**

- 세션 생성 및 기존 세션 재조회
- 메시지 저장 순서 및 `limit` 파라미터 동작
- 잘못된 role / 빈 content 입력 거부
- 최신 요약 메모리 반환
- 대화 이력 삭제 후 세션 row 보존
- 메시지/요약 없는 세션 삭제 시 `False` 반환

**`tests/test_student_info.py` 검증 범위**

- JSON 로드 후 카테고리 3개(transfer/policy/contest) 포함 여부 확인
- ChromaDB 저장 후 편입학/국가제도/공모전 각 카테고리 검색 결과 반환 확인

**경고 1건**: Python 3.14와 chromadb의 `asyncio.iscoroutinefunction` 호환성 경고. 기능에 영향 없으며 Python 3.16 이전에 chromadb 업데이트로 해소될 예정.

---

## 4. 현재 프로젝트 구조 (10주차 완료 기준)

```
CampusAgent/
├─ app.py                        # 대화 복원/저장 흐름 포함
├─ agent/
│   ├─ graph.py                  # STUDENT_INFO_TOOLS 연결
│   ├─ prompts.py                # v0.9.0, 새 도구 사용 규칙 포함
│   └─ state.py
├─ database/
│   └─ db.py                     # 장기기억 테이블 3개 + CRUD 함수 6개
├─ mcp_servers/
│   ├─ task_server.py
│   ├─ calendar_server.py
│   ├─ rag_server.py             # 기존 학과/학교 공지 검색 (유지)
│   └─ student_info_server.py    # 신규: 편입학/국가제도/공모전 검색
├─ data/
│   ├─ sample_notices.json
│   ├─ crawled_notices_cse.json
│   └─ student_info_samples.json # 신규
├─ rag/
│   ├─ crawler.py
│   ├─ loader.py
│   ├─ chunker.py
│   ├─ embedder.py
│   └─ retriever.py
└─ tests/
    ├─ test_task.py
    ├─ test_calendar.py
    ├─ test_memory.py            # 신규: 장기기억 7개 테스트
    ├─ test_rag.py
    └─ test_student_info.py      # 신규: 대학생 정보 2개 테스트
```

---

## 5. 한계 및 미결 사항

| 항목 | 내용 | 예정 시기 |
|---|---|---|
| 요약 메모리 자동 생성 | 테이블/함수는 완성, 트리거 미구현 → 항상 "요약 없음" 상태 | 14주차 |
| ChromaDB 컬렉션 분리 | 공지사항과 대학생 정보가 같은 컬렉션 공유 중 | 11주차 검토 |
| `tests/test_agent.py` | LangGraph tool routing, API 키 fallback 테스트 없음 | 11주차 |
| 대학생 정보 실시간 크롤러 | 현재 샘플 데이터 기반 → 실시간 수집은 11~13주차에 단계적 확장 | 11~13주차 |

---

## 6. 다음 주 (11주차) 계획

11주차는 편입학/전공심화 영역을 집중적으로 고도화하는 주차이다.

- 우리 학교(인하공업전문대학) 전공심화 과정 정보 수집 구조 추가
- 타 학교 편입학 모집요강 정보 수집 대상 선정 및 구조화
- 학교명, 모집 단위, 지원 자격, 제출 서류, 전형 일정을 포함한 검색 응답 구현
- 편입학 관련 마감일을 캘린더/과제 등록 후보로 추출하는 흐름 설계
- `tests/test_agent.py` 기본 케이스 추가

---

## 7. 참고

- 전체 로드맵: `md_file/plan.md`
- 10주차 상세 계획 및 체크리스트: `md_file/week_10_plan.md`
- 핵심 파일 위치: `database/db.py`, `mcp_servers/student_info_server.py`, `agent/graph.py`, `agent/prompts.py`
