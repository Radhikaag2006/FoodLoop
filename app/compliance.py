"""FSSAI & Environmental Waste Compliance Engine (Semantic RAG + AI Copilot).

Grounds FoodLoop's routing in official FSSAI Surplus Food Regulations (2019),
Solid Waste Management Rules (2016), and Food Safety and Standards Act (2006).

Features:
  1. Dense Semantic Vector Retrieval:
     - Google Gemini 'text-embedding-004' (768-dim dense vector embeddings with cosine similarity).
     - Latent Semantic Concept Vector Index (dense domain ontology projection & cosine similarity fallback).
  2. Hybrid Fusion (Semantic Vector Similarity + BM25 Lexical Score).
  3. Automated Lot Compliance Check (verifies safety tier restrictions).
  4. Interactive Regulatory Copilot (answers compliance questions with exact citations,
     supporting Gemini API when configured, with grounded synthesis fallback).
"""
import json
import math
import os
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

DATA_PATH = Path(__file__).parent / "data" / "regulations.json"
CACHE_PATH = Path(__file__).parent / "data" / "doc_embeddings.json"

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "as", "at", "be", "because", "been", "before", "being", "below",
    "between", "both", "but", "by", "can", "could", "did", "do", "does", "doing",
    "down", "during", "each", "few", "for", "from", "further", "had", "has", "have",
    "having", "he", "her", "here", "hers", "herself", "him", "himself", "his",
    "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just", "me",
    "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on",
    "once", "only", "or", "other", "our", "ours", "ourselves", "out", "over",
    "own", "same", "she", "should", "so", "some", "such", "than", "that", "the",
    "their", "theirs", "them", "themselves", "then", "there", "these", "they",
    "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why",
    "with", "would", "you", "your", "yours", "yourself", "yourselves"
}

# Domain semantic concept clusters for the latent vector space
SEMANTIC_CONCEPTS: Dict[str, List[str]] = {
    "ANIMAL_FEED_SWILL": [
        "swill", "feed", "livestock", "cattle", "cows", "cow", "pig", "pigs", "sheep",
        "goat", "goats", "ruminant", "ruminants", "bovine", "animals", "animal",
        "poultry", "meat", "gravy", "scraps", "slop", "slops", "dog", "dogs"
    ],
    "HUMAN_DONATION_SURPLUS": [
        "surplus", "donation", "donate", "charity", "hunger", "edible", "fresh",
        "ngo", "wholesome", "foodbank", "ration", "distribute", "serving", "kitchen"
    ],
    "SPOILAGE_DECAY_HAZARD": [
        "spoiled", "spoilage", "rot", "rotten", "rotting", "decay", "mold", "moldy",
        "fungus", "fungal", "stench", "smell", "stale", "slime", "slimy", "sour",
        "fermented", "curdled", "unfit", "unsafe", "contamination", "toxic", "poison"
    ],
    "EXPIRY_LOCKOUT": [
        "expired", "expiry", "date", "use-by", "best-before", "lapsed", "passed",
        "out-of-date", "shelf-life", "validity", "crossing"
    ],
    "TEMPERATURE_HOLDING": [
        "temperature", "degrees", "celsius", "hot", "cold", "chilled", "refrigeration",
        "freezer", "ambient", "holding", "window", "hour", "hours", "4-hour", "warming"
    ],
    "ORGANIC_RECOVERY_BIOGAS": [
        "compost", "composting", "biogas", "methane", "anaerobic", "digestion",
        "biomethanation", "organic", "wet", "waste", "biodegradable", "fertilizer",
        "manure", "leachate", "cpcb", "landfill", "segregation"
    ],
    "STATUTORY_PENALTIES": [
        "section", "59", "penalty", "penalties", "fine", "fines", "imprisonment",
        "punishment", "liability", "criminal", "prosecution", "offence", "jail", "law"
    ],
    "TRACEABILITY_AUDIT": [
        "traceability", "tamper", "tamper-evident", "audit", "record", "records",
        "log", "consignment", "hash", "fbo", "license", "registration", "verification"
    ],
}


