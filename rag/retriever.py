"""
CampusAgent - 벡터 검색기 (Retriever)
- ChromaDB 기반 유사도 검색
- 메타데이터 필터링 지원
"""
import chromadb
from typing import List, Optional

from config.settings import CHROMA_DB_DIR, CHROMA_COLLECTION_NAME


def init_chromadb():
    """ChromaDB 벡터 스토어 초기화"""
    print(f"🗃️ ChromaDB 벡터 스토어 초기화 중... ({CHROMA_DB_DIR})")
    client = chromadb.PersistentClient(path=CHROMA_DB_DIR)

    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    print(f"✅ ChromaDB 컬렉션 '{CHROMA_COLLECTION_NAME}' 세팅 완료 (총 문서 수: {collection.count()})")
    return collection


def search_notices(
    query: str,
    n_results: int = 5,
    category: Optional[str] = None,
) -> List[dict]:
    """
    공지사항을 유사도 기반으로 검색합니다.

    Args:
        query: 검색 질의 (자연어)
        n_results: 반환할 결과 수 (기본 5)
        category: 카테고리 필터 (학사/장학/취업 등, 선택)

    Returns:
        검색 결과 리스트 [{text, title, date, category, source, distance}]
    """
    client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    if collection.count() == 0:
        return []

    # 메타데이터 필터 설정
    where_filter = None
    if category:
        where_filter = {"category": category}

    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count()),
        where=where_filter,
    )

    search_results = []
    if results and results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            distance = results["distances"][0][i] if results["distances"] else 0

            search_results.append({
                "text": doc,
                "title": metadata.get("title", ""),
                "date": metadata.get("date", ""),
                "category": metadata.get("category", ""),
                "source": metadata.get("source", ""),
                "url": metadata.get("url", ""),
                "deadline": metadata.get("deadline", ""),
                "target": metadata.get("target", ""),
                "source_type": metadata.get("source_type", ""),
                "provider": metadata.get("provider", ""),
                "eligibility_checked": metadata.get("eligibility_checked", ""),
                "query_context": metadata.get("query_context", ""),
                "distance": round(distance, 4),
                "relevance": round(1 - distance, 4),  # 코사인 유사도
            })

    return search_results


def get_notice_count() -> int:
    """저장된 공지사항 총 수"""
    client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    return collection.count()


if __name__ == "__main__":
    init_chromadb()
