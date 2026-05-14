#!/usr/bin/env python3
"""
CLI de chat con memoria de grafos.
Uso: python chat.py [--api http://localhost:8000] [--lmstudio http://localhost:1234/v1] [--model nombre]
"""

import argparse
import httpx
from openai import OpenAI

API = "http://localhost:8000"
LMSTUDIO = "http://localhost:1234/v1"

SYSTEM_BASE = """Eres un asistente conversacional con memoria persistente en grafo.

REGLAS:
1. USAR EL CONTEXTO: Si el contexto del grafo contiene la respuesta, úsala con naturalidad. No digas "según mi base de datos".
2. PREGUNTAR SI FALTA INFO: Si el usuario pregunta algo personal que no está en el contexto, pregúntaselo. Ejemplo: "No recuerdo dónde vives, ¿me lo puedes decir?"
3. ACTUALIZAR DATOS: Si el usuario corrige información ("ahora vivo en Barcelona"), responde confirmando. El sistema lo guardará.
4. NATURAL: Responde de forma conversacional. No menciones "grafos", "nodos" ni tecnicismos.
"""


def api_post(api: str, path: str, **kwargs) -> dict:
    r = httpx.post(f"{api}{path}", timeout=60, **kwargs)
    r.raise_for_status()
    return r.json()


def api_get(api: str, path: str, **kwargs) -> dict:
    r = httpx.get(f"{api}{path}", timeout=60, **kwargs)
    r.raise_for_status()
    return r.json()


def get_context(api: str, query: str) -> str:
    data = api_post(api, "/query", json={"query": query, "max_hops": 2})
    return data.get("context", "")


def store_message(api: str, message: str) -> dict:
    return api_post(api, "/conversation", json={"message": message})


def save_note(api: str, topic: str, summary: str, entities: list[str], session_id: str):
    api_post(api, "/memory/note", params={
        "topic": topic,
        "summary": summary,
        "entities": ",".join(entities),
        "session_id": session_id,
    })


def load_topic_context(api: str, topic: str) -> dict:
    return api_get(api, f"/topic/{topic}/context")


def build_messages(history: list, context: str, topic_ctx: str, user_msg: str) -> list:
    messages = [{"role": "system", "content": SYSTEM_BASE}]

    if topic_ctx:
        messages.append({"role": "system", "content": f"Contexto inicial del tema:\n{topic_ctx}"})

    if context:
        messages.append({"role": "system", "content": f"Contexto relevante de memoria:\n{context}"})
    else:
        messages.append({"role": "system", "content": "No tienes contexto relevante para esta pregunta. Si es personal, pregunta al usuario."})

    messages += history[-8:]
    messages.append({"role": "user", "content": user_msg})
    return messages


def chat_reply(llm: OpenAI, model: str, messages: list) -> str:
    resp = llm.chat.completions.create(model=model, messages=messages, temperature=0.7)
    return resp.choices[0].message.content.strip()


def summarize_and_save(api: str, llm: OpenAI, model: str, history: list, topic: str, session_id: str):
    """Ask LMStudio to summarize the conversation, then store as MemoryNote."""
    if not history:
        return
    convo = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history[-12:])
    prompt = f"""Resume en 2-3 frases los hechos clave de esta conversación sobre '{topic}'.
Solo hechos concretos útiles para recordar. Sin preámbulos.
Luego añade una línea "ENTIDADES:" con los nombres propios mencionados (separados por coma).

Conversación:
{convo}

Respuesta:"""
    try:
        resp = llm.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        raw = resp.choices[0].message.content.strip()
        lines = raw.split("\n")
        entities = []
        summary_lines = []
        for line in lines:
            if line.upper().startswith("ENTIDADES:"):
                entities = [e.strip() for e in line.split(":", 1)[-1].split(",") if e.strip()]
            else:
                summary_lines.append(line)
        summary = "\n".join(summary_lines).strip()
        if summary:
            save_note(api, topic, summary, entities, session_id)
            print(f"  [nota guardada sobre '{topic}': {summary[:80]}...]")
    except Exception as e:
        print(f"  [advertencia al resumir: {e}]")


def format_topic_ctx(data: dict) -> str:
    lines = []
    for t in data.get("triples", []):
        lines.append(f"({t['subject']}) --[{t['predicate']}]--> ({t['object']})")
    for n in data.get("memory_notes", []):
        lines.append(f"[Nota anterior sobre {n['topic']}]: {n['summary']}")
    return "\n".join(lines)


