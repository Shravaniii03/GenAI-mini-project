"""
rag_engine.py — MODULE 6: RAG + Local LLM Engine
══════════════════════════════════════════════════════════════════
Retrieval-Augmented Generation over automotive knowledge base.
Grounds LLM outputs in trusted VSS catalog, CAN database, ISO 26262 rules.

Eliminates hallucinations by retrieving relevant context before LLM calls.
Paper reference: RAG layer (Section II), Retrieve & Re-Rank methodology,
SentenceTransformer all-MiniLM-L6-v2 + cross-encoder ms-marco-MiniLM.

Simplified version: uses TF-IDF similarity (no GPU required).
For production: swap embedder with sentence-transformers.
"""

import json
import os
import math
import re
from pathlib import Path
from typing import Optional, Union
from llm_client import query_llm


# ──────────────────────────────────────────────────────────────────────
# Knowledge Base Loader
# ──────────────────────────────────────────────────────────────────────

_KB_PATH = Path("knowledge_base")
_CACHE: dict = {}


def _load_kb(filename: str) -> Union[dict, list]:
    """Load a knowledge base JSON file with caching."""
    if filename in _CACHE:
        return _CACHE[filename]
    path = _KB_PATH / filename
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    _CACHE[filename] = data
    return data


def load_vss_signals() -> list:
    data = _load_kb("vss_signals.json")
    return data.get("signals", []) if isinstance(data, dict) else []


def load_can_messages() -> list:
    data = _load_kb("can_messages.json")
    return data.get("messages", []) if isinstance(data, dict) else []


def load_iso_rules() -> list:
    data = _load_kb("iso26262_rules.json")
    if isinstance(data, dict):
        return data.get("timing_rules", []) + data.get("event_chain_rules", [])
    return []


def load_attack_patterns() -> list:
    data = _load_kb("attack_patterns.json")
    return data.get("attack_patterns", []) if isinstance(data, dict) else []


# ──────────────────────────────────────────────────────────────────────
# Simple TF-IDF based retrieval (no GPU / no external embedding models)
# For production: replace with sentence-transformers + FAISS
# ──────────────────────────────────────────────────────────────────────

def _tokenize(text: str) -> list:
    return re.findall(r'\w+', text.lower())


def _tfidf_score(query_tokens: list, doc_tokens: list, corpus: list) -> float:
    """Simple TF-IDF cosine-like score between query and document."""
    query_set = set(query_tokens)
    doc_set   = set(doc_tokens)
    overlap   = query_set & doc_set
    if not overlap:
        return 0.0

    score = 0.0
    N = len(corpus)
    for term in overlap:
        tf  = doc_tokens.count(term) / (len(doc_tokens) + 1)
        df  = sum(1 for d in corpus if term in d)
        idf = math.log((N + 1) / (df + 1)) + 1.0
        score += tf * idf

    # Normalize by query length
    return score / (len(query_tokens) + 1)


def _doc_to_text(item: dict, doc_type: str) -> str:
    """Convert knowledge base entry to searchable text."""
    if doc_type == "vss":
        return f"{item.get('path','')} {item.get('description','')} {item.get('unit','')}"
    elif doc_type == "can":
        signals = " ".join(s.get("name","") for s in item.get("signals",[]))
        return f"{item.get('name','')} {item.get('description','')} {signals} {item.get('sender','')} {item.get('id','')}"
    elif doc_type == "iso":
        return f"{item.get('name','')} {item.get('description','')} {item.get('component','')} {item.get('rule_id','')} {item.get('rule','')}"
    elif doc_type == "attack":
        chain = " ".join(item.get("attack_chain",[]))
        return f"{item.get('name','')} {item.get('description','')} {chain} {item.get('attack_vector','')}"
    return str(item)


