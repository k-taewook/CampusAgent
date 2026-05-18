# CampusAgent 11주차 상세 구현 계획

작성일: 2026-05-18  
대상 기간: 2026-05-13 ~ 2026-05-20  
현재 기준 주차: 11주차  
작성 기준 문서: `md_file/plan.md`, `md_file/week_10_plan.md`, `md_file/week_10_report.md`, 현재 코드 구조.

---

## 1. 11주차 목표 요약

11주차의 핵심 목표는 **과제 자동 분해와 서브태스크 트리 기능을 시연 가능한 수준으로 완성하는 것**이다.

`md_file/plan.md`의 11주차 공식 목표는 다음 다섯 가지다.

- 큰 과제를 여러 개의 서브태스크로 자동 분해.
- 부모-자식 과제 구조 저장.
- 진행률 자동 계산.
- UI에서 계층형 과제 구조 표시.
- 과제 관련 테스트 점검.

완료 기준은 다음과 같다.

- 큰 과제를 추가하면 5~7개의 서브태스크가 자동 생성된다.
- 서브태스크 완료 시 상위 과제 진행률이 자동 반영된다.
- Streamlit UI와 챗봇 도구에서 시연 가능한 형태로 정리된다.

10주차 보고서에는 11주차로 넘기는 항목도 남아 있다.

- `tests/test_agent.py` 작성.
- ChromaDB 컬렉션 분리 검토.
- `research.md` 경로 갱신.
- 편입학/전공심화 고도화.

따라서 11주차는 **과제 분해 기능을 우선 구현**하고, 10주차 미결 항목은 기능 개발을 방해하지 않는 선에서 보조 작업으로 정리한다.

---

## 2. 현재 프로젝트 상태 정리

현재 CampusAgent는 Streamlit UI, LangGraph Agent, SQLite, ChromaDB, RAG 크롤러가 결합된 로컬 AI 학생 비서다.

주요 계층은 다음과 같다.

| 영역 | 현재 상태 | 11주차 영향 |
|---|---|---|
| `app.py` | Streamlit 4탭 UI, 채팅, 과제 대시보드, 캘린더, 설정 탭 구현. | 과제 대시보드에 계층형 표시와 진행률 표시를 추가해야 한다. |
| `agent/graph.py` | `TASK_TOOLS`, `CALENDAR_TOOLS`, `RAG_TOOLS`, `STUDENT_INFO_TOOLS`를 LangGraph에 바인딩. | 새 과제 분해 도구를 `TASK_TOOLS`에 추가하면 Agent가 바로 사용할 수 있다. |
| `agent/prompts.py` | 과제, 일정, 공지, 대학생 정보 검색 도구 사용 규칙 포함. | 큰 과제 요청 시 자동 분해 도구를 쓰도록 프롬프트 규칙을 추가해야 한다. |
| `database/db.py` | `assignments`, `schedules`, `user_settings`, 장기기억 테이블 구현. | `assignments` 테이블을 확장하거나 별도 `assignment_subtasks` 테이블을 추가해야 한다. |
| `database/models.py` | 단일 과제 모델 `AssignmentCreate`, `Assignment` 중심. | 부모 과제와 서브태스크 모델 또는 확장 필드가 필요하다. |
| `mcp_servers/task_server.py` | 과제 추가, 조회, 상태 변경, 삭제, 마감 임박 조회 도구 5개. | 자동 분해, 서브태스크 조회, 서브태스크 상태 변경 도구를 추가해야 한다. |
| `tests/test_task.py` | 단일 과제 CRUD 테스트 13개. | 부모-자식 저장, 진행률 계산, cascade 처리 테스트를 추가해야 한다. |
| `tests/test_agent.py` | 비어 있음. | 최소한 도구 목록, fallback, context 반영 테스트를 추가한다. |
| `rag/`, `mcp_servers/student_info_server.py` | 공지/대학생 정보 검색과 외부 API 연동 구현. | 11주차의 주 작업은 아니지만 검색 결과 마감일을 과제로 등록하는 흐름과 연결될 수 있다. |

현재 과제 구조는 단일 테이블 기반이다.

```text
assignments
  id
  title
  course_name
  description
  due_date
  status
  priority
  created_at
```

이 구조만으로는 부모 과제와 서브태스크 관계, 서브태스크별 완료 여부, 상위 진행률을 안정적으로 표현하기 어렵다.

