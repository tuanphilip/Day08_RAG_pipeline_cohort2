"""
Task 5 — Semantic Search Module.

Viết module tìm kiếm ngữ nghĩa (dense retrieval) trên vector store.
"""


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Tìm kiếm ngữ nghĩa sử dụng vector similarity (Cosine similarity tính trên local JSON file).

    Args:
        query: Câu truy vấn
        top_k: Số lượng kết quả tối đa

    Returns:
        List of {
            'content': str,      # Nội dung chunk
            'score': float,      # Cosine similarity score
            'metadata': dict     # source, doc_type, chunk_index
        }
        Sorted by score descending.
    """
    import json
    import numpy as np
    from pathlib import Path
    from sentence_transformers import SentenceTransformer

    db_file = Path(__file__).parent.parent / "data" / "vector_store.json"
    if not db_file.exists():
        return []

    try:
        chunks = json.loads(db_file.read_text(encoding="utf-8"))
    except Exception:
        return []

    if not chunks:
        return []

    # Khởi tạo mô hình và mã hoá query
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    query_embedding = model.encode(query)
    query_norm = np.linalg.norm(query_embedding)

    results = []
    for c in chunks:
        emb = np.array(c["embedding"])
        emb_norm = np.linalg.norm(emb)
        
        if query_norm == 0.0 or emb_norm == 0.0:
            sim = 0.0
        else:
            sim = float(np.dot(query_embedding, emb) / (query_norm * emb_norm))

        results.append({
            "content": c["content"],
            "score": sim,
            "metadata": {
                "source": c["metadata"].get("source"),
                "type": c["metadata"].get("doc_type"),
                "chunk_index": c["metadata"].get("chunk_index")
            }
        })

    # Sắp xếp giảm dần theo điểm tương đồng cosine
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


if __name__ == "__main__":
    # Test
    results = semantic_search("hình phạt cho tội tàng trữ ma tuý", top_k=5)
    for r in results:
        print(f"[{r['score']:.3f}] {r['content'][:100]}...")
