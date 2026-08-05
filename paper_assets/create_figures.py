# CampusAgent 논문 그림 생성 스크립트
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
import os, sys

plt.rcParams['font.family'] = ['Malgun Gothic', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

OUT = os.path.dirname(os.path.abspath(__file__))

# ──────────────────────────────────────────────
# 그림 1: 시스템 전체 구조도
# ──────────────────────────────────────────────
def fig1_arch():
    # 캔버스 원래 크기 유지, 글자만 최대화
    fig, ax = plt.subplots(figsize=(13, 7.5), facecolor='white')
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 7.5)
    ax.axis('off')

    # fs: 제목, fs-5: 부제목. 박스 높이(h단위) 기준으로 꽉 차게 설정
    def box(x, y, w, h, title, sub=None, fc='#1565C0', fs=19):
        r = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                                    lw=1.5, ec=fc, fc=fc, zorder=2, alpha=0.92)
        ax.add_patch(r)
        ty = y + h/2 + (h*0.14 if sub else 0)
        ax.text(x+w/2, ty, title, ha='center', va='center',
                fontsize=fs, fontweight='bold', color='white', zorder=3)
        if sub:
            ax.text(x+w/2, y+h*0.24, sub, ha='center', va='center',
                    fontsize=fs-6, color='white', alpha=0.95, zorder=3)

    def arr(x1, y1, x2, y2, lbl='', lx=None, ly=None, ha='left'):
        ax.annotate('', xy=(x2,y2), xytext=(x1,y1),
                    arrowprops=dict(arrowstyle='->', color='#444', lw=2), zorder=1)
        if lbl:
            ax.text(lx or (x1+x2)/2+0.05, ly or (y1+y2)/2,
                    lbl, fontsize=12, color='#222', ha=ha)

    # ── Streamlit UI (원래 폭 유지) ──────────────────────────
    box(0.4, 6.1, 12.2, 1.1, 'Streamlit UI',
        '챗봇  |  과제 대시보드  |  캘린더  |  설정', '#0D47A1', 20)

    # Arrow: UI → Agent
    arr(6.5, 6.1, 6.5, 5.65, '사용자 입력 + 개인화 컨텍스트', lx=6.55, ly=5.88)

    # ── LangGraph Agent (폭 축소: 9.4 → 7.6) ────────────────
    box(1.8, 4.5, 7.6, 1.0, 'LangGraph Agent  (MemorySaver)',
        'Gemini / OpenAI  ·  개인화 프로필 자동 주입', '#1B5E20', 18)

    # Arrow: Agent → ToolNode
    arr(4.5, 4.5, 4.5, 4.07, 'tool_calls', lx=3.4, ly=4.28, ha='right')

    # Arrow: Agent → 최종 응답 (박스 오른쪽 끝 9.4부터 12.8까지 넉넉하게)
    ax.annotate('', xy=(12.8, 5.0), xytext=(9.4, 5.0),
                arrowprops=dict(arrowstyle='->', color='#444', lw=2))
    ax.text(10.0, 5.28, '최종 응답', fontsize=15, color='#222',
            va='center', fontweight='bold')

    # ── ToolNode (폭 축소: 9.4 → 7.6) ───────────────────────
    box(1.8, 2.95, 7.6, 1.0, 'ToolNode  (총 29개 도구)',
        'Task(9)  |  Calendar(6)  |  RAG(5)  |  Student Info(9)', '#4A148C', 18)

    # Arrows: ToolNode → 하단 저장소
    arr(3.2, 2.95, 2.4, 2.38)
    arr(5.8, 2.95, 5.8, 2.38)
    arr(8.2, 2.95, 9.0, 2.38)

    # ── SQLite ────────────────────────────────────────────────
    box(0.2, 1.25, 4.1, 1.05, 'SQLite',
        '과제 · 일정 · 대화 · 설정', '#B71C1C', 18)

    # ── ChromaDB ──────────────────────────────────────────────
    box(4.5, 1.25, 4.1, 1.05, 'ChromaDB',
        '공지 · 학생정보 (벡터검색)', '#006064', 18)

    # ── 외부 API ──────────────────────────────────────────────
    box(8.8, 1.25, 4.0, 1.05, '외부 API / 크롤러',
        '학교공지 · 온통청년 · 워크넷', '#E65100', 18)

    plt.tight_layout(pad=0.3)
    path = os.path.join(OUT, 'fig1_arch.png')
    plt.savefig(path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f'Saved: {path}')

fig1_arch()
print("Done!")
