// CampusAgent 최종보고서 DOCX 생성
"use strict";
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  ImageRun, AlignmentType, SectionType, BorderStyle, WidthType,
  ShadingType, VerticalAlign, Column, HeadingLevel, PageNumber,
  Header, Footer, UnderlineType
} = require("docx");
const fs = require("fs");
const path = require("path");

// ── 파일 경로 ──────────────────────────────────────────────────────────
const ASSETS = __dirname;
const OUT = path.join(ASSETS, "CampusAgent_최종보고서.docx");

// 스크린샷 파일 (없으면 placeholder 사용)
const SHOTS = {
  fig2: path.join(ASSETS, "fig2_chatbot.png"),
  fig3: path.join(ASSETS, "fig3_dashboard.png"),
  fig4: path.join(ASSETS, "fig4_calendar.png"),
  fig5: path.join(ASSETS, "fig5_notice.png"),
  fig6: path.join(ASSETS, "fig6_settings.png"),
};

// ── 치수 (A4, DXA) ─────────────────────────────────────────────────────
const PW  = 11906;   // A4 width
const PH  = 16838;   // A4 height
const ML  = 1134;    // left margin  (~2 cm)
const MR  = 1134;    // right margin
const MT  = 1134;    // top margin
const MB  = 1134;    // bottom margin
const CW  = PW - ML - MR;          // content width = 9638
const GAP = 567;                   // column gap (~1 cm)
const COL = Math.floor((CW - GAP) / 2);  // one column = 4535

// ── 유틸 ──────────────────────────────────────────────────────────────
const KN  = "Malgun Gothic";   // 한글 본문
const EN  = "Times New Roman"; // 영문
const HF  = 8;   // font size half-points; 1pt = 2 half-points
// font size shortcuts (in half-points)
const pt  = n => n * 2;

const border0 = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const borders0 = { top: border0, bottom: border0, left: border0, right: border0 };
const borderGray = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const bordersGray = { top: borderGray, bottom: borderGray, left: borderGray, right: borderGray };

// 단락 생성 단축
function P(runs, opts={}) {
  return new Paragraph({ children: Array.isArray(runs) ? runs : [runs], ...opts });
}
function TR(text, fontSize, bold=false, font=KN, color="000000", align=AlignmentType.LEFT, space={}) {
  return new TextRun({ text, size: pt(fontSize), bold, font, color, ...space });
}
function KR(text, fontSize=10, bold=false, opts={}) {
  return new TextRun({ text, size: pt(fontSize), font: KN, bold, ...opts });
}
function ER(text, fontSize=10, bold=false, opts={}) {
  return new TextRun({ text, size: pt(fontSize), font: EN, bold, ...opts });
}

// ── 이미지 로더 ────────────────────────────────────────────────────────
function loadImg(fpath, wDxa, hDxa) {
  if (!fs.existsSync(fpath)) return null;
  const data = fs.readFileSync(fpath);
  const ext  = path.extname(fpath).slice(1).toLowerCase();
  return new ImageRun({
    type: ext === "jpg" ? "jpeg" : ext,
    data,
    transformation: { width: Math.round(wDxa * 96 / 1440), height: Math.round(hDxa * 96 / 1440) },
    altText: { title: path.basename(fpath), description: "", name: path.basename(fpath) }
  });
}

// 이미지 단락 + 캡션 (2-column section 안에서 한 컬럼 너비 기준)
function figPara(imgPath, wDxa, hDxa, capKr, capEn) {
  const img = loadImg(imgPath, wDxa, hDxa);
  const paras = [];
  if (img) {
    paras.push(P([img], { alignment: AlignmentType.CENTER, spacing: { before: pt(3), after: 0 } }));
  } else {
    // placeholder
    paras.push(P([KR(`[ ${capKr} - 스크린샷 삽입 위치 ]`, 9, false, { color: "888888" })],
      { alignment: AlignmentType.CENTER }));
  }
  paras.push(P([KR(capKr, 9, true), KR(" / ", 9), ER(capEn, 9, true)],
    { alignment: AlignmentType.CENTER, spacing: { before: 0, after: pt(4) } }));
  return paras;
}

