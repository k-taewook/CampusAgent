"""
CampusAgent - 텍스트 청커
- 긴 문서를 검색에 적합한 크기로 분할
- RecursiveCharacterTextSplitter 활용
"""
from typing import List


class SimpleTextChunker:
    """
    간단한 텍스트 청커
    - chunk_size: 각 청크의 최대 문자 수
    - chunk_overlap: 청크 간 겹치는 문자 수 (문맥 유지)
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> List[str]:
        """텍스트를 청크로 분할"""
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size

            # 문장 단위로 자르기 시도
            if end < len(text):
                # 마지막 마침표, 물음표, 느낌표, 줄바꿈 위치 찾기
                for sep in ["\n\n", "\n", ". ", "? ", "! "]:
                    last_sep = text.rfind(sep, start, end)
                    if last_sep > start:
                        end = last_sep + len(sep)
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - self.chunk_overlap
            if start >= len(text):
                break

        return chunks

    def split_documents(self, documents: List[dict]) -> List[dict]:
        """
        문서 리스트를 청킹하여 반환
        각 문서의 'full_text' 필드를 분할하고, 메타데이터를 유지
        """
        chunked_docs = []
        for doc in documents:
            text = doc.get("full_text", doc.get("content", ""))
            chunks = self.split_text(text)

            for chunk_idx, chunk in enumerate(chunks):
                chunked_doc = {
                    "id": f"{doc['id']}_chunk{chunk_idx}",
                    "text": chunk,
                    "title": doc.get("title", ""),
                    "date": doc.get("date", ""),
                    "category": doc.get("category", ""),
                    "source": doc.get("source", ""),
                    "url": doc.get("url", ""),
                    "chunk_index": chunk_idx,
                    "total_chunks": len(chunks),
                }
                chunked_docs.append(chunked_doc)

        print(f"✂️ {len(documents)}개 문서 → {len(chunked_docs)}개 청크로 분할 완료")
        return chunked_docs
