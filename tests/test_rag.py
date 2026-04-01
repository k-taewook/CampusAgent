"""
CampusAgent - RAG 파이프라인 단위 테스트
"""
import pytest
import os
import sys
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rag.loader import load_notices_from_json
from rag.chunker import SimpleTextChunker
from rag.embedder import DocumentEmbedder
from rag.retriever import search_notices
import config.settings as settings


@pytest.fixture(autouse=True)
def setup_test_chroma(tmp_path):
    """테스트용 임시 ChromaDB 사용"""
    test_chroma = str(tmp_path / "test_chroma")
    settings.CHROMA_DB_DIR = test_chroma
    # embedder와 retriever가 사용하는 경로도 동기화
    import rag.embedder as emb
    import rag.retriever as ret
    emb.CHROMA_DB_DIR = test_chroma
    ret.CHROMA_DB_DIR = test_chroma
    yield
    # Windows에서 ChromaDB SQLite 파일 lock으로 인한 PermissionError 방지
    try:
        if os.path.exists(test_chroma):
            shutil.rmtree(test_chroma, ignore_errors=True)
    except Exception:
        pass


class TestLoader:
    def test_load_sample_json(self):
        """샘플 JSON 로드"""
        filepath = os.path.join(os.path.dirname(__file__), "..", "data", "sample_notices.json")
        if not os.path.exists(filepath):
            pytest.skip("sample_notices.json not found")

        docs = load_notices_from_json(filepath)
        assert len(docs) > 0
        assert "title" in docs[0]
        assert "content" in docs[0]
        assert "full_text" in docs[0]

    def test_load_nonexistent(self):
        """존재하지 않는 파일"""
        docs = load_notices_from_json("nonexistent.json")
        assert docs == []


class TestChunker:
    def test_short_text(self):
        """짧은 텍스트는 분할 안 됨"""
        chunker = SimpleTextChunker(chunk_size=500)
        chunks = chunker.split_text("짧은 텍스트입니다.")
        assert len(chunks) == 1

    def test_long_text(self):
        """긴 텍스트 분할"""
        chunker = SimpleTextChunker(chunk_size=100, chunk_overlap=10)
        long_text = "이것은 테스트 문장입니다. " * 50
        chunks = chunker.split_text(long_text)
        assert len(chunks) > 1

    def test_split_documents(self):
        """문서 리스트 분할"""
        chunker = SimpleTextChunker(chunk_size=100, chunk_overlap=10)
        docs = [
            {"id": "test_0", "title": "테스트", "content": "내용", "full_text": "테스트 " * 100},
        ]
        chunked = chunker.split_documents(docs)
        assert len(chunked) > 1
        assert chunked[0]["title"] == "테스트"


class TestEmbedder:
    def test_embed_and_store(self):
        """임베딩 & 저장"""
        embedder = DocumentEmbedder()
        docs = [
            {
                "id": "test_0_chunk0",
                "text": "장학금 신청 관련 공지사항입니다.",
                "title": "장학금 공지",
                "date": "2026-04-01",
                "category": "장학",
                "source": "학생지원팀",
                "chunk_index": 0,
            },
            {
                "id": "test_1_chunk0",
                "text": "수강신청 변경 기간 안내입니다.",
                "title": "수강신청 변경",
                "date": "2026-03-10",
                "category": "학사",
                "source": "학사지원팀",
                "chunk_index": 0,
            },
        ]
        stored = embedder.embed_and_store(docs)
        assert stored == 2
        assert embedder.get_collection_count() == 2

    def test_empty_store(self):
        """빈 문서 저장"""
        embedder = DocumentEmbedder()
        stored = embedder.embed_and_store([])
        assert stored == 0


class TestFullPipeline:
    def test_load_chunk_embed_search(self):
        """전체 파이프라인: 로드 → 청킹 → 임베딩 → 검색"""
        filepath = os.path.join(os.path.dirname(__file__), "..", "data", "sample_notices.json")
        if not os.path.exists(filepath):
            pytest.skip("sample_notices.json not found")

        # 1. 로드
        docs = load_notices_from_json(filepath)
        assert len(docs) > 0

        # 2. 청킹
        chunker = SimpleTextChunker(chunk_size=500, chunk_overlap=50)
        chunked = chunker.split_documents(docs)
        assert len(chunked) >= len(docs)

        # 3. 임베딩 & 저장
        embedder = DocumentEmbedder()
        stored = embedder.embed_and_store(chunked)
        assert stored > 0

        # 4. 검색
        results = search_notices("장학금 신청", n_results=3)
        assert len(results) > 0
        # 첫 번째 결과의 관련도가 0보다 커야함
        assert results[0]["relevance"] > 0
