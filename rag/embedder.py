"""
CampusAgent - 임베딩 생성기
- ChromaDB 기본 임베딩 사용 (all-MiniLM-L6-v2 기반)
- 별도 무거운 모델 설치 없이 동작
"""
from typing import List
import chromadb

from config.settings import CHROMA_DB_DIR, CHROMA_COLLECTION_NAME


class DocumentEmbedder:
    """
    ChromaDB에 문서를 임베딩하여 저장하는 클래스
    - ChromaDB의 내장 임베딩 함수 사용 (별도 설치 불필요)
    """

    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
        self.collection = self.client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def embed_and_store(self, chunked_docs: List[dict]) -> int:
        """
        청킹된 문서들을 ChromaDB에 임베딩 & 저장
        
        Args:
            chunked_docs: chunker에서 나온 문서 리스트
                          각 문서에는 id, text, title, date, category 등 포함
        
        Returns:
            저장된 문서 수
        """
        if not chunked_docs:
            print("⚠️ 저장할 문서가 없습니다.")
            return 0

        ids = [doc["id"] for doc in chunked_docs]
        documents = [doc["text"] for doc in chunked_docs]
        metadatas = [
            {
                "title": doc.get("title", ""),
                "date": doc.get("date", ""),
                "category": doc.get("category", ""),
                "source": doc.get("source", ""),
                "chunk_index": doc.get("chunk_index", 0),
            }
            for doc in chunked_docs
        ]

        # 중복 방지: 기존 ID가 있으면 upsert
        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

        print(f"💾 {len(chunked_docs)}개 문서 ChromaDB 저장 완료 (총 문서: {self.collection.count()})")
        return len(chunked_docs)

    def get_collection_count(self) -> int:
        """현재 컬렉션의 문서 수 반환"""
        return self.collection.count()

    def clear_collection(self):
        """컬렉션 초기화 (전체 삭제 후 재생성)"""
        self.client.delete_collection(CHROMA_COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        print("🗑️ ChromaDB 컬렉션 초기화 완료")