---

## 3. 구현 원칙

11주차 작업은 다음 원칙으로 진행한다.

1. 기존 과제 CRUD를 깨지 않는다.
2. 기존 `assignments` 데이터를 삭제하거나 초기화하지 않는다.
3. 서브태스크 기능은 DB 스키마, 도구, UI, 테스트를 함께 맞춘다.
4. 자동 분해는 처음부터 복잡한 LLM 에이전트 체인으로 만들지 않고, 안정적인 규칙 기반 분해를 먼저 구현한다.
5. LLM이 사용 가능하면 분해 품질을 높일 수 있도록 확장 여지만 둔다.
6. 시연에서는 "큰 과제 등록 → 서브태스크 자동 생성 → 일부 완료 → 진행률 반영" 흐름을 명확히 보여준다.

자동 분해 방식은 다음처럼 단계화한다.

- 1차 구현: 과제 제목, 설명, 마감일을 기준으로 규칙 기반 5~7개 서브태스크 생성.
- 2차 보강: 과제 유형 키워드에 따라 보고서형, 발표형, 코딩형, 시험준비형 템플릿을 다르게 적용.
- 확장 후보: LLM이 사용 가능한 환경에서는 서브태스크 제목과 설명을 더 자연스럽게 생성.

11주차 완료 기준은 규칙 기반만으로도 만족할 수 있어야 한다.

---

## 4. 데이터베이스 설계 계획

### 4.1 권장 스키마

기존 `assignments` 테이블을 큰 폭으로 바꾸기보다, 별도 테이블을 추가하는 방식이 가장 안전하다.

새 테이블 후보는 `assignment_subtasks`다.

```sql
CREATE TABLE IF NOT EXISTS assignment_subtasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    due_date TEXT,
    status TEXT DEFAULT 'pending',
    sort_order INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (assignment_id) REFERENCES assignments(id)
);
```

이 설계를 선택하는 이유는 다음과 같다.

- 기존 `assignments` row를 그대로 부모 과제로 유지할 수 있다.
- 기존 `add_task`, `list_tasks`, `update_task_status`, `delete_task`의 동작을 크게 바꾸지 않아도 된다.
- 기존 테스트와 DB 데이터를 보존하기 쉽다.
- 서브태스크만 별도로 삭제, 조회, 진행률 계산하기 쉽다.

### 4.2 진행률 계산 방식

상위 과제 진행률은 DB에 저장하지 않고 조회 시 계산하는 방식을 우선한다.

```text
progress = 완료된 서브태스크 수 / 전체 서브태스크 수 * 100
```

상태 반영 규칙은 다음과 같다.

| 조건 | 상위 과제 상태 |
|---|---|
| 서브태스크가 없고 기존 상태가 있음 | 기존 상태 유지 |
| 서브태스크 완료율 0% | `pending` |
| 완료율 1~99% | `in_progress` |
| 완료율 100% | `done` |

서브태스크 상태 변경 시 상위 과제 상태를 자동 갱신한다.

### 4.3 삭제 정책

부모 과제를 삭제하면 연결된 서브태스크도 함께 삭제해야 한다.

SQLite에서 `ON DELETE CASCADE`를 쓰려면 foreign key pragma 처리를 신경 써야 하므로, 1차 구현에서는 `delete_assignment()` 내부에서 다음 순서로 명시 삭제하는 것이 안전하다.

1. `assignment_subtasks`에서 `assignment_id`에 해당하는 row 삭제.
2. `assignments`에서 부모 과제 삭제.

---

## 5. 모델 및 DB 함수 계획

### 5.1 `database/models.py`

추가할 모델은 다음과 같다.

| 모델 | 역할 |
|---|---|
| `SubtaskCreate` | 서브태스크 생성 요청 검증. |
| `Subtask` | DB에서 조회한 서브태스크 표현. |
| `AssignmentWithProgress` | 부모 과제, 서브태스크 목록, 진행률을 함께 표현하는 확장 모델. |

필드 후보는 다음과 같다.

```python
class SubtaskCreate(BaseModel):
    assignment_id: int
    title: str
    description: Optional[str] = None
    due_date: Optional[str] = None
    status: str = "pending"
    sort_order: int = 0
```

날짜 검증은 기존 `AssignmentCreate.due_date`와 맞춰 `YYYY-MM-DD` 또는 `YYYY-MM-DD HH:MM`을 허용한다.

