import json
import re
from .graph_db import GraphMemory
from .llm_client import LMStudioClient
from .models import ContextResponse

INTENT_PROMPT = """Analiza este mensaje y extrae información para buscar en un grafo de memoria personal.

El grafo tiene nodos con nombres reales (ej: "Madrid", "Toby", "Usuario") y tipos: PERSONA, LUGAR, MASCOTA, HOBBIE, CONDICION, ESTADO, TRABAJO, COMIDA, FECHA, ENTIDAD.
Las relaciones (predicados) son: VIVE_EN, TIENE_MASCOTA, PREFIERE, TRABAJA_EN, TIENE_ESTADO, CONOCE, ES_UN, TIENE_CARACTERISTICA, REALIZA, etc.

Devuelve SOLO un JSON válido con:
- "seeds": nombres de nodos a buscar directamente (siempre incluye "Usuario" si la pregunta es personal)
- "predicates": predicados relevantes para filtrar
- "types": tipos de nodo que podrían contener la respuesta
- "is_personal": true si la pregunta es sobre el propio usuario

Mensaje: """

CONTEXT_PROMPT = """Dado este subgrafo de memoria, genera un resumen de 1-2 líneas conciso para responder la consulta.
Si no hay información relevante, devuelve exactamente la cadena: NO_INFO

Consulta: {query}

Grafo:
{triples}

Resumen (o NO_INFO):"""


def _parse_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {}


def _triples_to_text(triples: list[dict]) -> str:
    return "\n".join(
        f"({t['subject']}) --[{t['predicate']}]--> ({t['object']})"
        for t in triples
    )


class Retriever:
    def __init__(self, graph: GraphMemory, llm: LMStudioClient):
        self.graph = graph
        self.llm = llm

    def _extract_intent(self, query: str) -> dict:
        raw = self.llm._call(INTENT_PROMPT + query, temperature=0.1)
        try:
            return _parse_json(raw)
        except Exception:
            return {"seeds": ["Usuario"], "predicates": [], "types": [], "is_personal": True}

    def retrieve(self, query: str, max_hops: int = 2, max_nodes: int = 15) -> ContextResponse:
        intent = self._extract_intent(query)

        seed_names: list[str] = []

        # Always include Usuario for personal queries
        if intent.get("is_personal", True):
            seed_names.append("Usuario")

        # Seeds from intent
        for name in intent.get("seeds", []):
            if name not in seed_names:
                seed_names.append(name)

        # Expand by predicate hints
        for name in self.graph.get_nodes_by_predicate(intent.get("predicates", [])):
            if name not in seed_names:
                seed_names.append(name)

        # Expand by type hints
        for name in self.graph.get_nodes_by_type(intent.get("types", [])):
            if name not in seed_names:
                seed_names.append(name)

        # Fallback: keyword search on remaining query words
        if len(seed_names) <= 1:
            stopwords = {"el","la","los","las","un","una","de","que","en","y","a",
                         "es","su","con","por","para","como","mi","me","se","del",
                         "al","le","sabes","donde","vives","tienes","cuando","quien"}
            words = [w for w in re.findall(r"\w+", query.lower())
                     if w not in stopwords and len(w) > 2]
            for word in words:
                for name in self.graph.search_nodes(word, limit=3):
                    if name not in seed_names:
                        seed_names.append(name)

        if not seed_names:
            return ContextResponse(
                context="",
                triples_found=0,
                nodes=[],
                raw_triples=[],
            )

        triples = self.graph.get_neighborhood(seed_names[:max_nodes], hops=max_hops)

        # Filter to relevant predicates if intent specified them
        if intent.get("predicates"):
            relevant = [t for t in triples if t["predicate"] in intent["predicates"]]
            triples = relevant if relevant else triples

        triples = triples[: max_nodes * 3]

        if not triples:
            return ContextResponse(context="", triples_found=0, nodes=[], raw_triples=[])

        triples_text = _triples_to_text(triples)
        prompt = CONTEXT_PROMPT.format(query=query, triples=triples_text)
        summary = self.llm._call(prompt, temperature=0.2).strip()

        if summary == "NO_INFO":
            summary = ""

        all_nodes = list({t["subject"] for t in triples} | {t["object"] for t in triples})

        return ContextResponse(
            context=summary,
            triples_found=len(triples),
            nodes=all_nodes,
            raw_triples=triples,
        )