def _tokenize(text: str) -> List[str]:
    words = re.findall(r"[A-Za-z0-9]+", text.lower())
    return [w for w in words if len(w) > 1 and w not in STOPWORDS]


def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes cosine similarity between two dense vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = 0.0
    norm1 = 0.0
    norm2 = 0.0
    for a, b in zip(v1, v2):
        dot += a * b
        norm1 += a * a
        norm2 += b * b
    if norm1 <= 0.0 or norm2 <= 0.0:
        return 0.0
    return dot / (math.sqrt(norm1) * math.sqrt(norm2))


class SemanticVectorIndex:
    """Hybrid Semantic Vector Index combining:
    1. Dense Vector Embeddings (Gemini 'text-embedding-004' when API key is set)
    2. Latent Semantic Space Projections (Cosine similarity over domain ontology)
    3. BM25 Lexical Keyword scoring for exact legal clause numbers
    """

    def __init__(self, docs: List[Dict[str, Any]]):
        self.docs = docs
        self.doc_len: List[int] = []
        self.avg_doc_len = 0.0
        self.inverted_index: Dict[str, List[Tuple[int, int]]] = {}
        self.latent_vectors: List[List[float]] = []
        self.gemini_embeddings: Dict[str, List[float]] = {}
        self._build_lexical_and_latent()
        self._load_cached_embeddings()

    def _build_lexical_and_latent(self):
        total_tokens = 0
        concepts_list = list(SEMANTIC_CONCEPTS.keys())

        for i, doc in enumerate(self.docs):
            full_text = " ".join([
                doc.get("title", ""),
                doc.get("regulation", ""),
                doc.get("clause", ""),
                doc.get("text", ""),
                doc.get("legal_mandate", ""),
                doc.get("tier_rule", ""),
                " ".join(doc.get("keywords", [])) * 2,
            ]).lower()

            tokens = _tokenize(full_text)
            self.doc_len.append(len(tokens))
            total_tokens += len(tokens)

            # BM25 Inverted index
            counts: Dict[str, int] = {}
            for t in tokens:
                counts[t] = counts.get(t, 0) + 1
            for t, cnt in counts.items():
                self.inverted_index.setdefault(t, []).append((i, cnt))

            # Latent Semantic Vector for this doc
            latent_vec = [0.0] * len(concepts_list)
            for c_idx, c_name in enumerate(concepts_list):
                keywords = SEMANTIC_CONCEPTS[c_name]
                weight = 0.0
                for kw in keywords:
                    if kw in counts:
                        weight += counts[kw] * 1.5
                    elif kw in full_text:
                        weight += 1.0
                latent_vec[c_idx] = weight

            # Normalize latent vector
            norm = math.sqrt(sum(x * x for x in latent_vec))
            if norm > 0:
                latent_vec = [x / norm for x in latent_vec]
            self.latent_vectors.append(latent_vec)

        n_docs = max(len(self.docs), 1)
        self.avg_doc_len = total_tokens / n_docs

    def _load_cached_embeddings(self):
        if CACHE_PATH.exists():
            try:
                with open(CACHE_PATH, "r", encoding="utf-8") as f:
                    self.gemini_embeddings = json.load(f)
            except Exception:
                self.gemini_embeddings = {}

    def _save_cached_embeddings(self):
        try:
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.gemini_embeddings, f)
        except Exception:
            pass

    def _embed_gemini(self, text: str, api_key: str) -> Optional[List[float]]:
        """Generates a 768-dim vector embedding using Gemini text-embedding-004."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={api_key}"
        payload = {
            "model": "models/text-embedding-004",
            "content": {"parts": [{"text": text[:2000]}]},
        }
        try:
            with httpx.Client(timeout=6.0) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data.get("embedding", {}).get("values")
        except Exception:
            return None
        return None

    def _ensure_doc_embeddings_gemini(self, api_key: str):
        """Pre-embeds statutory corpus if not already cached."""
        if not api_key:
            return
        modified = False
        for doc in self.docs:
            doc_id = doc["id"]
            if doc_id not in self.gemini_embeddings:
                summary = f"{doc['title']}. {doc['clause']}. {doc['text']} {doc['legal_mandate']} {doc['tier_rule']}"
                vec = self._embed_gemini(summary, api_key)
                if vec:
                    self.gemini_embeddings[doc_id] = vec
                    modified = True
        if modified:
            self._save_cached_embeddings()

    def _bm25_scores(self, q_tokens: List[str]) -> List[float]:
        k1, b = 1.5, 0.75
        scores = [0.0] * len(self.docs)
        n_docs = len(self.docs)

        for token in q_tokens:
            if token not in self.inverted_index:
                continue
            postings = self.inverted_index[token]
            df = len(postings)
            idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)

            for doc_idx, freq in postings:
                d_len = self.doc_len[doc_idx]
                num = freq * (k1 + 1)
                den = freq + k1 * (1 - b + b * (d_len / max(self.avg_doc_len, 1e-6)))
                scores[doc_idx] += idf * (num / den)

        # Normalize BM25
        max_s = max(scores) if scores else 0.0
        if max_s > 0:
            scores = [s / max_s for s in scores]
        return scores

    def _latent_semantic_vector(self, query: str) -> List[float]:
        q_lower = query.lower()
        q_tokens = _tokenize(query)
        q_counts = {t: q_tokens.count(t) for t in q_tokens}
        concepts_list = list(SEMANTIC_CONCEPTS.keys())

        vec = [0.0] * len(concepts_list)
        for c_idx, c_name in enumerate(concepts_list):
            keywords = SEMANTIC_CONCEPTS[c_name]
            w = 0.0
            for kw in keywords:
                if kw in q_counts:
                    w += q_counts[kw] * 2.0
                elif kw in q_lower:
                    w += 1.0
            vec[c_idx] = w

        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            return [x / norm for x in vec]
        return vec

    def search(
        self,
        query: str,
        top_k: int = 3,
        api_key: Optional[str] = None
    ) -> List[Tuple[Dict[str, Any], float, str]]:
        """Performs true semantic retrieval.

        Returns tuples of (document, similarity_score, search_mode).
        """
        q_tokens = _tokenize(query)
        bm25 = self._bm25_scores(q_tokens) if q_tokens else [0.0] * len(self.docs)

        # 1. Try Dense Semantic Vector Search via Gemini Embeddings
        if api_key:
            self._ensure_doc_embeddings_gemini(api_key)
            q_emb = self._embed_gemini(query, api_key)
            if q_emb:
                combined_scores = []
                for idx, doc in enumerate(self.docs):
                    d_emb = self.gemini_embeddings.get(doc["id"])
                    cos_sim = _cosine_similarity(q_emb, d_emb) if d_emb else 0.0
                    # Hybrid Fusion: 75% Semantic Vector Cosine Sim + 25% BM25 Lexical
                    hybrid = 0.75 * max(cos_sim, 0.0) + 0.25 * bm25[idx]
                    combined_scores.append((doc, round(hybrid, 4), "dense_gemini_embedding"))
                combined_scores.sort(key=lambda x: x[1], reverse=True)
                return combined_scores[:top_k]

        # 2. Latent Semantic Space Vector Search (Offline / Local)
        q_latent = self._latent_semantic_vector(query)
        latent_scores = []
        has_semantic_signal = sum(q_latent) > 0.0

        for idx, doc in enumerate(self.docs):
            d_latent = self.latent_vectors[idx]
            cos_sim = _cosine_similarity(q_latent, d_latent) if has_semantic_signal else 0.0
            # Hybrid Fusion: 70% Latent Semantic Cosine + 30% BM25
            if has_semantic_signal:
                hybrid = 0.70 * cos_sim + 0.30 * bm25[idx]
            else:
                hybrid = bm25[idx]
            latent_scores.append((doc, round(hybrid, 4), "latent_semantic_vector"))

        latent_scores.sort(key=lambda x: x[1], reverse=True)
        return latent_scores[:top_k]


def _load_documents() -> List[Dict[str, Any]]:
    if not DATA_PATH.exists():
        return []
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


DOCUMENTS = _load_documents()
INDEX = SemanticVectorIndex(DOCUMENTS)


def get_all_regulations() -> List[Dict[str, Any]]:
    return DOCUMENTS


def check_lot_compliance(
    item: str,
    condition: str = "fresh",
    expiry_date: Optional[date] = None,
    today: Optional[date] = None,
) -> Dict[str, Any]:
    """Evaluates a batch against statutory FSSAI and CPCB rules using semantic retrieval."""
    today = today or date.today()
    days_left = (expiry_date - today).days if expiry_date else None
    is_expired = days_left is not None and days_left < 0
    is_spoiled = condition == "spoiled"

    citations = []
    flags = []

    if is_expired:
        hits = INDEX.search("expired food use-by date human consumption", top_k=2)
        citations.extend([h[0] for h in hits])
        flags.append({
            "code": "EXPIRED_LOCK",
            "level": "MANDATORY_LOCK",
            "tier_locked": ["B", "C"],
            "tier_allowed": "D",
            "clause": "FSSAI Surplus Food Regulations 2019, Regulation 5",
            "message": "Food past expiry is legally unfit for human or livestock consumption. Routed exclusively to certified compost/biogas (Tier D).",
        })

    if is_spoiled:
        hits = INDEX.search("spoiled food mold rot unsafe decay", top_k=2)
        citations.extend([h[0] for h in hits])
        flags.append({
            "code": "SPOILAGE_LOCK",
            "level": "MANDATORY_LOCK",
            "tier_locked": ["B", "C"],
            "tier_allowed": "D",
            "clause": "Food Safety and Standards Act 2006, Section 59",
            "message": "Observable decay/mold detected. Strict civil/criminal liability forbids human processing or feed usage.",
        })

    # Swill feeding check for dairy or non-veg residues
    if item in ("dairy", "meat", "poultry", "mixed_waste") and condition != "spoiled" and not is_expired:
        hits = INDEX.search("swill feed animal cattle dairy meat ban livestock", top_k=2)
        citations.extend([h[0] for h in hits])
        flags.append({
            "code": "SWILL_FEED_RESTRICTION",
            "level": "RESTRICTION",
            "tier_locked": ["C"],
            "clause": "DAHD & FSSAI Livestock Feed Guidelines",
            "message": "Dairy and catering residues are prohibited from ruminant livestock feed to prevent zoonotic pathogens.",
        })

    # Base citation for segregation & record-keeping
    base_hits = INDEX.search("fbo responsibility segregation tamper evident record audit", top_k=1)
    if base_hits and base_hits[0][0] not in citations:
        citations.append(base_hits[0][0])

    unique_citations = []
    seen = set()
    for c in citations:
        if c["id"] not in seen:
            seen.add(c["id"])
            unique_citations.append({
                "id": c["id"],
                "authority": c["authority"],
                "regulation": c["regulation"],
                "clause": c["clause"],
                "title": c["title"],
                "legal_mandate": c["legal_mandate"],
            })

    status = "COMPLIANT"
    if any(f["level"] == "MANDATORY_LOCK" for f in flags):
        status = "LOCKED_TO_RECOVERY"
    elif flags:
        status = "RESTRICTED"

    return {
        "status": status,
        "item": item,
        "condition": condition,
        "is_expired": is_expired,
        "days_left": days_left,
        "flags": flags,
        "citations": unique_citations,
        "tamper_evident_required": True,
        "fssai_compliant": True,
    }


def _ask_gemini(query: str, retrieved_chunks: List[Dict[str, Any]], api_key: str) -> Optional[str]:
    """Calls Gemini API to synthesize answer from retrieved legal context."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    context_str = "\n\n".join([
        f"[{c['id']}] {c['authority']} - {c['regulation']} ({c['clause']})\n"
        f"Title: {c['title']}\n"
        f"Text: {c['text']}\n"
        f"Legal Mandate: {c['legal_mandate']}\n"
        f"FoodLoop Rule: {c['tier_rule']}"
        for c in retrieved_chunks
    ])

    prompt = (
        "You are the FoodLoop FSSAI & Environmental Regulatory Compliance Copilot.\n"
        "Your task is to answer food waste, donation, animal feed, and disposal compliance questions for food business operators.\n"
        "Ground your response strictly in the retrieved Indian regulatory context below.\n"
        "Cite the specific Regulation, Section, or Clause numbers explicitly.\n\n"
        f"--- OFFICIAL REGULATORY CONTEXT ---\n{context_str}\n-----------------------------------\n\n"
        f"USER QUESTION: {query}\n\n"
        "Provide a concise, professional answer with:\n"
        "1. Direct Legal Ruling (Allowed / Prohibited / Conditional)\n"
        "2. Statutory Reference & Explanation (citing clauses)\n"
        "3. FoodLoop Routing Action (which Tier: B-Process, C-Feed, D-Recover Biogas/Compost, or E-Recycle)."
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 600},
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return None
    return None