### 5.2 `database/db.py`

추가할 함수는 다음과 같다.

| 함수 | 역할 |
|---|---|
| `add_subtask(data: SubtaskCreate) -> Subtask` | 서브태스크 1개 추가. |
| `add_subtasks(assignment_id: int, subtasks: list[SubtaskCreate]) -> list[Subtask]` | 자동 분해 결과 일괄 저장. |
| `get_subtasks(assignment_id: int) -> list[Subtask]` | 특정 과제의 서브태스크 목록 조회. |
| `get_assignment_progress(assignment_id: int) -> dict` | 전체 수, 완료 수, 진행률 계산. |
| `update_subtask_status(subtask_id: int, new_status: str) -> Optional[Subtask]` | 서브태스크 상태 변경. |
| `delete_subtask(subtask_id: int) -> bool` | 서브태스크 삭제. |
| `sync_assignment_status_from_subtasks(assignment_id: int) -> Optional[Assignment]` | 서브태스크 진행률 기준으로 부모 상태 갱신. |
| `get_assignments_with_progress() -> list[dict]` | UI 표시용 통합 조회. |

기존 함수 중 수정이 필요한 부분은 다음과 같다.

- `init_sqlite_db()`: `assignment_subtasks` 테이블 생성 SQL 추가.
- `delete_assignment()`: 연결된 서브태스크 삭제 후 부모 과제 삭제.
- `_row_to_assignment()`: 기존 동작 유지.

---

## 6. 자동 분해 로직 계획

### 6.1 기본 함수 위치

자동 분해 로직은 DB 함수가 아니라 `mcp_servers/task_server.py` 또는 별도 순수 유틸 모듈로 분리한다.

권장 위치는 `mcp_servers/task_server.py` 내부의 작은 헬퍼 함수다.

```python
def _generate_subtask_plan(title: str, description: str, due_date: str) -> list[dict]:
    ...
```

이유는 다음과 같다.

- 11주차 범위에서는 별도 추상화가 과하다.
- 도구 구현과 가까워 자연어 과제 등록 흐름을 이해하기 쉽다.
- 테스트에서는 헬퍼를 직접 검증할 수 있다.

나중에 분해 규칙이 커지면 `agent/task_decomposer.py` 같은 모듈로 분리한다.

### 6.2 과제 유형별 템플릿

자동 분해는 과제 제목과 설명의 키워드로 유형을 추정한다.

| 유형 | 감지 키워드 | 생성 서브태스크 예시 |
|---|---|---|
| 보고서형 | 보고서, 레포트, 리포트, 조사 | 주제 확인, 자료 조사, 목차 작성, 초안 작성, 검토 및 제출. |
| 발표형 | 발표, PPT, 프레젠테이션 | 요구사항 확인, 자료 조사, 슬라이드 구성, 발표 대본 작성, 리허설. |
| 코딩형 | 프로젝트, 구현, 개발, 프로그래밍, 코드 | 요구사항 분석, 구조 설계, 핵심 기능 구현, 테스트 작성, 디버깅, 제출 정리. |
| 시험준비형 | 시험, 중간고사, 기말고사, 퀴즈 | 범위 확인, 요약 정리, 문제 풀이, 오답 정리, 최종 복습. |
| 일반형 | 위 키워드 없음 | 요구사항 정리, 자료 수집, 작업 계획, 본 작업, 검토, 제출. |

5~7개 생성 조건을 지키기 위해 기본은 6개로 생성한다.

### 6.3 마감일 배분

서브태스크 마감일은 부모 과제 마감일을 기준으로 역산한다.

예시 규칙은 다음과 같다.

| 순서 | 마감일 배분 |
|---|---|
| 1번 | 부모 마감 6일 전 |
| 2번 | 부모 마감 5일 전 |
| 3번 | 부모 마감 4일 전 |
| 4번 | 부모 마감 3일 전 |
| 5번 | 부모 마감 2일 전 |
| 6번 | 부모 마감 1일 전 또는 부모 마감일 |

부모 마감까지 남은 기간이 짧으면 같은 날짜에 여러 서브태스크를 배치한다.

주의할 점은 기존 `due_date`가 `YYYY-MM-DD HH:MM` 형식도 허용한다는 것이다. 날짜 계산은 우선 앞 10자리 `YYYY-MM-DD` 기준으로 수행하고, 시간은 부모 마감일에만 보존하는 방식이 단순하다.

