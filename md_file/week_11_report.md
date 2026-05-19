# CampusAgent 11주차 구현 결과 보고서

작성일: 2026-05-19.

## 1. 구현 요약

11주차 목표였던 과제 자동 분해와 서브태스크 트리 기능을 구현했다.

- `assignment_subtasks` 테이블을 추가해 기존 `assignments` 데이터를 보존하면서 부모-자식 과제 구조를 저장한다.
- 큰 과제, 프로젝트, 발표, 보고서, 코딩 과제, 시험 준비 과제를 규칙 기반으로 5~7개 서브태스크로 분해한다.
- 서브태스크 완료 상태를 기준으로 부모 과제 진행률과 상태를 자동 계산한다.
- Streamlit 과제 대시보드에서 부모 과제별 진행률과 서브태스크 체크 UI를 제공한다.
- LangGraph에 새 Task 도구가 바인딩되도록 `TASK_TOOLS`와 프롬프트를 갱신했다.

## 2. 주요 변경 파일

- `database/models.py`: `SubtaskCreate`, `Subtask`, `AssignmentWithProgress` 모델을 추가했다.
- `database/db.py`: 서브태스크 테이블 생성, CRUD, 진행률 계산, 부모 상태 동기화, 부모 삭제 시 서브태스크 정리를 추가했다.
- `mcp_servers/task_server.py`: `add_task_with_subtasks`, `list_task_tree`, `update_subtask_status_tool`, `get_task_progress` 도구와 규칙 기반 분해 함수를 추가했다.
- `agent/prompts.py`: 큰 과제와 서브태스크 요청에서 새 도구를 우선 사용하도록 안내를 추가했다.
- `config/mcp_config.json`: Task 서버 도구 목록을 갱신했다.
- `app.py`: 과제 대시보드를 진행률 bar와 서브태스크 체크박스 중심으로 갱신했다.
- `tests/test_task.py`: 서브태스크 저장, 정렬, 진행률, 부모 상태 동기화, 삭제 정리, 자동 분해 계획 테스트를 추가했다.
- `tests/test_agent.py`: 새 도구 바인딩, 프롬프트 반영, LLM 미설정 fallback 테스트를 추가했다.

## 3. 검증 결과

다음 명령을 실행해 통과를 확인했다.

```powershell
.\venv\Scripts\python.exe -m py_compile app.py database\models.py database\db.py mcp_servers\task_server.py agent\prompts.py
.\venv\Scripts\python.exe -m pytest tests/test_task.py -q
.\venv\Scripts\python.exe -m pytest tests/test_agent.py -q
.\venv\Scripts\python.exe -m pytest tests -q
```

결과는 다음과 같다.

- `tests/test_task.py`: 23 passed.
- `tests/test_agent.py`: 3 passed.
- 전체 테스트: 61 passed.

## 4. 남은 확인 사항

- 실사용 시연은 실행 중인 Streamlit 화면에서 큰 과제 등록, 서브태스크 체크, 진행률 반영 순서로 확인하면 된다.
- 자동 분해는 11주차 범위에 맞춰 규칙 기반으로 구현했다. LLM 기반 분해 품질 고도화는 12주차 이후 Task specialist 작업으로 넘길 수 있다.
- ChromaDB 컬렉션 분리는 이번 주 핵심 범위가 아니므로 기존 구조를 유지했다.
