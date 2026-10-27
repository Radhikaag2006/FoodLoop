"""FSSAI & Environmental Waste Compliance Engine (RAG + AI Copilot).

Grounds FoodLoop's routing in official FSSAI Surplus Food Regulations (2019),
Solid Waste Management Rules (2016), and Food Safety and Standards Act (2006).

Features:
  1. Semantic BM25-based Retrieval of relevant legal clauses.
  2. Automated Lot Compliance Check (verifies safety tier restrictions).
  3. Interactive Regulatory Copilot (answers compliance questions with exact citations,
     supporting Gemini API when configured, with offline synthesis fallback).
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


def _tokenize(text: str) -> List[str]:
    words = re.findall(r"[A-Za-z0-9]+", text.lower())
    return [w for w in words if len(w) > 1 and w not in STOPWORDS]


class RegulatoryIndex:
    """In-memory BM25 index over FSSAI and CPCB statutory documents."""

    def __init__(self, docs: List[Dict[str, Any]]):
        self.docs = docs
        self.doc_len = []
        self.avg_doc_len = 0.0
        self.inverted_index: Dict[str, List[Tuple[int, int]]] = {}
        self._build()

    def _build(self):
        total_tokens = 0
        for i, doc in enumerate(self.docs):
            full_text = " ".join([
                doc.get("title", ""),
                doc.get("regulation", ""),
                doc.get("clause", ""),
                doc.get("text", ""),
                doc.get("legal_mandate", ""),
                doc.get("tier_rule", ""),
                " ".join(doc.get("keywords", [])) * 2,  # Boost keywords
            ])
            tokens = _tokenize(full_text)
            self.doc_len.append(len(tokens))
            total_tokens += len(tokens)

            counts: Dict[str, int] = {}
            for t in tokens:
                counts[t] = counts.get(t, 0) + 1
            for t, cnt in counts.items():
                self.inverted_index.setdefault(t, []).append((i, cnt))

        n_docs = max(len(self.docs), 1)
        self.avg_doc_len = total_tokens / n_docs

    def search(self, query: str, top_k: int = 3) -> List[Tuple[Dict[str, Any], float]]:
        q_tokens = _tokenize(query)
        if not q_tokens:
            return [(d, 1.0) for d in self.docs[:top_k]]

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

        ranked = sorted(
            [(self.docs[i], round(scores[i], 3)) for i in range(len(self.docs)) if scores[i] > 0],
            key=lambda x: x[1],
            reverse=True,
        )
        return ranked[:top_k] if ranked else [(d, 0.5) for d in self.docs[:top_k]]


def _load_documents() -> List[Dict[str, Any]]:
    if not DATA_PATH.exists():
        return []
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


DOCUMENTS = _load_documents()
INDEX = RegulatoryIndex(DOCUMENTS)


def get_all_regulations() -> List[Dict[str, Any]]:
    return DOCUMENTS


def check_lot_compliance(
    item: str,
    condition: str = "fresh",
    expiry_date: Optional[date] = None,
    today: Optional[date] = None,
) -> Dict[str, Any]:
    """Evaluates a batch against statutory FSSAI and CPCB rules."""
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
        hits = INDEX.search("spoiled food mold rot unsafe", top_k=2)
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
        hits = INDEX.search("swill feed animal cattle dairy meat ban", top_k=2)
        citations.extend([h[0] for h in hits])
        flags.append({
            "code": "SWILL_FEED_RESTRICTION",
            "level": "RESTRICTION",
            "tier_locked": ["C"],
            "clause": "DAHD & FSSAI Livestock Feed Guidelines",
            "message": "Dairy and catering residues are prohibited from ruminant livestock feed to prevent zoonotic pathogens.",
        })

    # Always cite baseline segregation & tamper-evident record keeping
    base_hits = INDEX.search("fbo responsibility segregation tamper evident record", top_k=1)
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
    """RAG pipeline: Retrieve relevant regulatory clauses and synthesize guidance."""
    cleaned_query = query.strip()
    if not cleaned_query:
        return {
            "query": query,
            "answer": "Please ask a question regarding food safety, FSSAI regulations, cattle feed restrictions, or disposal rules.",
            "citations": [],
            "source": "empty",
        }

    retrieved = INDEX.search(cleaned_query, top_k=3)
    chunks = [r[0] for r in retrieved]

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
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