---

## 7. Task 도구 확장 계획

### 7.1 새 도구 목록

`mcp_servers/task_server.py`에 다음 도구를 추가한다.

| 도구 | 역할 |
|---|---|
| `add_task_with_subtasks` | 큰 과제를 추가하고 5~7개 서브태스크 자동 생성. |
| `list_task_tree` | 부모 과제와 서브태스크를 계층형으로 조회. |
| `update_subtask_status_tool` | 서브태스크 상태 변경 후 부모 진행률 갱신. |
| `get_task_progress` | 특정 과제의 진행률과 남은 작업 조회. |

기존 도구 이름과 충돌하지 않게 `update_subtask_status_tool`처럼 함수명을 조정한다.

### 7.2 `add_task_with_subtasks` 응답 예시

```text
✅ 큰 과제를 서브태스크로 분해해 등록했습니다.

📌 부모 과제: [12] 자료구조 프로젝트
📊 진행률: 0% (0/6)

1. 요구사항 확인.
2. 자료구조 설계.
3. 핵심 기능 구현.
4. 예외 처리와 디버깅.
5. 테스트 케이스 작성.
6. 제출 파일 정리.

💡 다음 추천 행동
- 1번 서브태스크부터 진행 상태를 `in_progress`로 바꿀 수 있습니다.
```

### 7.3 기존 `add_task`와의 관계

기존 `add_task`는 그대로 유지한다.

사용 기준은 다음과 같다.

- 사용자가 단순히 "과제 추가해줘"라고 하면 `add_task`.
- 사용자가 "큰 과제", "프로젝트", "분해", "계획 세워줘", "단계별로 나눠줘"라고 말하면 `add_task_with_subtasks`.
- 사용자가 `add_task`로 이미 등록한 과제를 나중에 분해하고 싶다고 하면 별도 `decompose_existing_task` 도구를 추가할 수 있다.

11주차 최소 범위에서는 `decompose_existing_task`는 선택 작업으로 둔다.

### 7.4 도구 목록 반영

`TASK_TOOLS`에 새 도구를 추가한다.

```python
TASK_TOOLS = [
    add_task,
    add_task_with_subtasks,
    list_tasks,
    list_task_tree,
    update_task_status,
    update_subtask_status_tool,
    get_task_progress,
    delete_task,
    get_upcoming_deadlines,
]
```

`agent/graph.py`는 `TASK_TOOLS`를 가져오므로 별도 수정이 거의 필요 없다.

---

## 8. 프롬프트 수정 계획

`agent/prompts.py`의 과제 관리 도구 목록에 새 도구를 추가한다.

추가할 사용 규칙은 다음과 같다.

- "프로젝트", "큰 과제", "레포트 계획", "단계별로 나눠줘", "서브태스크", "분해해줘"가 포함되면 `add_task_with_subtasks`를 우선 사용한다.
- 서브태스크 완료 요청은 `update_subtask_status_tool`을 사용한다.
- 과제 진행률을 묻는 요청은 `get_task_progress` 또는 `list_task_tree`를 사용한다.
- 일반 과제 등록은 기존 `add_task`를 사용한다.

현재 시스템 프롬프트는 도구 실행 결과를 엄격한 템플릿으로 정리하라고 지시한다. 새 도구 응답도 같은 구조를 따르게 한다.

---

## 9. Streamlit UI 수정 계획

### 9.1 과제 대시보드

현재 `app.py`의 과제 대시보드는 `get_assignments()` 결과를 DataFrame으로 표시하고, 완료 체크 시 `update_assignment_status()`를 호출한다.

11주차에는 다음을 추가한다.

- 부모 과제 행에 진행률 표시.
- 서브태스크 수 표시.
- 서브태스크를 들여쓰기 또는 별도 확장 영역으로 표시.
- 서브태스크 완료 체크 시 `update_subtask_status()` 호출.
- 부모 과제 상태는 직접 체크보다 진행률 기준 자동 반영을 우선한다.

Streamlit에서 계층형 DataFrame 편집은 제한이 있으므로, 1차 구현은 다음 구성이 현실적이다.

```text
부모 과제 카드 또는 expander
  - 제목, 과목, 마감일, 우선순위, 진행률
  - progress bar
  - 서브태스크 체크박스 목록
```

