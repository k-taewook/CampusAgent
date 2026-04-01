"""
CampusAgent - 문서 로더
- JSON / 텍스트 형식의 공지사항 데이터를 로딩
- 각 문서를 표준 dict 형태로 변환
"""
import json
import os
from typing import List, Optional
from datetime import datetime


def load_notices_from_json(filepath: str) -> List[dict]:
    """
    JSON 파일에서 공지사항 목록을 로드합니다.
    
    Expected JSON 형식:
    [
        {
            "title": "공지 제목",
            "content": "공지 내용",
            "date": "2026-04-01",
            "category": "학사",
            "source": "학과 홈페이지"
        }, ...
    ]
    
    Returns:
        List[dict]: 표준화된 문서 리스트
    """
    if not os.path.exists(filepath):
        print(f"⚠️ 파일을 찾을 수 없습니다: {filepath}")
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    documents = []
    for idx, item in enumerate(raw_data):
        doc = {
            "id": f"notice_{idx}",
            "title": item.get("title", "제목 없음"),
            "content": item.get("content", ""),
            "date": item.get("date", ""),
            "category": item.get("category", "일반"),
            "source": item.get("source", "알 수 없음"),
            # 검색에 사용할 전체 텍스트
            "full_text": f"[{item.get('category', '일반')}] {item.get('title', '')} - {item.get('content', '')}",
        }
        documents.append(doc)

    print(f"📄 {len(documents)}개의 공지사항 로드 완료 ({filepath})")
    return documents


def load_notices_from_text(filepath: str, delimiter: str = "\n---\n") -> List[dict]:
    """
    텍스트 파일에서 구분자(---)기준으로 공지사항을 로드합니다.
    
    Returns:
        List[dict]: 문서 리스트
    """
    if not os.path.exists(filepath):
        print(f"⚠️ 파일을 찾을 수 없습니다: {filepath}")
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    sections = text.split(delimiter)
    documents = []
    for idx, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue
        # 첫 줄을 제목으로 사용
        lines = section.split("\n", 1)
        title = lines[0].strip()
        content = lines[1].strip() if len(lines) > 1 else ""

        documents.append({
            "id": f"text_{idx}",
            "title": title,
            "content": content,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "category": "일반",
            "source": os.path.basename(filepath),
            "full_text": f"{title} - {content}",
        })

    print(f"📄 {len(documents)}개의 문서 로드 완료 ({filepath})")
    return documents
