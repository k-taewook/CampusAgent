# CampusAgent 워크스페이스 지침

## 적용 범위
- 이 지침은 저장소 전체에 적용됩니다.
- 변경은 최소 범위로 정확하게 수행하고, 요청이 없는 한 큰 리팩터링은 피하세요.

## 빌드 및 테스트
- Python 요구 버전: 3.10+
- 환경 설정:
  - `python -m venv venv`
  - `venv\Scripts\activate` (Windows PowerShell)
  - `pip install -e .`
  - `pip install pytest`
- 앱 실행:
  - `streamlit run app.py`
- 테스트 실행:
  - `python -m pytest tests/ -v`
  - 선택 실행(개별 테스트):
    - `python -m pytest tests/test_task.py -v`
    - `python -m pytest tests/test_calendar.py -v`
    - `python -m pytest tests/test_rag.py -v`

## 아키텍처
- UI 진입점: `app.py` (Streamlit 채팅 + 사이드바 상태).
- 에이전트 오케스트레이션: `agent/graph.py` (LangGraph 상태 머신).
  - 흐름: `tool_calls`가 없어질 때까지 `agent -> tools -> agent` 순환.
  - 도구 실행은 task/calendar/RAG 서버 도구를 하나의 통합 목록으로 묶어 사용.
- 도구 제공 계층: `mcp_servers/`
  - `task_server.py`, `calendar_server.py`, `rag_server.py`
- 데이터 계층:
  - SQLite CRUD: `database/db.py`
  - Pydantic 모델/검증: `database/models.py`
  - 벡터 검색(ChromaDB 영속 저장): `rag/retriever.py`
- 런타임 설정 및 제공자 선택: `config/settings.py`

## 프로젝트 규칙
- 호출 가능한 모든 도구는 LangChain `@tool`로 노출하고, 명확한 docstring을 작성하세요.
- 사용자 노출 문구는 한국어 우선입니다. 프롬프트/메시지 수정 시 기존 한국어 톤을 유지하세요.
- 저장 계층으로 들어가는 날짜/시간 입력은 엄격하게 다룹니다(예: `YYYY-MM-DD`, `YYYY-MM-DD HH:MM`). 가능하면 초기에 검증하고, 수정 가능한 오류 메시지를 반환하세요.
- 도구 경계에서는 사용자 친화적으로 예외를 처리하세요. 원시 traceback 대신 이해 가능한 오류 메시지를 반환하세요.
- DB 테스트를 추가할 때는 기존 테스트 격리 패턴을 따르세요:
  - fixture에서 임시 DB 경로를 사용하고, `config.settings.SQLITE_DB_PATH`와 `database.db.SQLITE_DB_PATH`를 함께 동기화하세요.

## 자주 발생하는 함정
- API 키가 없으면 앱은 실행되어도 활성 LLM 제공자가 `none`이 될 수 있습니다. 심층 디버깅 전에 `.env`와 `config/settings.py`의 provider 감지 로직을 먼저 확인하세요.
- 상대 날짜 표현(예: "내일")은 엄격한 validator가 실행되기 전에 구체 날짜 문자열로 변환되어야 합니다.
- Streamlit 세션 상태와 LangGraph 체크포인트 메모리를 동일한 상태로 가정해 섞어 쓰지 마세요.

## 링크 우선, 중복 금지
- 프로젝트 전체 개요와 사용 예시는 `README.md`를 참고하세요.
- `README.md`의 큰 아키텍처/기능 표를 코드 주석이나 지침 파일에 그대로 복제하지 마세요.
