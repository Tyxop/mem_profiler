import json
import re
import os
from openai import OpenAI
from .models import Triple

EXTRACT_PROMPT = """Eres un extractor de conocimiento para un grafo de memoria. Tu tarea es extraer hechos permanentes o semipermanentes del texto.

REGLAS:
- Solo extrae hechos que valga la pena recordar (preferencias, relaciones, estados, datos personales, eventos importantes)
- Ignora saludos, frases vacías, o información efímera
- El sujeto "Usuario" siempre se refiere a la persona con quien hablo
- Usa predicados en MAYUSCULAS_CON_GUION_BAJO (VIVE_EN, PREFIERE, TIENE, ES_UN, TRABAJA_EN, etc.)
- Sé conciso: objeto máximo 5 palabras, añade detalles como propiedades JSON en "object_properties"

Devuelve SOLO un array JSON válido. Sin explicaciones. Sin markdown.

Formato de cada tripleta:
{"subject": "...", "subject_type": "TIPO", "predicate": "PREDICADO", "object": "...", "object_type": "TIPO"}

Tipos válidos: PERSONA, LUGAR, MASCOTA, COMIDA, TRABAJO, HOBBIE, ESTADO, CONDICION, FECHA, OBJETO, ENTIDAD

Texto a analizar:
"""

CLEAN_PROMPT = """Tienes estas tripletas de un grafo de memoria. Elimina duplicados y las que sean irrelevantes o contradictorias. Devuelve SOLO el array JSON limpio. Sin markdown.

Tripletas:
"""


class LMStudioClient:
    def __init__(self):
        self.client = OpenAI(
            base_url=os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1"),
            api_key="lm-studio",
        )
        self.model = os.getenv("LMSTUDIO_MODEL", "local-model")

    def _call(self, prompt: str, temperature: float = 0.1) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()

    def _parse_json_array(self, text: str) -> list:
        text = text.strip()
        # Strip markdown code blocks if present
        text = re.sub(r"```(?:json)?\s*", "", text).strip()
        # Find first JSON array
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        if text.startswith("["):
            return json.loads(text)
        return []

    def extract_triples(self, text: str) -> list[Triple]:
        raw = self._call(EXTRACT_PROMPT + text)
        try:
            data = self._parse_json_array(raw)
            triples = []
            for item in data:
                if all(k in item for k in ("subject", "predicate", "object")):
                    triples.append(Triple(**item))
            return triples
        except (json.JSONDecodeError, Exception):
            return []

    def summarize_conversation(self, history: list[dict], topic: str) -> tuple[str, list[str]]:
        """Returns (summary_text, list_of_mentioned_entity_names)."""
        if not history:
            return "", []
        convo = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in history[-12:]
        )
        prompt = f"""Resume en 2-3 frases los hechos clave de esta conversación sobre '{topic}'.
Solo hechos concretos y útiles para recordar en el futuro. Sin preámbulos.
Luego añade una línea "ENTIDADES:" con los nombres propios mencionados (separados por coma).

Conversación:
{convo}

Respuesta:"""
        raw = self._call(prompt, temperature=0.2)
        lines = raw.strip().split("\n")
        entities: list[str] = []
        summary_lines = []
        for line in lines:
            if line.upper().startswith("ENTIDADES:"):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    entities = [e.strip() for e in parts[1].split(",") if e.strip()]
            else:
                summary_lines.append(line)
        return "\n".join(summary_lines).strip(), entities

    def build_context_summary(self, query: str, triples: list[dict]) -> str:
        if not triples:
            return ""
        triples_text = "\n".join(
            f"- ({t['subject']}) --[{t['predicate']}]--> ({t['object']})"
            for t in triples
        )
        prompt = f"""Dado este subgrafo de memoria relevante, genera un resumen conciso (máximo 3 líneas) para usar como contexto al responder la consulta.

Consulta: {query}

Grafo relevante:
{triples_text}

Resumen de contexto (directo, sin preámbulos):"""
        return self._call(prompt, temperature=0.3)
