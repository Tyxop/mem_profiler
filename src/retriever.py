import re
from .graph_db import GraphMemory
from .llm_client import LMStudioClient
from .models import ContextResponse


def _triples_to_compact(triples: list[dict]) -> str:
    lines = [
        f"({t['subject']}) --[{t['predicate']}]--> ({t['object']})"
        for t in triples
    ]
    return "\n".join(lines)


def _tokenize_query(query: str) -> list[str]:
    """Split query into search terms, removing stopwords."""
    stopwords = {"el", "la", "los", "las", "un", "una", "de", "que", "en",
                 "y", "a", "es", "su", "con", "por", "para", "como", "mi",
                 "me", "se", "del", "al", "le", "the", "is", "my", "a"}
    words = re.findall(r"\w+", query.lower())
    return [w for w in words if w not in stopwords and len(w) > 2]


class Retriever:
    def __init__(self, graph: GraphMemory, llm: LMStudioClient):
        self.graph = graph
        self.llm = llm

    def retrieve(self, query: str, max_hops: int = 2, max_nodes: int = 15) -> ContextResponse:
        terms = _tokenize_query(query)
        seed_names: list[str] = []
        for term in terms:
            found = self.graph.search_nodes(term, limit=3)
            for name in found:
                if name not in seed_names:
                    seed_names.append(name)
            if len(seed_names) >= max_nodes:
                break

        if not seed_names:
            return ContextResponse(
                context="No se encontró información relevante en la memoria.",
                triples_found=0,
                nodes=[],
                raw_triples=[],
            )

        triples = self.graph.get_neighborhood(seed_names[:max_nodes], hops=max_hops)

        # Trim to max_nodes worth of triples
        triples = triples[: max_nodes * 3]

        compact = _triples_to_compact(triples)
        summary = self.llm.build_context_summary(query, triples) if triples else ""

        all_nodes = list({t["subject"] for t in triples} | {t["object"] for t in triples})

        return ContextResponse(
            context=summary or compact,
            triples_found=len(triples),
            nodes=all_nodes,
            raw_triples=triples,
        )
