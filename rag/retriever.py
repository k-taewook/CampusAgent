import chromadb
import os

DB_DIR = "chroma_db_storage"

def init_chromadb():
    print(f"🗃️ ChromaDB 벡터 스토어 초기화 중... ({DB_DIR})")
    client = chromadb.PersistentClient(path=DB_DIR)
    
    # 공지사항 컬렉션 생성 (존재하면 가져오기)
    collection_name = "university_notices"
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )
    
    print(f"✅ ChromaDB 단일 컬렉션 '{collection_name}' 세팅 완료 (총 문서 수: {collection.count()})")
    return collection

if __name__ == "__main__":
    init_chromadb()
