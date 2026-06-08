"""
Task 4 — Chunking & Indexing vào Vector Store.
"""

from pathlib import Path

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"

# CHUNK_SIZE: Kích thước mỗi chunk (ký tự). Chọn 500 vì nó vừa đủ chứa khoảng 2-3 câu dài,
# đảm bảo giữ được ngữ cảnh của điều luật/tin tức mà không vượt quá giới hạn token của LLM.
CHUNK_SIZE = 500

# CHUNK_OVERLAP: Độ gối đầu giữa các chunk. Chọn 50 vì nó giúp liên kết thông tin liền mạch
# giữa các đoạn liền kề, không bị mất thông tin nằm ở ranh giới cắt.
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

# EMBEDDING_MODEL: Sử dụng all-MiniLM-L6-v2 (kích thước 384) vì nó nhẹ, tốc độ sinh vector nhanh,
# tài nguyên tính toán thấp, rất phù hợp chạy local trong môi trường kiểm thử mà vẫn giữ độ chính xác cao.
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# VECTOR_STORE: Chọn local json file thay thế cho chromadb vì chạy offline hoàn toàn dưới dạng file cục bộ (json),
# tránh triệt để lỗi biên dịch nhị phân HNSW và khoá SQLite trên nền tảng Windows.
VECTOR_STORE = "chromadb"


def load_documents() -> list[dict]:
    """
    Đọc toàn bộ markdown files từ data/standardized/.

    Returns:
        List of {'content': str, 'metadata': {'source': str, 'type': str}}
    """
    documents = []
    if not STANDARDIZED_DIR.exists():
        return documents

    for md_file in STANDARDIZED_DIR.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            doc_type = "legal" if "legal" in str(md_file.parent) else "news"
            documents.append({
                "content": content,
                "metadata": {"source": md_file.name, "type": doc_type}
            })
        except Exception as e:
            print(f"Error reading file {md_file}: {e}")
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """
    Chunk documents theo strategy đã chọn.

    Returns:
        List of {'content': str, 'metadata': dict} — mỗi item là 1 chunk
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = []
    for doc in documents:
        splits = splitter.split_text(doc["content"])
        for i, chunk_text in enumerate(splits):
            chunks.append({
                "content": chunk_text,
                "metadata": {
                    "source": doc["metadata"]["source"],
                    "type": doc["metadata"]["type"],
                    "chunk_index": i
                }
            })
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Embed toàn bộ chunks bằng model đã chọn.

    Returns:
        Mỗi chunk dict được thêm key 'embedding': list[float]
    """
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(EMBEDDING_MODEL)
    texts = [c["content"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=True)
    for chunk, emb in zip(chunks, embeddings):
        chunk["embedding"] = emb.tolist()
    return chunks


def index_to_vectorstore(chunks: list[dict]):
    """
    Lưu chunks vào vector store đã chọn (lưu cục bộ ra file JSON).
    """
    import json
    
    db_file = Path(__file__).parent.parent / "data" / "vector_store.json"
    db_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Chuẩn hoá cấu trúc metadata lưu trữ
    normalized_chunks = []
    for c in chunks:
        meta = {
            "source": c["metadata"]["source"],
            "doc_type": c["metadata"]["type"],
            "chunk_index": c["metadata"]["chunk_index"]
        }
        normalized_chunks.append({
            "content": c["content"],
            "embedding": c["embedding"],
            "metadata": meta
        })
        
    db_file.write_text(json.dumps(normalized_chunks, ensure_ascii=False, indent=2), encoding="utf-8")


def run_pipeline():
    """Chạy toàn bộ pipeline: load → chunk → embed → index."""
    print("=" * 50)
    print("Task 4: Chunking & Indexing")
    print(f"  Chunking: {CHUNKING_METHOD} (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    print(f"  Embedding: {EMBEDDING_MODEL} (dim={EMBEDDING_DIM})")
    print(f"  Vector Store: {VECTOR_STORE}")
    print("=" * 50)

    docs = load_documents()
    print(f"\n[OK] Loaded {len(docs)} documents")

    chunks = chunk_documents(docs)
    print(f"[OK] Created {len(chunks)} chunks")

    chunks = embed_chunks(chunks)
    print(f"[OK] Embedded {len(chunks)} chunks")

    index_to_vectorstore(chunks)
    print("[OK] Indexed to vector store")


if __name__ == "__main__":
    run_pipeline()
