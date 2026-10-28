"""FSSAI & Environmental Waste Compliance Engine (Semantic RAG + Personal Assistant).

Grounds FoodLoop's routing in official FSSAI Surplus Food Regulations (2019),
Solid Waste Management Rules (2016), and Food Safety and Standards Act (2006).

Features:
  1. Dense Semantic Vector Retrieval:
     - Google Gemini 'text-embedding-004' (768-dim dense vector embeddings with cosine similarity).
     - Latent Semantic Concept Vector Index (dense domain ontology projection & cosine similarity fallback).
  2. Hybrid Fusion (Semantic Vector Similarity + BM25 Lexical Score).
  3. Automated Lot Compliance Check (verifies safety tier restrictions).
  4. Interactive Regulatory Personal Assistant (answers compliance questions with exact citations,
     supporting Gemini API when configured, with grounded synthesis fallback).
"""
import json
import math
import os
import re
import unicodedata
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
    "GAUSHALA_ROTI_FEED": [
        "roti", "rotis", "chapati", "chapatis", "phulka", "paratha", "naan", "puri",
        "gaushala", "goshala", "cow", "cows", "bovine", "cattle", "bread", "wheat",
        "atta", "maida", "grain", "grains", "cereal", "chawal", "rice", "dalia"
    ],
    "INDIC_COOKED_DISHES": [
        "dal", "sabzi", "curry", "gravy", "paneer", "sambar", "rasam", "khoya",
        "mithai", "halwai", "dhaba", "langar", "prasad", "bhog", "annadhanam"
    ],
    "ANIMAL_FEED_SWILL": [
        "swill", "feed", "livestock", "cattle", "cows", "cow", "pig", "pigs", "sheep",
        "goat", "goats", "ruminant", "ruminants", "bovine", "animals", "animal",
        "poultry", "meat", "gravy", "scraps", "slop", "slops", "dog", "dogs",
        "roti", "rotis", "chapati", "gaushala", "goshala"
    ],
    "HUMAN_DONATION_SURPLUS": [
        "surplus", "donation", "donate", "charity", "hunger", "edible", "fresh",
        "ngo", "wholesome", "foodbank", "ration", "distribute", "serving", "kitchen",
        "langar", "prasad", "bhog", "annadhanam"
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
    "COOKING_OIL_BIODIESEL": [
        "cooking", "oil", "used", "fryer", "ruco", "tpc", "polar", "compounds",
        "grease", "drain", "sewage", "biodiesel", "biofuel", "re repurpose"
    ],
    "PACKAGING_DE_PACKAGING": [
        "packaging", "plastic", "plastics", "de-packaging", "wrapper", "wrappers",
        "foil", "bottle", "bottles", "sachet", "polybag", "microplastic", "pouch"
    ],
    "COLD_CHAIN_LOGISTICS": [
        "cold", "chain", "reefer", "transit", "truck", "frozen", "chill",
        "breach", "temperature-abused", "schedule", "iv"
    ],
    "BULK_WASTE_GENERATOR": [
        "bulk", "waste", "generator", "bwg", "100kg", "100", "kg", "ban",
        "on-site", "complex", "hotel", "banquet", "mall"
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

# ---- plain-language summaries and extra search words (separate data files) ----
SUMMARY_PATH = Path(__file__).parent / "data" / "answer_summaries.json"
TERMS_PATH = Path(__file__).parent / "data" / "hindi_terms.json"


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


SUMMARIES: Dict[str, Dict[str, Any]] = {
    k: v for k, v in _load_json(SUMMARY_PATH).items() if not k.startswith("_")}


def _with_search_words(doc: Dict[str, Any]) -> Dict[str, Any]:
    """The same regulation, plus the extra words people use to ask about it."""
    extra = SUMMARIES.get(doc.get("id", ""), {}).get("extra_keywords", [])
    return dict(doc, keywords=list(doc.get("keywords", [])) + list(extra))


INDEX = SemanticVectorIndex([_with_search_words(d) for d in DOCUMENTS])


# ---- Hindi / Hinglish / Devanagari understanding ----
def _norm_dev(text: str) -> str:
    """Lower-case, and fold spellings that vary in Devanagari (nukta, chandrabindu)."""
    t = unicodedata.normalize("NFC", text.lower())
    t = t.replace("\u093c", "")                 # nukta: ज़ -> ज, ड़ -> ड
    return t.replace("\u0901", "\u0902")        # chandrabindu -> anusvara


_TOKEN_RE = re.compile(r"[a-z0-9]+|[\u0900-\u097f]+")


def _words(text: str) -> List[str]:
    return _TOKEN_RE.findall(_norm_dev(text))


def _load_terms() -> Dict[str, Any]:
    raw = _load_json(TERMS_PATH)
    norm = lambda d: {_norm_dev(k): v for k, v in d.items()}
    phrases = {tuple(_words(k)): v for k, v in raw.get("phrases", {}).items()}
    return {
        "terms": norm(raw.get("terms", {})),
        "prefixes": norm(raw.get("prefixes", {})),
        "phrases": phrases,
        "markers": {_norm_dev(m) for m in raw.get("hinglish_markers", [])},
        "greetings": {_norm_dev(g) for g in raw.get("greetings", [])},
    }


TERMS = _load_terms()
_DEVANAGARI = re.compile(r"[\u0900-\u097f]")


def expand_query(query: str) -> Tuple[str, bool]:
    """Add the English terms behind Hindi/Hinglish words to a question.

    Returns (question + added English terms, whether it is a Hindi question)."""
    words = _words(query)
    adds: List[str] = []
    for i in range(len(words)):                       # whole phrases first
        for phrase, en in TERMS["phrases"].items():
            n = len(phrase)
            if n and tuple(words[i:i + n]) == phrase:
                adds += en
    for w in words:
        adds += TERMS["terms"].get(w, [])
        for pre, en in TERMS["prefixes"].items():
            if w.startswith(pre):
                adds += en
    hindi = bool(_DEVANAGARI.search(query)) or any(w in TERMS["markers"] for w in words)
    return (query + " " + " ".join(dict.fromkeys(adds))).strip(), hindi


# Words that on their own do not make a question about food waste.
WEAK_TERMS = {
    "food", "eat", "date", "hot", "cold", "used", "wet", "hour", "hours", "law", "section",
    "kg", "100", "59", "chain", "log", "record", "records", "window", "kitchen", "complex",
    "cooking", "time", "old", "dry", "iv", "ban", "wheat", "meat", "oil", "cooked",
    "bad", "burnt", "frying", "fryer", "fried", "delivery",
}
# Everyday words that are clearly about this subject.
EXTRA_DOMAIN_TERMS = {
    "milk", "curd", "yogurt", "ghee", "butter", "cheese", "vegetable", "vegetables", "fruit", "fruits",
    "leftover", "leftovers", "dal", "rice", "sweets", "donate", "donation", "expired", "expiry", "expire",
    "stale", "spoiled", "spoil", "rotten", "mold", "mould", "fungus", "penalty", "licence", "license",
    "fssai", "restaurant", "catering", "banquet", "plastic", "landfill", "compost", "biogas", "dustbin",
    "garbage", "trash", "gaushala", "unfit", "biodiesel", "swill", "surplus", "bakery", "bread", "roti",
    "chapati", "cow", "cattle", "livestock", "temple", "prasad", "langar", "sachet", "polythene",
    "bad", "burnt", "frying", "fryer", "fried", "delivery",
}
# Shopping, recipes and similar: not a question about the rules unless a real concern is also raised.
OFF_INTENT = {
    "price", "prices", "cost", "buy", "buying", "brand", "brands", "best", "cheap", "recipe", "recipes",
    "ingredients", "calories", "calorie", "nutrition", "diet", "vitamin", "protein", "benefits",
    "weather", "movie", "song", "cricket", "score",
}


# What the assistant is for: a question is on topic when it raises one of these concerns
# (condition, donation, animal feed, disposal, penalties, storage, transport, records ...).
# A food name on its own ("dal", "milk") is not a question about the rules.
CONCERN_TERMS = {
    "expired", "expiry", "expire", "stale", "spoiled", "spoil", "spoilage", "rotten", "rot", "mold", "mould",
    "fungus", "fungal", "unfit", "smell", "insect", "infestation", "unsafe", "contamination", "contaminated",
    "donate", "donation", "distribute", "sell", "surplus", "leftover", "leftovers", "swill", "ngo", "charity",
    "waste", "garbage", "trash", "dispose", "disposal", "dump", "landfill", "drain", "dustbin", "compost",
    "biogas", "biodiesel", "segregate", "segregation", "decay",
    "feed", "cattle", "cow", "bovine", "livestock", "animal", "gaushala", "goshala", "buffalo", "goat",
    "sheep", "pig", "poultry",
    "penalty", "penalties", "fine", "punishment", "imprisonment", "prosecution", "liability", "offence",
    "licence", "license", "registration", "fbo", "fssai", "regulation", "regulations", "cpcb", "spcb",
    "packaging", "plastic", "sachet", "polythene", "wrapper",
    "temperature", "holding", "storage", "refrigeration", "chilled", "reefer", "transit", "tamper",
    "traceability", "audit", "bulk", "bwg", "municipal", "tpc", "ruco", "uco",
    "melted", "thawed", "frozen", "froze", "spoilt", "sold", "selling",
}


# Concerns strong enough to keep a question on topic even if it also mentions a price or a recipe.
CORE_CONCERNS = {
    "expired", "expiry", "expire", "stale", "spoiled", "spoil", "spoilage", "rotten", "mold", "mould", "fungus",
    "donate", "donation", "surplus", "leftover", "leftovers", "swill", "waste", "garbage", "dispose", "disposal",
    "compost", "biogas", "landfill", "feed", "cattle", "livestock", "gaushala", "penalty", "penalties",
    "punishment", "licence", "license", "fssai", "unsafe", "contaminated",
}


def _domain_terms() -> set:
    vocab = set(EXTRA_DOMAIN_TERMS)
    for words in SEMANTIC_CONCEPTS.values():
        vocab.update(words)
    for d in INDEX.docs:
        for kw in d.get("keywords", []):
            vocab.update(_tokenize(kw))
    return {w for w in vocab if w not in STOPWORDS}


DOMAIN_TERMS = _domain_terms()


def _stems(t: str):
    yield t
    if t.endswith("es"):
        yield t[:-2]
    if t.endswith("s"):
        yield t[:-1]
    if t.endswith("ing"):
        yield t[:-3]
        yield t[:-3] + "e"
    if t.endswith("ed"):
        yield t[:-2]
        yield t[:-1]


def is_in_scope(expanded_query: str) -> bool:
    """True when the question is about food safety, surplus, feed, expiry or waste.

    One concern word (expired, donate, cattle, penalty, dispose ...) is enough. Generic
    words (date, hot, section ...) only count when there are at least two of them, and a
    food name on its own does not make a question about the rules."""
    concern, weak = False, set()
    tokens = _tokenize(expanded_query)
    shopping = any(t in OFF_INTENT for t in tokens)
    for t in tokens:
        for st in _stems(t):
            if st in CONCERN_TERMS:
                concern = True
                break
            if st in DOMAIN_TERMS and (st in WEAK_TERMS or t in WEAK_TERMS):
                weak.add(t)
                break
    if shopping and not any(
            st in CORE_CONCERNS for t in tokens for st in _stems(t)):
        return False
    return concern or len(weak) >= 2


def _is_greeting(query: str) -> bool:
    words = _words(query)
    return bool(words) and all(w in TERMS["greetings"] for w in words)


OUT_OF_SCOPE = {
    "en": ("That's outside what I can help with. I answer questions about food safety, surplus food "
           "donation, animal feed, expired or spoiled food, waste disposal and FSSAI rules in India.\n\n"
           "For example: \"Can expired bread go to cattle feed?\" or \"What is the penalty under FSSAI Section 59?\""),
    "hi": ("यह सवाल मेरे दायरे से बाहर है। मैं खाद्य सुरक्षा, बचा हुआ खाना दान करने, पशु चारा, एक्सपायर्ड या ख़राब खाना, "
           "कचरा निपटान और भारत में FSSAI के नियमों से जुड़े सवालों के जवाब देता हूँ।\n\n"
           "जैसे: \"बासी रोटी गाय को खिला सकते हैं?\" या \"FSSAI धारा 59 में जुर्माना कितना है?\""),
}
GREETING = {
    "en": ("Hello! I can help with food safety, surplus food, animal feed, expired or spoiled food, waste "
           "disposal and FSSAI rules. What would you like to know?"),
    "hi": ("नमस्ते! मैं खाद्य सुरक्षा, बचा हुआ खाना, पशु चारा, एक्सपायर्ड या ख़राब खाना, कचरा निपटान और FSSAI के "
           "नियमों में आपकी मदद कर सकता हूँ। आप क्या जानना चाहते हैं?"),
}


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


def _ask_gemini(query: str, retrieved_chunks: List[Dict[str, Any]], api_key: str,
                hindi: bool = False) -> Optional[str]:
    """Calls Gemini API to synthesize answer from retrieved legal context with deep Indic culinary fluency."""
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
        "You are the FoodLoop FSSAI & Environmental Regulatory Personal Assistant for Indian Food Businesses.\n"
        "You understand everyday Indian food, catering, and business terms:\n"
        "- Roti, chapati, phulka, paratha, naan, bread, chawal (rice), dalia, grains\n"
        "- Gaushala, goshala (bovine cattle shelter), cows, buffaloes\n"
        "- Dal, sabzi, curry, gravy, paneer, sambar, khoya, mithai, halwai, dhaba, langar, prasad\n\n"
        "Your task is to answer food safety, surplus donation, animal feed, and waste compliance questions.\n"
        "Ground your advice strictly in the official Indian statutory regulations retrieved below.\n\n"
        f"--- OFFICIAL REGULATORY CONTEXT ---\n{context_str}\n-----------------------------------\n\n"
        f"USER INQUIRY: {query}\n\n"
        "Instructions:\n"
        "0. Answer ONLY the question asked, in plain words, in at most 150 words, with no markdown headings. "
        "If the context does not answer it, say so briefly instead of guessing. "
        + ("Reply in simple Hindi written in Devanagari script. " if hindi else "Reply in English. ") + "\n"
        "1. Give a direct, plain-language ruling in your opening sentence. If asked about feeding rotis to cows/gaushalas, say clearly whether it is permitted (Yes, if clean and mold-free), and under what specific safety conditions.\n"
        "2. Explain the safety requirements (e.g. rotis must be dry, not moldy/aflatoxin-contaminated, and not soaked with spicy/oily dal/curry or non-veg swill).\n"
        "3. Cite the exact Regulation, Section, or Clause numbers from the context.\n"
        "4. State the explicit FoodLoop Routing Action (Tier C - Feed vs Tier D - Biogas/Compost)."
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


def _is_roti_cow_question(q_lower: str) -> bool:
    return (any(k in q_lower for k in ("roti", "rotis", "chapati", "chapatis", "phulka", "bread", "atta"))
            and any(k in q_lower for k in ("cow", "cows", "gaushala", "goshala", "cattle", "feed")))


def _offline_synthesize(query: str, chunks: List[Dict[str, Any]], hindi: bool = False) -> str:
    """A grounded answer: the short answer first, then why, then what FoodLoop does."""
    if not chunks:
        return OUT_OF_SCOPE["hi" if hindi else "en"]

    primary = chunks[0]
    info = SUMMARIES.get(primary["id"], {})

    if hindi:
        short = info.get("short_hi")
        if short:
            lines = [f"संक्षिप्त उत्तर: {short}", ""]
            if info.get("action_hi"):
                lines.append(f"FoodLoop में क्या होता है: {info['action_hi']}")
            lines.append(f"नियम: {primary['clause']} ({primary['authority']})")
            return "\n".join(lines)
        # no Hindi text for this rule: fall through to the English answer

    # keep the detailed roti / gaushala ruling as it was
    if not hindi and _is_roti_cow_question(query.lower()):
        return (
            "Legal Ruling: Roti & Grain Donation to Gaushalas (Permitted with Conditions)\n\n"
            "Yes, clean vegetarian rotis, chapatis, and bakery grains CAN be donated to registered Gaushalas "
            "(cattle shelters) and dairy farms under FoodLoop Tier C (Animal Feed).\n\n"
            "Statutory Grounding: FSSAI & DAHD Livestock Feed Advisory (Clause 4.2)\n\n"
            "Key Compliance Requirements:\n"
            "• Must Be Mold-Free: Rotis must be dry and free from fungal mold (Rhizopus or Aspergillus). "
            "Moldy grains produce toxic aflatoxins that are lethal to cattle and illegal to distribute.\n"
            "• No Oily Curries / Catering Gravy: Rotis must NOT be soaked in spicy dal, sabzi, or non-vegetarian "
            "gravies. Such oily catering swill triggers fatal rumen acidosis in cattle.\n"
            "• Proper Segregation: Collect dry rotis in clean, ventilated containers within 12–24 hours of baking.\n\n"
            "FoodLoop Routing Action:\n"
            "• Clean, dry rotis/chapatis ➔ Tier C (Gaushala / Cattle Feed)\n"
            "• Moldy, wet, or curry-soaked rotis ➔ Tier D (Biogas / Composting)"
        )

    # The direct answer first, then the rule's own wording so the answer can be checked against it.
    short = info.get("short") or primary["text"]
    out = [f"Short answer: {short}", ""]
    if info.get("short"):
        out += [f"The rule says: {primary['text']}", ""]
    out += [
        f"Why: {primary['legal_mandate']}",
        f"What FoodLoop does: {primary['tier_rule']}",
        f"Source: {primary['clause']} ({primary['authority']})",
    ]
    if len(chunks) > 1:
        out.append("\nAlso relevant:")
        for c in chunks[1:]:
            out.append(f"• {c['clause']} ({c['authority']}): {c['legal_mandate']}")
    return "\n".join(out)


def _result(query: str, answer: str, source: str, mode: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "query": query,
        "answer": answer,
        "source": source,
        "retrieval_mode": mode,
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


def ask_compliance_copilot(query: str) -> Dict[str, Any]:
    """Semantic RAG pipeline: understand the question (English, Hinglish or Hindi), stay in scope,
    retrieve the relevant legal clauses and answer directly."""
    cleaned_query = query.strip()
    if not cleaned_query:
        return {
            "query": query,
            "answer": "Please ask a question regarding food safety, FSSAI regulations, cattle feed restrictions, or disposal rules.",
            "citations": [],
            "source": "empty",
            "retrieval_mode": "none",
        }

    expanded, hindi = expand_query(cleaned_query)
    lang = "hi" if hindi else "en"

    if _is_greeting(cleaned_query):
        return _result(cleaned_query, GREETING[lang], "greeting", "none", [])
    if not is_in_scope(expanded):
        return _result(cleaned_query, OUT_OF_SCOPE[lang], "out_of_scope", "none", [])

    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    # True semantic search with hybrid fallback (on the question plus the English terms behind it)
    retrieved = INDEX.search(expanded, top_k=3, api_key=api_key or None)
    best = retrieved[0][1] if retrieved else 0.0
    chunks = [r[0] for i, r in enumerate(retrieved) if i == 0 or r[1] >= 0.5 * best]
    retrieval_mode = retrieved[0][2] if retrieved else "latent_semantic_vector"

    answer = None
    source = "offline_rag_engine"

    if api_key:
        answer = _ask_gemini(cleaned_query, chunks, api_key, hindi)
        if answer:
            source = "gemini_rag_grounded"

    if not answer:
        answer = _offline_synthesize(expanded, chunks, hindi)

    return _result(cleaned_query, answer, source, retrieval_mode, chunks)
