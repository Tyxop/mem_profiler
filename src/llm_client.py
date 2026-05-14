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