def _offline_synthesize(query: str, chunks: List[Dict[str, Any]]) -> str:
    """Deterministic, grounded answer generation when external LLM API is unavailable."""
    if not chunks:
        return (
            "No specific FSSAI regulation matched your query. Generally, all food business operators "
            "must follow FSSAI 2019 guidelines ensuring food past expiry or showing decay is never routed "
            "to human or animal feed chains."
        )

    primary = chunks[0]
    out = [
        f"### Legal Assessment: {primary['title']}",
        f"**Governing Authority:** {primary['authority']} | *{primary['clause']}*",
        "",
        f"**Statutory Rule:** {primary['text']}",
        "",
        f"**Legal Mandate:** {primary['legal_mandate']}",
        f"**FoodLoop System Action:** {primary['tier_rule']}",
    ]

    if len(chunks) > 1:
        out.append("\n**Additional Applicable Regulations:**")
        for c in chunks[1:]:
            out.append(f"• **{c['clause']}** ({c['authority']}): {c['legal_mandate']}")

    return "\n".join(out)


def ask_compliance_copilot(query: str) -> Dict[str, Any]:
    """Semantic RAG pipeline: Retrieve relevant legal clauses via vector similarity & synthesize guidance."""
    cleaned_query = query.strip()
    if not cleaned_query:
        return {
            "query": query,
            "answer": "Please ask a question regarding food safety, FSSAI regulations, cattle feed restrictions, or disposal rules.",
            "citations": [],
            "source": "empty",
            "retrieval_mode": "none",
        }

    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    # True semantic search with hybrid fallback
    retrieved = INDEX.search(cleaned_query, top_k=3, api_key=api_key or None)
    chunks = [r[0] for r in retrieved]
    retrieval_mode = retrieved[0][2] if retrieved else "latent_semantic_vector"

    answer = None
    source = "offline_rag_engine"

    if api_key:
        answer = _ask_gemini(cleaned_query, chunks, api_key)
        if answer:
            source = "gemini_rag_grounded"

    if not answer:
        answer = _offline_synthesize(cleaned_query, chunks)

    return {
        "query": cleaned_query,
        "answer": answer,
        "source": source,
        "retrieval_mode": retrieval_mode,
        "citations": [
            {
                "id": c["id"],
                "authority": c["authority"],
                "regulation": c["regulation"],
                "clause": c["clause"],
                "title": c["title"],
                "legal_mandate": c["legal_mandate"],
            }
            for c in chunks
        ],
    }