def retrieve(query: str, doc_type: str, top_k: int = 5) -> list:
    """
    Retrieve top-k most relevant knowledge base entries for a query.
    doc_type: "vss" | "can" | "iso" | "attack"
    """
    loaders = {
        "vss":    load_vss_signals,
        "can":    load_can_messages,
        "iso":    load_iso_rules,
        "attack": load_attack_patterns
    }
    corpus_raw = loaders.get(doc_type, load_iso_rules)()
    if not corpus_raw:
        return []

    # Build text corpus
    corpus_texts = [_doc_to_text(item, doc_type) for item in corpus_raw]
    query_tokens = _tokenize(query)

    # Score all documents
    scores = [
        (i, _tfidf_score(query_tokens, _tokenize(text), corpus_texts))
        for i, text in enumerate(corpus_texts)
    ]
    scores.sort(key=lambda x: x[1], reverse=True)

    # Return top-k items
    return [corpus_raw[i] for i, score in scores[:top_k] if score > 0]


def retrieve_all(query: str, top_k: int = 3) -> dict:
    """Retrieve from all knowledge bases at once."""
    return {
        "vss_signals":    retrieve(query, "vss",    top_k),
        "can_messages":   retrieve(query, "can",    top_k),
        "iso_rules":      retrieve(query, "iso",    top_k),
        "attack_patterns": retrieve(query, "attack", top_k)
    }


# ──────────────────────────────────────────────────────────────────────
# RAG Context Builder
# ──────────────────────────────────────────────────────────────────────

def build_rag_context(query: str, top_k: int = 3) -> str:
    """
    Build a compact RAG context string to prepend to LLM prompts.
    Grounds the LLM in trusted automotive knowledge.
    """
    results = retrieve_all(query, top_k)
    lines = ["=== RAG CONTEXT (Automotive Knowledge Base) ==="]

    if results["iso_rules"]:
        lines.append("\nISO 26262 Rules:")
        for r in results["iso_rules"]:
            lines.append(f"  [{r.get('rule_id','?')}] {r.get('name','?')} — max {r.get('max_latency_ms','?')}ms | {r.get('component','?')}")

    if results["vss_signals"]:
        lines.append("\nRelevant VSS Signals:")
        for s in results["vss_signals"]:
            timing = f" (timing: {s['timing_constraint_ms']}ms)" if s.get("timing_constraint_ms") else ""
            lines.append(f"  {s.get('path','?')} [{s.get('type','?')}]{timing}")

    if results["can_messages"]:
        lines.append("\nRelevant CAN Messages:")
        for m in results["can_messages"]:
            lines.append(f"  {m.get('id','?')} {m.get('name','?')} — {m.get('description','?')[:60]}")

    if results["attack_patterns"]:
        lines.append("\nKnown Attack Patterns:")
        for a in results["attack_patterns"]:
            lines.append(f"  [{a.get('id','?')}] {a.get('name','?')} — {a.get('severity','?')} risk")

    lines.append("=== END RAG CONTEXT ===\n")
    return "\n".join(lines)


def rag_query(question: str, top_k: int = 3) -> str:
    """
    Full RAG pipeline: retrieve relevant context, then query LLM.
    Use for any automotive knowledge question.
    """
    context = build_rag_context(question, top_k)
    prompt = f"""
{context}

Based ONLY on the automotive knowledge above, answer this question:
{question}

Be precise. Reference specific rule IDs, signal paths, or CAN IDs from the context.
Plain text. Max 4 sentences.
"""
    return query_llm(prompt, temperature=0.2)


def get_iso_rule_for_component(component: str) -> Optional[dict]:
    """Quick lookup: get the most relevant ISO 26262 rule for a component."""
    rules = retrieve(component, "iso", top_k=1)
    return rules[0] if rules else None


def get_attack_patterns_for_component(component: str) -> list:
    """Get relevant attack patterns for a component."""
    return retrieve(component, "attack", top_k=3)


# ──────────────────────────────────────────────────────────────────────
# CLI test
# ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    query = sys.argv[1] if len(sys.argv) > 1 else "emergency brake timing ISO 26262"
    print(f"\n[RAG] Query: {query}")
    print("\n--- Retrieved Context ---")
    print(build_rag_context(query, top_k=2))
    print("\n--- RAG Answer ---")
    print(rag_query(query))