기존 DataEditor는 일반 과제 목록 표시용으로 유지하거나, 전체 과제 요약 표로 축소한다.

### 9.2 캘린더 표시

서브태스크까지 캘린더에 모두 표시하면 화면이 복잡해질 수 있다. 11주차에는 부모 과제 마감만 기존처럼 표시하고, 서브태스크는 과제 대시보드에서 관리한다.

선택 작업으로 다음을 고려한다.

- 마감이 오늘 또는 내일인 서브태스크만 사이드바 긴급 알림에 표시.
- 캘린더 배지에는 부모 과제만 표시.

### 9.3 챗봇 후속 액션

검색 결과에서 "캘린더나 과제에 등록하기" 버튼을 누르면 현재는 일반 문장으로 다시 프롬프트를 넣는다. 11주차에는 이 흐름을 유지하되, 큰 마감 정보나 프로젝트성 작업이면 `add_task_with_subtasks`를 쓰도록 프롬프트를 보강한다.

---

## 10. 테스트 계획

### 10.1 `tests/test_task.py`

추가할 테스트는 다음과 같다.

| 테스트 | 검증 내용 |
|---|---|
| `test_add_subtask` | 부모 과제에 서브태스크 1개 추가. |
| `test_add_multiple_subtasks_ordered` | sort_order 기준 조회 순서 유지. |
| `test_progress_empty_subtasks` | 서브태스크가 없으면 진행률 계산이 안전하게 동작. |
| `test_progress_partial_done` | 일부 완료 시 진행률 1~99% 계산. |
| `test_progress_all_done_updates_parent` | 모두 완료 시 부모 상태 `done` 반영. |
| `test_delete_parent_removes_subtasks` | 부모 삭제 시 서브태스크 삭제. |
| `test_generate_subtask_plan_count` | 자동 분해 결과가 5~7개인지 확인. |
| `test_subtask_invalid_status_rejected` | 잘못된 상태 입력 거부. |

### 10.2 `tests/test_agent.py`

현재 비어 있으므로 최소 테스트를 작성한다.

추천 범위는 다음과 같다.

- `ALL_TOOLS`에 새 과제 분해 도구가 포함되는지 확인.
- LLM API 키가 없을 때 fallback 응답이 생성되는지 확인.
- `current_context`에 `memory_summary`가 들어가도 그래프 호출이 깨지지 않는지 확인.
- 새 도구 설명이 프롬프트에 포함되는지 확인.

LangGraph 전체 end-to-end 테스트는 API 키와 모델 응답에 의존하므로, 11주차에는 무리하게 실모델 호출을 자동 테스트에 넣지 않는다.

### 10.3 회귀 테스트

작업 후 실행할 기본 테스트는 다음과 같다.

```powershell
python -m pytest tests/test_task.py -q
python -m pytest tests/test_agent.py -q
python -m pytest tests -q
```

수동 검증은 다음으로 진행한다.

```powershell
streamlit run app.py
```

수동 검증 항목은 다음과 같다.

- "자료구조 프로젝트 과제 추가해줘. 마감일은 2026-05-20이고 단계별로 나눠줘." 입력.
- 5~7개 서브태스크가 생성되는지 확인.
- 과제 대시보드에서 서브태스크 체크 시 진행률이 올라가는지 확인.
- 모든 서브태스크 완료 시 부모 과제가 완료 상태가 되는지 확인.
- 기존 일반 과제 추가, 일정 추가, 공지 검색이 깨지지 않는지 확인.

---

## 11. 구현 순서

11주차 구현은 다음 순서로 진행한다.

1. `database/db.py`에 `assignment_subtasks` 테이블 생성 SQL 추가.
2. `database/models.py`에 `SubtaskCreate`, `Subtask` 모델 추가.
3. `database/db.py`에 서브태스크 CRUD와 진행률 계산 함수 추가.
4. `delete_assignment()`에 부모 과제 삭제 시 서브태스크 정리 로직 추가.
5. `mcp_servers/task_server.py`에 자동 분해 헬퍼와 새 도구 추가.
6. `TASK_TOOLS`에 새 도구를 등록.
7. `agent/prompts.py`에 서브태스크 도구 사용 규칙 추가.
8. `config/mcp_config.json`의 task 도구 목록 동기화.
9. `app.py` 과제 대시보드에 진행률과 서브태스크 체크 UI 추가.
10. `tests/test_task.py`에 서브태스크 단위 테스트 추가.
11. `tests/test_agent.py`에 기본 Agent 테스트 추가.
12. `python -m pytest tests/test_task.py -q` 실행.
13. `python -m pytest tests/test_agent.py -q` 실행.
14. `python -m pytest tests -q`로 전체 회귀 확인.
15. 앱 수동 실행으로 시연 흐름 확인.

