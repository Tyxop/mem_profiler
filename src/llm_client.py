import json
import re
import os
from openai import OpenAI
from .models import Triple

EXTRACT_PROMPT = """Eres un extractor de conocimiento para un grafo de memoria en árbol.
Tu tarea: convertir texto en tripletas S-P-O que formen un ÁRBOL de entidades relacionadas, NO una lista plana.

REGLA FUNDAMENTAL — CONSTRUYE ÁRBOLES:
Conecta al Usuario solo el nodo raíz de cada tema. Desde ese nodo, crea ramas hacia subtipos, detalles, épocas, personas, etc.

CORRECTO (árbol):
Texto: "Me encanta el cine de ciencia ficción, sobre todo las distopías de los 80 y Christopher Nolan"
[
  {"subject": "Usuario", "subject_type": "PERSONA", "predicate": "LE_GUSTA", "object": "Cine", "object_type": "ENTRETENIMIENTO"},
  {"subject": "Cine", "subject_type": "ENTRETENIMIENTO", "predicate": "GENERO_PREFERIDO", "object": "Ciencia Ficción", "object_type": "GENERO"},
  {"subject": "Ciencia Ficción", "subject_type": "GENERO", "predicate": "SUBTEMA_PREFERIDO", "object": "Distopía", "object_type": "SUBTEMA"},
  {"subject": "Distopía", "subject_type": "SUBTEMA", "predicate": "EPOCA_PREFERIDA", "object": "Años 80", "object_type": "EPOCA"},
  {"subject": "Ciencia Ficción", "subject_type": "GENERO", "predicate": "DIRECTOR_FAVORITO", "object": "Christopher Nolan", "object_type": "DIRECTOR"}
]

INCORRECTO (todo plano al usuario — NUNCA hagas esto):
[
  {"subject": "Usuario", "predicate": "LE_GUSTA", "object": "Cine de ciencia ficción"},
  {"subject": "Usuario", "predicate": "LE_GUSTA", "object": "Distopías de los 80"},
  {"subject": "Usuario", "predicate": "DIRECTOR_FAVORITO", "object": "Christopher Nolan"}
]

MÁS EJEMPLOS DE ÁRBOL:
- Mascotas: (Usuario)-[TIENE_MASCOTA]->(Toby) → (Toby)-[ES_UN]->(Perro) → (Toby)-[TIENE_ESTADO]->(Enfermo)
- Trabajo: (Usuario)-[TRABAJA_EN]->(Empresa X) → (Empresa X)-[SECTOR]->(Tecnología) → (Empresa X)-[ROL_USUARIO]->(Developer)
- Música: (Usuario)-[LE_GUSTA]->(Música) → (Música)-[GENERO_PREFERIDO]->(Jazz) → (Jazz)-[ARTISTA_FAVORITO]->(Miles Davis)

TIPOS DE NODO: PERSONA, ENTRETENIMIENTO, GENERO, SUBTEMA, EPOCA, DIRECTOR, PELICULA, SERIE, LIBRO, AUTOR,
MUSICA, ARTISTA, ALBUM, DEPORTE, EQUIPO, LUGAR, MASCOTA, COMIDA, TRABAJO, EMPRESA, TECNOLOGIA,
HOBBIE, ESTADO, CONDICION, CONCEPTO, FECHA, OBJETO

PREDICADOS: usa verbos específicos del dominio. No todo es PREFIERE.
Cine: GENERO_PREFERIDO, DIRECTOR_FAVORITO, PELICULA_FAVORITA, SUBTEMA_PREFERIDO, EPOCA_PREFERIDA
Mascotas: TIENE_MASCOTA, ES_UN, TIENE_ESTADO, PREFIERE, VIVE_CON
Trabajo: TRABAJA_EN, TIENE_ROL, USA_TECNOLOGIA, PROGRAMA_EN

REGLAS FINALES:
- Solo extrae hechos permanentes o semipermanentes (ignora saludos e info efímera)
- El objeto debe ser un sustantivo concreto (máximo 4 palabras)
- Si el texto habla de un tema sin mencionar al usuario directamente, conéctalo igualmente al árbol de ese tema
- Devuelve SOLO el array JSON. Sin markdown. Sin explicaciones.

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
