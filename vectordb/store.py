
from langchain_openai import OpenAIEmbeddings
from sqlalchemy import select
from langchain_core.documents import Document
from langchain_chroma import Chroma
from core.database import AsyncSessionLocal, Product
from config import CHROMA_DIR
from pathlib import Path
import asyncio
import numpy as np

embedder = OpenAIEmbeddings(model='text-embedding-3-small')

inventory_agent_db = None
inventory_agent_search = None

# In-memory mirror of the chromadb vectors, loaded once at startup.
# Runtime queries never touch chromadb (its sync SQLite query path
# deadlocks under the async server on Windows) — we do an async query
# embedding + pure-numpy cosine match instead.
_vec_matrix = None        # shape (n_products, dim), L2-normalized rows
_vec_metadatas = None     # list[dict] aligned with _vec_matrix rows
_search_cache = {}
_search_lock = None       # asyncio.Lock — created lazily inside the running loop


async def build_vector_store():
    global inventory_agent_db, inventory_agent_search
    global _vec_matrix, _vec_metadatas, _search_lock

    _search_lock = asyncio.Lock()

    # Pull the catalog from SQL once — used both to (re)build chromadb and
    # to construct the in-memory search matrix via async embeddings.
    catalog = []
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Product))
        products = result.scalars().all()
        for p in products:
            data = p.name + " " + p.category + " " + p.description + " " + str(p.unit_price)
            metadata = {
                "product_id": p.id,
                "name": p.name,
                "category": p.category,
                "unit_price": p.unit_price,
                "quantity": p.quantity,
            }
            catalog.append((data, metadata))

    if Path(CHROMA_DIR).exists():
        inventory_agent_db = Chroma(
            collection_name="store_inventory",
            embedding_function=embedder,
            persist_directory=CHROMA_DIR
        )
        inventory_agent_search = inventory_agent_db.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 3, "score_threshold": 0.2}
        )
        print("########### Vector Store Loaded From Disk #########")
    else:
        processed_docs = [
            Document(page_content=data, metadata=metadata)
            for data, metadata in catalog
        ]
        inventory_agent_db = Chroma.from_documents(
            documents=processed_docs,
            collection_name='store_inventory',
            embedding=embedder,
            collection_metadata={'hnsw:space': 'cosine'},
            persist_directory=CHROMA_DIR
        )
        inventory_agent_search = inventory_agent_db.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 3, "score_threshold": 0.2}
        )
        print("########### Vector Store Established #########")

    # Build the in-memory search matrix with the ASYNC embedder (this path
    # never blocks the event loop). No chromadb get/query is ever called
    # from inside the running loop — that is what was deadlocking.
    texts = [data for data, _ in catalog]
    embeddings = np.asarray(
        await embedder.aembed_documents(texts), dtype=np.float32
    )
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    _vec_matrix = embeddings / norms
    _vec_metadatas = [metadata for _, metadata in catalog]
    print(f"########### Search vectors cached in memory ({_vec_matrix.shape}) #########")


async def semantic_search(query: str):
    if query in _search_cache:
        return _search_cache[query]

    async with _search_lock:
        if query in _search_cache:
            return _search_cache[query]

        # Async embedding (this path never hangs); 15s ceiling as a guard.
        q_emb = await asyncio.wait_for(embedder.aembed_query(query), timeout=15.0)
        q = np.asarray(q_emb, dtype=np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            q_norm = 1.0
        q = q / q_norm

        # Pure in-memory cosine similarity — microseconds, no chromadb.
        sims = _vec_matrix @ q
        top_idx = np.argsort(-sims)[:3]
        result = [
            _vec_metadatas[i]
            for i in top_idx
            if sims[i] >= 0.2
        ]
        _search_cache[query] = result
        return result