---

## 12. 예상 변경 파일

| 파일 | 변경 내용 |
|---|---|
| `database/models.py` | 서브태스크 모델 추가. |
| `database/db.py` | 서브태스크 테이블, CRUD, 진행률 계산, 부모 상태 동기화 추가. |
| `mcp_servers/task_server.py` | 자동 분해 도구와 서브태스크 관리 도구 추가. |
| `agent/prompts.py` | 새 과제 분해 도구 사용 규칙 추가. |
| `config/mcp_config.json` | task 도구 목록 갱신. |
| `app.py` | 과제 대시보드에 계층형 과제 표시와 진행률 UI 추가. |
| `tests/test_task.py` | 서브태스크 저장, 진행률, 삭제, 자동 분해 테스트 추가. |
| `tests/test_agent.py` | 기본 Agent 구성 테스트 추가. |
| `md_file/week_11_report.md` | 구현 후 작성할 11주차 실습일지 후보. |

`campus_tasks.db`, `chroma_db_storage/`, `.env`는 검증 중 삭제하거나 초기화하지 않는다.

---

## 13. 10주차 미결 항목 처리 계획

### 13.1 `tests/test_agent.py`

11주차에 최소 자동 테스트를 추가한다. 이 항목은 과제 분해 도구가 Agent에 실제 바인딩되는지 확인하는 데도 필요하므로 우선순위가 높다.

### 13.2 ChromaDB 컬렉션 분리

현재 공지사항과 대학생 정보가 `university_notices` 컬렉션을 공유한다. 11주차의 핵심은 과제 분해이므로, 컬렉션 분리 구현은 하지 않고 검토 결과만 정리한다.

권장 결론은 다음과 같다.

- 11주차에는 기존 구조 유지.
- 12주차 Multi-Agent 구조 정리 시 Notice specialist와 Info specialist의 저장소 분리까지 함께 검토.
- 단기적으로는 metadata `category`와 `source`로 구분.

### 13.3 `research.md` 경로 갱신

`md_file/research.md`에는 과거 경로인 `C:\workspace\CampusAgent`가 남아 있다. 11주차 문서 정리 작업 때 현재 경로인 `C:\Users\kimka\OneDrive\Documents\GitHub\CampusAgent`로 갱신한다.

단, 코드 구현과 직접 관련은 낮으므로 과제 분해 기능이 안정화된 뒤 진행한다.

### 13.4 편입학/전공심화 고도화

10주차 보고서에는 편입학 고도화가 다음 주 계획으로 적혀 있다. 하지만 공식 `plan.md`의 11주차 목표는 과제 자동 분해다.

따라서 11주차에서는 다음 수준으로 제한한다.

- 편입학 검색 결과에서 마감일 후보를 과제 또는 캘린더 등록 후보로 제안.
- 실제 편입학 크롤러 추가 고도화는 12주차 이후 또는 발표 보강 작업으로 이동.

---

## 14. 위험 요소와 대응

| 위험 | 원인 | 대응 |
|---|---|---|
| 기존 과제 테스트 회귀 | `assignments` 관련 함수 수정. | 기존 함수 인터페이스 유지, 서브태스크는 별도 테이블로 분리. |
| Streamlit 대시보드 복잡도 증가 | DataEditor로 계층형 편집이 어려움. | expander + checkbox + progress bar 방식으로 단순화. |
| 자동 분해 품질 부족 | 규칙 기반 템플릿의 한계. | 5~7개 생성과 시연 가능성을 우선하고, LLM 고도화는 선택 작업으로 둔다. |
| 부모 상태와 서브태스크 상태 불일치 | 수동 상태 변경과 자동 진행률 계산 충돌. | 서브태스크가 있는 과제는 진행률 기준으로 부모 상태를 동기화한다. |
| DB 마이그레이션 문제 | 기존 `campus_tasks.db`에 새 테이블 추가 필요. | `CREATE TABLE IF NOT EXISTS`만 사용하고 기존 데이터는 건드리지 않는다. |
| 날짜 계산 오류 | `YYYY-MM-DD HH:MM`과 `YYYY-MM-DD` 혼재. | 계산은 날짜 부분 기준으로 수행하고 원본 마감일은 부모 과제에 유지한다. |
| LLM API 의존 테스트 불안정 | 외부 모델 응답 비결정성. | 자동 테스트는 도구 목록과 순수 함수 중심으로 작성한다. |

