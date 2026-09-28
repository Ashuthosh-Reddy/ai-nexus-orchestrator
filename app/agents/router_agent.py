"""Intelligent Router Agent that classifies user queries to the right domain model."""
import asyncio
from app.config import MODEL_DOMAINS, settings
from app.llm_client import call_llm


ROUTER_SYSTEM_PROMPT = """You are an intelligent AI query router. Your job is to classify a user's query
and determine which specialized AI model should handle it.

Available models:
1. code_generator - For generating code, implementing features, building modules, writing scripts
2. test_engineer - For creating tests, test specifications, QA, verification, test cases
3. doc_analyzer - For analyzing documents, summarizing text, extracting insights, reviewing specs
4. data_analytics - For data analysis, creating charts, statistics, visualizations, working with datasets
5. general_qa - For general questions, factual information, explanations, conversational queries

Rules:
- Respond with ONLY the model ID (e.g., "code_generator") — nothing else
- Choose the BEST matching model based on the user's intent
- Use "general_qa" for: factual questions (who/what/when/where), definitions, explanations, general knowledge
- If the query mentions both code and tests, choose "test_engineer" (testing is the primary intent)
- If unsure between technical vs general, prefer the technical model
"""


def keyword_classify(query: str) -> tuple[str, float]:
    """Fast keyword-based classification as primary or fallback."""
    query_lower = query.lower()
    scores: dict[str, int] = {}

    # Boost for uploaded files — detect file markers
    has_uploaded_file = "--- uploaded file:" in query_lower
    file_ext = ""
    if has_uploaded_file:
        import re
        ext_match = re.search(r'--- uploaded file:.*?\.(\w+)', query_lower)
        if ext_match:
            file_ext = ext_match.group(1)

    for domain_id, domain in MODEL_DOMAINS.items():
        score = 0
        for keyword in domain["keywords"]:
            if keyword in query_lower:
                score += len(keyword)  # Longer matches = higher confidence
        scores[domain_id] = score

    # Boost doc_analyzer for uploaded text/document files
    if has_uploaded_file and file_ext in ("txt", "md", "pdf", "log", "conf", "xml", "html"):
        scores["doc_analyzer"] = scores.get("doc_analyzer", 0) + 20

    # Boost data_analytics for data files
    if has_uploaded_file and file_ext in ("csv", "json", "yaml", "yml"):
        scores["data_analytics"] = scores.get("data_analytics", 0) + 20

    # Boost doc_analyzer for image files
    if has_uploaded_file and file_ext in ("png", "jpg", "jpeg", "gif", "bmp", "webp", "svg"):
        scores["doc_analyzer"] = scores.get("doc_analyzer", 0) + 20

    # Boost code analysis for code files
    if has_uploaded_file and file_ext in ("py", "js", "ts", "java", "go", "rs", "c", "cpp"):
        scores["doc_analyzer"] = scores.get("doc_analyzer", 0) + 15

    if not scores or max(scores.values()) == 0:
        return "code_generator", 0.3

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    confidence = scores[best] / total if total > 0 else 0.3
    return best, round(confidence, 2)


async def route_query(query: str) -> dict:
    """Route a user query to the best domain model.
    
    Uses fast keyword classification (instant, no LLM call needed).
    This eliminates the 30-60s routing delay from the previous LLM-based router.
    """
    keyword_model, keyword_confidence = keyword_classify(query)
    selected = keyword_model
    confidence = max(keyword_confidence, 0.65)  # Floor confidence at 65%
    method = "keyword"

    domain = MODEL_DOMAINS[selected]
    return {
        "selected_model": selected,
        "model_name": domain["name"],
        "model_description": domain["description"],
        "confidence": confidence,
        "method": method,
    }