def cmd_profile(api: str):
    data = api_get(api, "/profile")
    print(f"\n[Grafo: {data['total']} tripletas]")
    for t in data["triples"]:
        print(f"  ({t['subject']}) --[{t['predicate']}]--> ({t['object']})")
    print()


def cmd_branch(api: str, branch: str):
    try:
        data = api_get(api, f"/branch/{branch}")
        print(f"\n[Rama '{branch}': {len(data['triples'])} tripletas]")
        for t in data["triples"]:
            print(f"  ({t['subject']}) --[{t['predicate']}]--> ({t['object']})")
    except httpx.HTTPStatusError:
        branches = api_get(api, "/branches")
        print(f"Rama no encontrada. Disponibles: {branches['branches']}")
    print()


def cmd_notes(api: str, topic: str = None):
    params = {"topic": topic} if topic else {}
    data = api_get(api, "/memory/notes", params=params)
    print(f"\n[Notas de conversación: {data['total']}]")
    for n in data["notes"]:
        ts = n.get("created_at", 0) // 1000
        entities = ", ".join(n.get("entities", []))
        print(f"  [{n['topic']}] {n['summary']}")
        if entities:
            print(f"    Entidades: {entities}")
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default=API)
    parser.add_argument("--lmstudio", default=LMSTUDIO)
    parser.add_argument("--model", default="local-model")
    args = parser.parse_args()

    llm = OpenAI(base_url=args.lmstudio, api_key="lm-studio")
    history: list = []
    current_topic = "general"
    topic_ctx_text = ""
    import uuid
    session_id = str(uuid.uuid4())[:8]

    print(f"[Graph Memory Chat] API={args.api} | Modelo={args.model}")
    print("Comandos: /tema <nombre>  /profile  /branch <rama>  /notas [tema]  /quit\n")
    print(f"Tema actual: {current_topic}\n")

    while True:
        try:
            user_input = input("Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAdios.")
            break

        if not user_input:
            continue

        # ── Comandos ────────────────────────────────────────────────────────
        if user_input == "/quit":
            break

        if user_input == "/profile":
            cmd_profile(args.api)
            continue

        if user_input.startswith("/branch "):
            cmd_branch(args.api, user_input.split(" ", 1)[1])
            continue

        if user_input.startswith("/notas"):
            parts = user_input.split(" ", 1)
            cmd_notes(args.api, parts[1] if len(parts) > 1 else None)
            continue

        if user_input.startswith("/tema "):
            new_topic = user_input.split(" ", 1)[1].strip()

            # 1. Resumir y guardar la conversación actual como MemoryNote
            if history:
                print(f"  [guardando resumen del tema '{current_topic}'...]")
                summarize_and_save(args.api, llm, args.model, history, current_topic, session_id)

            # 2. Limpiar historial
            history = []
            current_topic = new_topic

            # 3. Cargar contexto del nuevo tema desde el grafo
            print(f"  [cargando contexto del tema '{new_topic}' desde el grafo...]")
            try:
                ctx_data = load_topic_context(args.api, new_topic)
                topic_ctx_text = format_topic_ctx(ctx_data)
                t_count = ctx_data["triples_count"]
                n_count = ctx_data["notes_count"]
                print(f"  [{t_count} tripletas + {n_count} notas anteriores cargadas]\n")
                if not topic_ctx_text:
                    print(f"  [no hay información previa sobre '{new_topic}' en el grafo]\n")
            except Exception as e:
                topic_ctx_text = ""
                print(f"  [sin contexto previo para '{new_topic}']\n")

            print(f"Tema cambiado a: {new_topic}\n")
            continue

        # ── Flujo normal ─────────────────────────────────────────────────────

        # 1. Recuperar contexto relevante del grafo
        context = ""
        try:
            context = get_context(args.api, user_input)
        except Exception as e:
            print(f"  [advertencia retrieval: {e}]")

        # 2. Responder
        try:
            messages = build_messages(history, context, topic_ctx_text, user_input)
            reply = chat_reply(llm, args.model, messages)
            print(f"\nAsistente: {reply}\n")
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": reply})
        except Exception as e:
            print(f"[error LMStudio: {e}]")
            continue

        # 3. Extraer y guardar hechos del mensaje en el grafo
        try:
            stored = store_message(args.api, user_input)
            if stored["triples_stored"] > 0:
                labels = [
                    f"({t['subject']})-[{t['predicate']}]->({t['object']})"
                    for t in stored["triples"]
                ]
                print(f"  [memoria: {' | '.join(labels)}]\n")
        except Exception as e:
            print(f"  [advertencia store: {e}]")


if __name__ == "__main__":
    main()