---

## 15. 시연 시나리오

11주차 시연은 다음 순서로 준비한다.

1. 챗봇에 큰 과제 등록 요청.

```text
자료구조 프로젝트 과제 추가해줘. 마감일은 2026-05-20이고 단계별로 나눠줘.
```

2. Agent가 `add_task_with_subtasks`를 호출.
3. 부모 과제와 5~7개 서브태스크 생성 결과 표시.
4. 과제 대시보드에서 부모 과제 진행률 0% 확인.
5. 서브태스크 2개 완료 체크.
6. 부모 과제 진행률이 약 33%로 반영되는지 확인.
7. 모든 서브태스크 완료.
8. 부모 과제 상태가 `done`으로 바뀌는지 확인.
9. 기존 "이번 주 마감인 과제 알려줘" 요청이 정상 동작하는지 확인.

---

## 16. 완료 기준 체크리스트

### 핵심 기능

- [ ] `assignment_subtasks` 테이블이 자동 생성된다.
- [ ] 큰 과제 등록 시 5~7개 서브태스크가 자동 생성된다.
- [ ] 부모 과제와 서브태스크 관계가 SQLite에 저장된다.
- [ ] 서브태스크 목록을 과제별로 조회할 수 있다.
- [ ] 서브태스크 상태를 `pending`, `in_progress`, `done`으로 변경할 수 있다.
- [ ] 서브태스크 완료율로 부모 과제 진행률이 계산된다.
- [ ] 모든 서브태스크가 완료되면 부모 과제가 `done` 상태가 된다.
- [ ] 부모 과제 삭제 시 연결된 서브태스크도 삭제된다.

### Agent와 UI

- [ ] 새 도구가 `TASK_TOOLS`와 LangGraph에 바인딩된다.
- [ ] 시스템 프롬프트가 큰 과제 분해 요청을 새 도구로 유도한다.
- [ ] 과제 대시보드에서 부모 과제 진행률을 볼 수 있다.
- [ ] UI에서 서브태스크 완료 처리가 가능하다.
- [ ] 기존 일반 과제 추가와 일정 추가 흐름이 유지된다.

### 테스트와 문서

- [ ] `tests/test_task.py`에 서브태스크 테스트가 추가된다.
- [ ] `tests/test_agent.py`가 빈 파일이 아니게 된다.
- [ ] `python -m pytest tests/test_task.py -q`가 통과한다.
- [ ] `python -m pytest tests/test_agent.py -q`가 통과한다.
- [ ] `python -m pytest tests -q` 전체 회귀가 통과한다.
- [ ] 구현 후 `md_file/week_11_report.md`에 결과와 검증 내용을 정리한다.

---

## 17. 11주차 산출물

11주차가 끝났을 때 남아야 하는 산출물은 다음과 같다.

- 서브태스크 저장 테이블.
- 부모 과제와 서브태스크 CRUD 함수.
- 과제 자동 분해 도구.
- 과제 진행률 자동 계산 기능.
- Streamlit 과제 대시보드의 계층형 표시.
- 서브태스크 관련 단위 테스트.
- 최소 Agent 구성 테스트.
- 11주차 구현 결과 보고서.

---

## 18. 12주차 연결 계획

11주차 결과는 12주차 Multi-Agent 구조의 Task specialist로 이어진다.

12주차에서 연결할 방향은 다음과 같다.

- Task specialist가 과제 생성, 분해, 진행률 관리를 전담한다.
- Calendar specialist가 서브태스크 마감일을 일정 후보로 등록한다.
- Notice/Info specialist가 검색 결과의 마감일을 Task specialist로 넘긴다.
- Supervisor가 "공지 검색 후 과제로 등록" 같은 복합 요청을 specialist에게 분배한다.

즉, 11주차의 서브태스크 트리는 12주차 Multi-Agent 구조에서 Task specialist의 핵심 기능이 된다.