// ── 구분선 ──────────────────────────────────────────────────────────────
function hline(color="000000", size=6) {
  return P([], {
    border: { bottom: { style: BorderStyle.SINGLE, size, color } },
    spacing: { before: 0, after: pt(2) }
  });
}

// ── 테이블 ──────────────────────────────────────────────────────────────
function makeTable(headers, rows, colWidths) {
  const totalW = colWidths.reduce((a,b) => a+b, 0);
  const hRow = new TableRow({
    children: headers.map((h, i) => new TableCell({
      borders: bordersGray,
      width: { size: colWidths[i], type: WidthType.DXA },
      shading: { fill: "1565C0", type: ShadingType.CLEAR },
      margins: { top: 60, bottom: 60, left: 100, right: 100 },
      children: [P([KR(h, 8.5, true, { color: "FFFFFF" })], { alignment: AlignmentType.CENTER })]
    }))
  });
  const dataRows = rows.map(row =>
    new TableRow({
      children: row.map((cell, i) => new TableCell({
        borders: bordersGray,
        width: { size: colWidths[i], type: WidthType.DXA },
        margins: { top: 50, bottom: 50, left: 100, right: 100 },
        children: [P([KR(cell, 8.5)], { alignment: AlignmentType.LEFT })]
      }))
    })
  );
  return new Table({ width: { size: totalW, type: WidthType.DXA }, columnWidths: colWidths,
                     rows: [hRow, ...dataRows] });
}

// ─────────────────────────────────────────────────────────────────────────
// 섹션 1: 단컬럼 — 영문 헤더 (제목, 저자, 초록, 키워드, 한국어 소제목)
// ─────────────────────────────────────────────────────────────────────────
const sec1children = [

  // ── 논문지 제목줄 (이탤릭, 작은 글씨)
  P([ER("Proceedings of Capstone Design in System Engineering, Inha Technical College, 2026", 8, false, { italics: true })],
    { alignment: AlignmentType.CENTER, spacing: { before: 0, after: pt(3) } }),
  hline("000000", 4),

  // ── 논문 영문 제목
  P([ER("CampusAgent: A Local AI Student Assistant Based on", 15, true),
     ER("\nLangGraph for University Students", 15, true)],
    { alignment: AlignmentType.CENTER, spacing: { before: pt(6), after: pt(4) } }),

  // ── 저자
  P([ER("Tae-Wook Kim", 11, true), ER("¹", 9)],
    { alignment: AlignmentType.CENTER, spacing: { before: 0, after: 0 } }),
  P([ER("¹", 9), ER("Department of Computer Systems & Engineering, Inha Technical College", 9, false, { italics: true })],
    { alignment: AlignmentType.CENTER, spacing: { before: 0, after: pt(5) } }),

  hline("000000", 4),

  // ── A B S T R A C T 레이블
  P([ER("A B S T R A C T", 10, true)],
    { alignment: AlignmentType.CENTER, spacing: { before: pt(4), after: pt(2) } }),

  // ── 영문 초록
  P([ER(
    "University students must simultaneously manage assignments, schedules, school announcements, " +
    "scholarship information, and internship opportunities scattered across multiple platforms. " +
    "This paper presents CampusAgent, a local AI student assistant that integrates all these " +
    "functions into a single conversational interface. CampusAgent employs a LangGraph-based " +
    "agent that routes natural language requests to 29 LangChain tools organized into four groups: " +
    "task management (9 tools), calendar management (6 tools), notice retrieval via RAG (5 tools), " +
    "and student information search (9 tools). Structured data are persisted in SQLite while " +
    "unstructured texts are indexed in ChromaDB for semantic retrieval. A key feature is automatic " +
    "task decomposition, where large assignments are broken into 5–7 subtasks using rule-based type " +
    "detection, with completion rates propagated back to the parent task automatically. Real-time " +
    "web crawling supplements RAG retrieval with up-to-date notices from the university website. " +
    "Experimental validation with 67 automated test cases confirms correct operation across all " +
    "subsystems.", 9.5)],
    { alignment: AlignmentType.JUSTIFIED, spacing: { before: 0, after: pt(3) } }),

  P([ER("© 2026 Inha Technical College  All rights reserved", 9, false, { italics: true })],
    { alignment: AlignmentType.CENTER, spacing: { before: 0, after: pt(3) } }),

  hline("000000", 4),

  // ── 키워드
  P([ER("K E Y W O R D S", 9, true), ER("   LangGraph, RAG, Tool Calling, SQLite, ChromaDB, Student Assistant", 9)],
    { alignment: AlignmentType.LEFT, spacing: { before: pt(2), after: pt(3) } }),

  hline("000000", 6),
];

