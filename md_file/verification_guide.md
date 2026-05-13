# CampusAgent — 완성 부분 검증 가이드

## Context

이번 세션에서 변경된 핵심 사항.

- `.env`에 3개 API 키 설정 완료 (`GOOGLE_API_KEY`, `YOUTH_CENTER_API_KEY`, `WORKNET_API_KEY`)
- `rag/external_crawler.py`의 `fetch_youth_policy()` 엔드포인트/파라미터 수정 (`/go/ythip/getPlcy`, `apiKeyNm` 사용)
- `rag/external_crawler.py`의 `fetch_worknet_jobs()` 엔드포인트/파라미터 수정 (`callOpenApiSvcInfo210L21.do`, XML 파싱)

이 변경이 끝-단(end-to-end)으로 동작하는지 4단계로 검증합니다.

---

## Step 1. 환경 점검 (30초)

```powershell
cd C:\Users\kimka\OneDrive\Documents\GitHub\CampusAgent
venv\Scripts\Activate.ps1

python -c "from config.settings import GOOGLE_API_KEY, YOUTH_CENTER_API_KEY, WORKNET_API_KEY, get_llm_provider; print('Gemini:', bool(GOOGLE_API_KEY), '| Youth:', bool(YOUTH_CENTER_API_KEY), '| Worknet:', bool(WORKNET_API_KEY), '| Provider:', get_llm_provider())"
```

**기대 출력**: `Gemini: True | Youth: True | Worknet: True | Provider: gemini`

---

## Step 2. 외부 API 함수 단위 테스트 (1분)

### 2-A. 온통청년 API

```powershell
python -c "import sys, io; sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8'); from config.settings import YOUTH_CENTER_API_KEY; from rag.external_crawler import fetch_youth_policy; r = fetch_youth_policy('장학', YOUTH_CENTER_API_KEY, display=3); print(f'수신: {len(r)}건'); [print(' -', x['title']) for x in r]"
```

**기대 출력**: `수신: 3건` + 장학금 정책 제목 3개

### 2-B. 워크넷 공채속보 API

```powershell
python -c "import sys, io; sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8'); from config.settings import WORKNET_API_KEY; from rag.external_crawler import fetch_worknet_jobs; r = fetch_worknet_jobs('', WORKNET_API_KEY, display=3); print(f'수신: {len(r)}건'); [print(f'  [{x[\"date\"]}] {x[\"title\"]}') for x in r]"
```

**기대 출력**: `수신: 3건` + 신입/인턴 채용공고 3개 (마감일 포함)

### 2-C. Gemini LLM

```powershell
python -c "from google import genai; from config.settings import GOOGLE_API_KEY; c = genai.Client(api_key=GOOGLE_API_KEY); print(c.models.generate_content(model='gemini-2.5-flash', contents='hi').text)"
```

---

## Step 3. 통합 테스트 스위트 실행 (2분)

```powershell
pytest tests/test_student_info.py -v
```

또는 전체 회귀.

```powershell
pytest tests/ -v
```

---

## Step 4. Streamlit 챗봇으로 end-to-end 검증 (3-5분)

### 4-A. 앱 실행

```powershell
streamlit run app.py
```

`http://localhost:8501` 자동 열림.

### 4-B. 사이드바 점검

- "✅ Gemini 활성화" 표시 확인
- 공지 데이터 메트릭 확인

### 4-C. 챗봇 탭 — 검증 질의 3종

| # | 질의 | 호출되어야 할 도구 | 검증 포인트 |
|---|---|---|---|
| 1 | `장학금 정책 알려줘` | `search_scholarship_policy` (온통청년 API) | 응답에 실제 장학 정책명이 출처와 함께 표시 |
| 2 | `최근 신입 채용공고 보여줘` | `search_job_intern` (워크넷 API) | 응답에 기업명·마감일이 포함된 채용공고 표시 |
| 3 | `소프트웨어 공모전 추천해줘` | `search_contest_external` (K-스타트업 크롤링) | 회귀 확인 |

각 응답에 "온통청년" 또는 "워크넷 공채속보" 출처 라벨이 보이면 변경이 에이전트까지 잘 전달된 것.

---

## 트러블슈팅

| 증상 | 원인 / 조치 |
|---|---|
| Step 1에서 `False` 반환 | `.env`가 프로젝트 루트에 있는지 확인 |
| Step 2-A 결과 0건 | 온통청년 서버 응답을 직접 확인 |
| Step 2-B 결과 0건 | work24 서버 XML 응답 직접 확인 |
| Step 4 챗봇이 도구 미호출 | 질의를 더 구체적으로 |

---

## 핵심 파일

- `rag/external_crawler.py:106-176` — `fetch_youth_policy()` (수정됨)
- `rag/external_crawler.py:180-272` — `fetch_worknet_jobs()` (수정됨)
- `mcp_servers/student_info_server.py:529-595` — MCP 도구
- `agent/graph.py:23-26` — `STUDENT_INFO_TOOLS` 바인딩
- `app.py` — Streamlit UI
- `tests/test_student_info.py` — 통합 테스트
