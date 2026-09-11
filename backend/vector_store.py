"""
vector_store.py
Real embedding-based (semantic) retrieval for the Financial Literacy
Tutor Agent, replacing the earlier keyword-overlap matching.

How it works:
1. Each knowledge-base entry's text is converted into a numeric vector
   ("embedding") using Google's embedding model. Vectors that are
   semantically similar end up close together in this vector space,
   even if they share no words in common.
2. Embeddings for the knowledge base are computed once and cached to
   disk (data/kb_embeddings.json), so normal use doesn't re-call the
   embedding API for the same fixed knowledge base every time.
3. A user's question is embedded the same way, and compared against
   every cached knowledge-base embedding using cosine similarity.
   The closest matches are returned as context for the LLM to answer
   from -- the LLM still writes the actual answer; this only changes
   how relevant facts are found.

If no API key is configured, or an embedding call fails for any
reason (network issue, quota, etc.), retrieval falls back to the
original keyword-overlap method so the tutor keeps working.
"""

import os
import json
import math

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE_PATH = os.path.join(DATA_DIR, "kb_embeddings.json")
EMBED_MODEL = "gemini-embedding-001"

API_KEY = os.getenv("GEMINI_API_KEY")
_client = None
if API_KEY:
    try:
        from google import genai
        _client = genai.Client(api_key=API_KEY)
    except ImportError:
        _client = None


def _embed_texts(texts: list) -> list:
    if _client is None:
        raise RuntimeError("No Gemini API key configured")

    result = _client.models.embed_content(model=EMBED_MODEL, contents=texts)
    return [list(e.values) for e in result.embeddings]


def _cosine_similarity(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _load_cache():
    if not os.path.exists(CACHE_PATH):
        return None
    try:
        with open(CACHE_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _save_cache(cache: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f)


def _knowledge_base_signature(knowledge_base: list) -> str:
    joined = "|".join(f"{e['topic']}:{len(e['text'])}" for e in knowledge_base)
    return str(hash(joined))


def get_or_build_kb_embeddings(knowledge_base: list):
    signature = _knowledge_base_signature(knowledge_base)
    cache = _load_cache()

    if cache and cache.get("signature") == signature:
        return cache["embeddings"]

    texts = [f"{e['topic']}: {e['text']}" for e in knowledge_base]
    vectors = _embed_texts(texts)
    embeddings = {entry["topic"]: vec for entry, vec in zip(knowledge_base, vectors)}

    _save_cache({"signature": signature, "embeddings": embeddings})
    return embeddings


def semantic_retrieve(query: str, knowledge_base: list, top_k: int = 2):
    kb_embeddings = get_or_build_kb_embeddings(knowledge_base)
    query_vec = _embed_texts([query])[0]

    scored = [
        (_cosine_similarity(query_vec, kb_embeddings[entry["topic"]]), entry)
        for entry in knowledge_base
        if entry["topic"] in kb_embeddings
    ]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in scored[:top_k]]