// ─────────────────────────────────────────────────────────────────────────
// 섹션 2: 2-컬럼 — 한국어 본문
// ─────────────────────────────────────────────────────────────────────────

// 본문 단락 헬퍼
function BP(text, space={before:0, after:pt(2)}) {
  return P([KR(text, 9.5)], { alignment: AlignmentType.JUSTIFIED, spacing: space });
}
function SH(num, text) {   // 소제목
  return P([KR(`${num} ${text}`, 10, true)], { spacing: { before: pt(5), after: pt(2) } });
}
function MH(num, text) {   // 중제목
  return P([KR(`${num}. ${text}`, 11, true)], { spacing: { before: pt(7), after: pt(3) } });
}

const archImg = loadImg(path.join(ASSETS, "fig1_arch.png"), COL*2 + GAP, Math.round((COL*2+GAP)*0.58));

const sec2children = [

  // ══════════════════════════════
  // 1. 서론
  // ══════════════════════════════
  MH("1", "서  론"),
  BP("대학생은 학기 중 과제, 시험, 수업 일정, 학교 공지, 장학금, 공모전, 인턴십 등 다양한 정보를 " +
     "동시에 관리해야 한다. 이 정보들은 학교 홈페이지, 학과 홈페이지, 공공기관 웹사이트, " +
     "개인 메모 앱, 캘린더 앱 등에 흩어져 있어 사용자가 필요한 정보를 얻으려면 여러 사이트를 " +
     "직접 방문해야 하며, 찾은 정보를 다시 일정이나 과제로 등록해야 하는 이중 부담이 발생한다."),
  BP("최근 LLM 기반 챗봇은 자연어 질의응답에 강점을 보이지만, 단순 대화만으로는 실제 할 일을 " +
     "저장하거나 학교 공지를 검색하거나 과제 진행률을 관리하기 어렵다. 따라서 대학생에게 " +
     "실질적으로 도움이 되는 AI 비서를 구현하려면 LLM, 로컬 데이터베이스, 검색 시스템, " +
     "외부 정보 수집 도구가 함께 연결되어야 한다."),
  BP("본 논문에서는 이러한 문제를 해결하기 위해 LangGraph 기반 에이전트, LangChain 도구 " +
     "호출, SQLite, ChromaDB, Streamlit, 웹 크롤링, 공공 API를 결합한 로컬 AI 학생 비서 " +
     "CampusAgent를 설계하고 구현한 결과를 다룬다."),

  // ══════════════════════════════
  // 2. 관련 기술
  // ══════════════════════════════
  MH("2", "관련 기술"),

  SH("2.1", "LangGraph와 도구 호출"),
  BP("LangGraph[1]는 LLM 호출, 도구 실행, 상태 저장을 그래프 형태로 구성할 수 있는 " +
     "프레임워크다. CampusAgent는 agent 노드에서 LLM을 호출하고, 도구 호출이 필요한 경우 " +
     "ToolNode로 이동한 뒤 다시 agent 노드로 돌아오는 순환 구조를 사용한다. 도구는 " +
     "LangChain의 @tool 데코레이터로 정의되며 LLM이 자연어 요청을 분석하여 적절한 도구를 " +
     "선택하고 실행한다."),

  SH("2.2", "RAG"),
  BP("RAG(Retrieval-Augmented Generation)[2]는 외부 문서를 검색한 뒤 검색 결과를 LLM 응답에 " +
     "활용하는 방식이다. CampusAgent는 학교 공지와 학생 정보 데이터를 텍스트 청크로 나누고 " +
     "ChromaDB에 저장한 뒤 질의와 유사한 문서를 검색한다. 저장된 데이터가 부족할 경우 " +
     "학교 홈페이지를 실시간 크롤링하여 최신 정보를 보강한다."),

  SH("2.3", "SQLite와 ChromaDB"),
  BP("CampusAgent는 구조화 데이터와 비정형 검색 데이터를 분리 저장한다. 과제, 일정, 사용자 " +
     "설정, 대화 메시지는 SQLite[3]에 저장하고, 공지사항과 학생 정보처럼 의미 기반 검색이 " +
     "필요한 텍스트 데이터는 ChromaDB[4]에 저장한다. 이 구조는 트랜잭션이 필요한 데이터와 " +
     "의미 기반 검색이 필요한 데이터를 각 목적에 맞게 처리한다."),

  // ══════════════════════════════
  // 3. 시스템 설계 및 구현
  // ══════════════════════════════
  MH("3", "시스템 설계 및 구현"),

  SH("3.1", "전체 구조"),
  BP("CampusAgent의 전체 구조는 <그림 1>과 같다. 사용자가 Streamlit 채팅 UI에서 자연어 " +
     "요청을 입력하면 LangGraph 에이전트가 도구 호출 여부를 판단한다. 도구 호출이 필요한 " +
     "경우 ToolNode에서 총 29개의 LangChain 도구 중 적절한 도구가 실행되고, 결과를 바탕으로 " +
     "최종 응답이 생성된다."),
  BP("UI는 챗봇, 과제 대시보드, 캘린더, 설정의 4개 탭으로 구성되며 사용자의 전공, 학년, " +
     "관심 영역, 희망 진로 등의 개인화 프로필이 매 턴 에이전트 시스템 프롬프트에 주입된다."),

  // 그림 1 (아키텍처) - 2컬럼 합치기 위해 full-width 이미지
  ...(archImg ? [
    P([archImg], { alignment: AlignmentType.CENTER, spacing: { before: pt(4), after: 0 } }),
  ] : [
    P([KR("[ 그림 1: 시스템 전체 구조도 삽입 위치 ]", 9, false, { color: "888888" })],
      { alignment: AlignmentType.CENTER }),
  ]),
  P([KR("그림 1. 시스템 전체 구조도", 9, true), KR(" / ", 9), ER("Figure 1. System Architecture", 9, true)],
    { alignment: AlignmentType.CENTER, spacing: { before: 0, after: pt(5) } }),

  SH("3.2", "과제 관리 및 서브태스크 자동 분해"),
  BP("과제 관리 기능은 <표 1>과 같이 9개의 도구로 구성된다. 사용자가 \"자료구조 프로젝트 " +
     "과제 추가해줘. 마감일은 6월 20일이고 단계별로 나눠줘\"처럼 요청하면 에이전트가 " +
     "add_task_with_subtasks 도구를 호출한다."),
  BP("이 도구는 제목과 설명의 키워드를 분석하여 과제 유형(발표형/보고서형/코딩형/시험형/일반형)을 " +
     "감지하고 유형별 템플릿에 따라 5~7개의 서브태스크를 자동 생성한다. 각 서브태스크의 " +
     "마감일은 부모 과제 마감일로부터 역산하여 배분된다."),
  BP("서브태스크 완료 시 progress = 완료 수 / 전체 수 × 100(%)로 진행률이 계산되며, " +
     "진행률이 100%에 도달하면 부모 과제 상태가 자동으로 done으로 갱신된다. " +
     "<그림 2>는 챗봇 탭에서 과제 자동 분해가 실행된 결과이고, " +
     "<그림 3>은 과제 대시보드에서 서브태스크 진행률을 확인하는 화면이다."),

  // 표 1
  BP(""),
  makeTable(
    ["도구", "역할"],
    [
      ["add_task", "단순 과제 추가"],
      ["add_task_with_subtasks", "큰 과제를 5~7개 서브태스크로 자동 분해"],
      ["list_tasks / list_task_tree", "과제 목록 / 계층 구조 조회"],
      ["update_task_status / update_subtask_status_tool", "과제 · 서브태스크 상태 변경"],
      ["get_task_progress", "진행률 조회"],
      ["delete_task", "과제 + 서브태스크 CASCADE 삭제"],
      ["get_upcoming_deadlines", "마감 임박 과제 조회"],
    ],
    [Math.round(COL*0.45), Math.round(COL*0.55)]
  ),
  P([KR("표 1. 과제 관리 도구 구성", 9, true), KR(" / ", 9), ER("Table 1. Task Management Tools", 9, true)],
    { alignment: AlignmentType.CENTER, spacing: { before: pt(2), after: pt(5) } }),

  // 그림 2 (챗봇 과제 분해) — 1 column 폭
  ...figPara(SHOTS.fig2, COL, Math.round(COL*0.58),
    "그림 2. 과제 자동 분해 결과 (챗봇)",
    "Figure 2. Task Auto-Decomposition in Chatbot"),

  // 그림 3 (과제 대시보드) — 1 column 폭
  ...figPara(SHOTS.fig3, COL, Math.round(COL*0.58),
    "그림 3. 과제 대시보드 (진행률 + 서브태스크)",
    "Figure 3. Task Dashboard with Progress"),

  SH("3.3", "공지사항 RAG 검색"),
  BP("공지 검색은 학과 공지(인하공업전문대학 컴퓨터시스템공학과)와 학교 대표 공지를 구분한다. " +
     "검색 요청이 들어오면 ChromaDB 캐시에서 먼저 관련 문서를 검색하고, 결과가 부족하면 " +
     "학교 홈페이지를 실시간 크롤링하여 데이터를 보강한다. 수집된 공지는 500자 단위로 " +
     "청킹(overlap 50자)된 후 ChromaDB에 저장되어 이후 검색에 재활용된다."),
  BP("<그림 5>와 같이 검색 결과에는 공지 제목, 날짜, 요약, URL이 포함되며 " +
     "\"마감일을 캘린더에 등록해줘\"처럼 후속 동작으로 연계할 수 있는 버튼도 제공된다."),

  // 그림 5 (공지 검색)
  ...figPara(SHOTS.fig5, COL, Math.round(COL*0.70),
    "그림 5. 공지사항 RAG 검색 결과",
    "Figure 5. Notice Search Result (RAG)"),

  SH("3.4", "캘린더 및 일정 관리"),
  BP("일정 관리 기능은 add_calendar_event, list_calendar_events, get_today_schedule, " +
     "get_week_schedule, delete_calendar_event, check_dday 6개의 도구로 구성된다. " +
     "에이전트는 시스템 프롬프트에 현재 시간을 주입받아 \"내일 9시\", \"다음 주 수요일\" 같은 " +
     "상대적 날짜 표현을 절대 날짜(YYYY-MM-DD)로 변환한 후 도구를 호출한다."),
  BP("Streamlit UI의 캘린더 탭(<그림 4>)은 월별 그리드로 일정과 과제 마감일을 배지로 표시하며 " +
     "우선순위별 색상(빨강/주황/초록), 카테고리(수업/시험/개인/회의), ◀▶ 월 이동 기능을 제공한다."),

  // 그림 4 (캘린더)
  ...figPara(SHOTS.fig4, COL, Math.round(COL*0.58),
    "그림 4. 캘린더 탭 (월별 일정 + 과제 마감)",
    "Figure 4. Calendar Tab"),

  SH("3.5", "대학생 정보 검색 및 개인화 추천"),
  BP("대학생 정보 검색은 편입학, 국가장학금, 청년정책, 공모전, 인턴십 정보를 9개의 도구로 " +
     "통합 제공한다. 개인화 추천 도구 search_personalized_student_info는 설정 탭(<그림 6>)에서 " +
     "저장된 전공, 학년, 관심 영역, 희망 진로를 기반으로 카테고리별 검색 쿼리를 자동 생성하여 " +
     "ChromaDB에서 의미 검색을 수행하고 추천 이유 레이블을 붙여 반환한다."),
  BP("외부 공공 API 도구로 온통청년 API 기반 청년정책 검색, 워크넷 API 기반 채용공고 검색, " +
     "K-스타트업 공모전 크롤링이 구현되어 있다. 단, 실제 신청 가능 여부는 나이, 거주 지역, " +
     "소득 등 세부 조건에 따라 달라지므로 현재 시스템에서는 후보 탐색과 원문 확인 보조 기능으로 " +
     "범위를 한정하고 있다."),

  // 그림 6 (설정)
  ...figPara(SHOTS.fig6, COL, Math.round(COL*0.62),
    "그림 6. 사용자 설정 탭 (개인화 프로필)",
    "Figure 6. User Settings Tab"),

  SH("3.6", "저장소 설계 및 장기기억"),
  BP("SQLite에는 <표 2>와 같이 7개의 테이블이 사용된다. 앱 재실행 후 최근 20개의 대화 " +
     "메시지가 자동으로 복원되어 기본 대화 맥락이 유지된다. 단기 문맥은 LangGraph의 " +
     "MemorySaver로 유지되며 session 내 모든 도구 호출 흐름이 보존된다."),
  BP(""),
  makeTable(
    ["테이블", "역할"],
    [
      ["assignments", "과제 기본 정보 저장"],
      ["assignment_subtasks", "서브태스크 저장 (FK → assignments)"],
      ["schedules", "일정 정보 저장"],
      ["user_settings", "전공·학년·관심 영역 등 사용자 설정"],
      ["conversation_sessions", "대화 세션 정보"],
      ["conversation_messages", "대화 메시지 원문 저장"],
      ["memory_summaries", "장기기억 요약 (테이블·함수 준비됨)"],
    ],
    [Math.round(COL*0.42), Math.round(COL*0.58)]
  ),
  P([KR("표 2. SQLite 테이블 구성", 9, true), KR(" / ", 9), ER("Table 2. SQLite Table Schema", 9, true)],
    { alignment: AlignmentType.CENTER, spacing: { before: pt(2), after: pt(5) } }),

  // ══════════════════════════════
  // 4. 결론
  // ══════════════════════════════
  MH("4", "결  론"),
  BP("본 논문에서는 대학생의 과제 관리, 일정 관리, 공지사항 검색, 대학생 정보 탐색을 하나의 " +
     "대화형 인터페이스로 통합한 로컬 AI 학생 비서 CampusAgent를 구현하였다. LangGraph 기반 " +
     "에이전트가 29개의 LangChain 도구를 통해 SQLite, ChromaDB, 외부 API, 웹 크롤러와 연결되어 " +
     "자연어 요청을 실제 데이터 처리 작업으로 변환한다."),
  BP("특히 과제 자동 분해 기능은 큰 과제를 규칙 기반으로 5~7개의 서브태스크로 분해하고 " +
     "서브태스크 완료율에 따라 부모 과제 진행률을 자동 갱신하는 학습 관리 도구로서 " +
     "단순한 과제 등록을 넘어 실행 가능한 작업 계획으로 변환한다는 점에서 의미가 있다. " +
     "또한 67개의 pytest 테스트 케이스가 모두 통과함으로써 주요 기능의 정확성을 검증하였다."),
  BP("향후에는 자동 요약 메모리 구현, ChromaDB 컬렉션 분리, 청년정책 조건 구조화, " +
     "Multi-Agent 구조 도입을 통해 더 정교한 개인화 학생 비서로 발전시킬 계획이다."),

  // ══════════════════════════════
  // References
  // ══════════════════════════════
  hline("000000", 4),
  P([KR("References", 10, true)], { spacing: { before: pt(4), after: pt(2) } }),

  ...[
    "[1] LangChain AI, \"LangGraph - Building Stateful, Multi-Actor Applications with LLMs,\" " +
      "LangChain Documentation, 2024. https://langchain-ai.github.io/langgraph/",
    "[2] P. Lewis et al., \"Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks,\" " +
      "Advances in Neural Information Processing Systems, Vol.33, 2020.",
    "[3] D. R. Hipp, \"SQLite - A Self-Contained, Serverless, Zero-Configuration, Transactional SQL " +
      "Database Engine,\" https://www.sqlite.org/, 2024.",
    "[4] Chroma Research, \"Chroma - The AI-native Open-source Embedding Database,\" " +
      "https://www.trychroma.com/, 2024.",
    "[5] Streamlit Inc., \"Streamlit - The Fastest Way to Build and Share Data Apps,\" " +
      "https://streamlit.io/, 2024.",
    "[6] LangChain AI, \"LangChain - Building Applications with LLMs,\" " +
      "https://www.langchain.com/, 2024.",
    "[7] Google DeepMind, \"Gemini 2.5 Flash Technical Report,\" Google, 2025.",
    "[8] 온통청년 공식 홈페이지, https://www.youthcenter.go.kr/, 2024.",
  ].map(ref => P([ER(ref, 8.5)], { spacing: { before: 0, after: pt(1) } })),
];

