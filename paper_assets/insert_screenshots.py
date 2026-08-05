# 스크린샷을 paper_assets 폴더에 아래 이름으로 저장한 뒤 이 스크립트 실행
# fig2_chatbot.png  → 챗봇 과제 분해 결과   (스크린샷 4번)
# fig3_dashboard.png → 과제 대시보드        (스크린샷 5번)
# fig4_calendar.png  → 캘린더 탭            (스크린샷 1번)
# fig5_notice.png    → 공지 검색 결과       (스크린샷 3번)
# fig6_settings.png  → 설정 탭              (스크린샷 2번)

import subprocess, sys, os
script_dir = os.path.dirname(os.path.abspath(__file__))

required = {
    "fig2_chatbot.png":   "챗봇 과제 분해 결과 (스크린샷 4번)",
    "fig3_dashboard.png": "과제 대시보드     (스크린샷 5번)",
    "fig4_calendar.png":  "캘린더 탭         (스크린샷 1번)",
    "fig5_notice.png":    "공지 검색 결과    (스크린샷 3번)",
    "fig6_settings.png":  "설정 탭           (스크린샷 2번)",
}

missing = [name for name in required if not os.path.exists(os.path.join(script_dir, name))]
if missing:
    print("⚠️  아래 파일이 없습니다. paper_assets 폴더에 저장해주세요:")
    for m in missing:
        print(f"   {m}  ←  {required[m]}")
    print("\n파일 저장 후 다시 실행하면 논문에 삽입됩니다.")
    sys.exit(1)

print("✅ 모든 스크린샷 확인됨. DOCX 재생성 중...")
result = subprocess.run(
    ["node", "make_paper.js"],
    cwd=script_dir,
    capture_output=True, text=True
)
print(result.stdout)
if result.returncode != 0:
    print("❌ 오류:", result.stderr)
else:
    print("논문 파일: paper_assets/CampusAgent_최종보고서.docx")