// ─────────────────────────────────────────────────────────────────────────
// 섹션 3: 단컬럼 — 한국어 요약
// ─────────────────────────────────────────────────────────────────────────
const sec3children = [
  hline("000000", 6),
  P([KR("어린이 정서 기반의 색칠놀이 앱에 관한", 10)], // 아래 한국어 논문 제목
    { alignment: AlignmentType.CENTER, spacing: { before: pt(4), after: 0 } }),

  // 실제 한국어 논문 제목 (한국어)
  P([KR("CampusAgent: 대학생을 위한 LangGraph 기반 로컬 AI 학생 비서", 12, true)],
    { alignment: AlignmentType.CENTER, spacing: { before: 0, after: pt(3) } }),

  P([KR("김태욱", 10, true), KR("¹", 9)],
    { alignment: AlignmentType.CENTER, spacing: { before: 0, after: 0 } }),
  P([KR("¹인하공업전문대학 컴퓨터시스템공학과", 9, false, { italics: true })],
    { alignment: AlignmentType.CENTER, spacing: { before: 0, after: pt(4) } }),

  P([KR("요  약", 11, true)], { alignment: AlignmentType.CENTER, spacing: { before: 0, after: pt(2) } }),

  P([KR(
    "대학생은 학기 중 과제, 시험, 일정, 학교 공지, 장학금, 공모전, 인턴십 등 다양한 정보를 " +
    "여러 플랫폼에서 따로 관리해야 한다는 불편함이 있다. 본 논문에서는 이를 해결하기 위해 " +
    "자연어 요청 하나로 과제 등록, 일정 관리, 공지 검색, 대학생 정보 추천을 한 번에 처리하는 " +
    "로컬 AI 학생 비서 CampusAgent를 설계하고 구현하였다.", 9.5)],
    { alignment: AlignmentType.JUSTIFIED, spacing: { before: 0, after: pt(2) } }),

  P([KR(
    "CampusAgent는 LangGraph 기반 에이전트가 29개의 LangChain 도구를 통해 SQLite, ChromaDB, " +
    "외부 API, 웹 크롤러와 연결되는 구조로 설계되었다. 핵심 기능인 과제 자동 분해는 사용자의 " +
    "과제를 규칙 기반으로 5~7개의 서브태스크로 분해하고 완료율에 따라 부모 과제 진행률을 " +
    "자동 갱신한다. 공지사항 RAG 검색은 ChromaDB 캐시와 실시간 크롤링을 결합하여 최신 " +
    "학교 공지를 제공하며, 개인화 설정에 따른 맞춤 대학생 정보 추천 기능도 포함한다. " +
    "67개의 자동화 테스트 케이스가 모두 통과함으로써 전체 서브시스템의 정확성이 검증되었다.", 9.5)],
    { alignment: AlignmentType.JUSTIFIED, spacing: { before: 0, after: pt(4) } }),
];

// ─────────────────────────────────────────────────────────────────────────
// Document 조립
// ─────────────────────────────────────────────────────────────────────────
const margins = { top: MT, right: MR, bottom: MB, left: ML };

const doc = new Document({
  styles: {
    default: {
      document: { run: { font: KN, size: pt(9.5) } }
    }
  },
  sections: [
    // ── 섹션 1: 단컬럼 헤더 ──
    {
      properties: {
        type: SectionType.CONTINUOUS,
        page: { size: { width: PW, height: PH }, margin: margins }
      },
      children: sec1children
    },
    // ── 섹션 2: 2-컬럼 본문 ──
    {
      properties: {
        type: SectionType.CONTINUOUS,
        column: { count: 2, space: GAP, equalWidth: true },
        page: { size: { width: PW, height: PH }, margin: margins }
      },
      children: sec2children
    },
    // ── 섹션 3: 단컬럼 한국어 요약 ──
    {
      properties: {
        type: SectionType.NEXT_PAGE,
        page: { size: { width: PW, height: PH }, margin: margins }
      },
      children: sec3children
    }
  ]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(OUT, buf);
  console.log("✅ Created:", OUT);
}).catch(err => {
  console.error("❌ Error:", err.message);
  process.exit(1);
});
