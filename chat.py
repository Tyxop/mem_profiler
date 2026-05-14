#!/usr/bin/env python3
"""
CLI de chat con memoria de grafos.
Cada mensaje se extrae al grafo, y antes de responder se inyecta contexto relevante.

Uso: python chat.py [--api http://localhost:8000] [--lmstudio http://localhost:1234/v1] [--model nombre]
"""

import argparse
import httpx
from openai import OpenAI

API = "http://localhost:8000"
LMSTUDIO = "http://localhost:1234/v1"

SYSTEM_PROMPT = """Eres un asistente conversacional con memoria persistente en grafo. Tu comportamiento:

1. USAR EL CONTEXTO: Si el contexto del grafo contiene la respuesta, úsala directamente y con naturalidad. No digas "según mi base de datos", simplemente responde como si lo recordaras.

2. PREGUNTAR SI FALTA INFO: Si el usuario pregunta algo sobre sí mismo (dónde vive, su nombre, sus gustos, su trabajo, su familia, sus mascotas, etc.) y el contexto del grafo no tiene esa información, pregúntaselo amablemente. Ejemplo: "No recuerdo dónde vives, ¿me lo puedes decir?"

3. ACTUALIZAR DATOS: Si el usuario corrige o actualiza información ("ahora vivo en Barcelona", "me llamo Juan"), responde confirmando el cambio. El sistema lo guardará automáticamente.

4. COMPORTAMIENTO NATURAL: Responde de forma conversacional y concisa. No menciones "grafos", "nodos", ni tecnicismos. Simplemente recuerda y conversa.
"""


def store_message(api: str, message: str) -> dict:
    r = httpx.post(f"{api}/conversation", json={"message": message}, timeout=60)
    r.raise_for_status()
    return r.json()


def get_context(api: str, query: str) -> str:
    r = httpx.post(f"{api}/query", json={"query": query, "max_hops": 2}, timeout=60)
    r.raise_for_status()
    return r.json().get("context", "")


def chat_reply(llm: OpenAI, model: str, history: list, context: str, user_msg: str) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if context:
        messages.append({
            "role": "system",
            "content": f"Contexto de memoria (lo que recuerdas del usuario):\n{context}",
        })
    else:
        messages.append({
            "role": "system",
            "content": "No tienes contexto relevante en memoria para esta pregunta. Si el usuario pregunta algo personal que no sabes, pregúntaselo.",
        })

    messages += history[-8:]
    messages.append({"role": "user", "content": user_msg})

    resp = llm.chat.completions.create(model=model, messages=messages, temperature=0.7)
    return resp.choices[0].message.content.strip()


def print_profile(api: str):
    r = httpx.get(f"{api}/profile", timeout=10)
    data = r.json()
    print(f"\n[Grafo: {data['total']} tripletas]")
    for t in data["triples"]:
        print(f"  ({t['subject']}) --[{t['predicate']}]--> ({t['object']})")
    print()


def print_branch(api: str, branch: str):
    r = httpx.get(f"{api}/branch/{branch}", timeout=10)
    if r.status_code == 404:
        r2 = httpx.get(f"{api}/branches", timeout=10)
        print(f"Rama no encontrada. Disponibles: {r2.json()['branches']}")
    else:
        data = r.json()
        print(f"\n[Rama '{branch}': {len(data['triples'])} tripletas]")
        for t in data["triples"]:
            print(f"  ({t['subject']}) --[{t['predicate']}]--> ({t['object']})")
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default=API)
    parser.add_argument("--lmstudio", default=LMSTUDIO)
    parser.add_argument("--model", default="local-model")
    args = parser.parse_args()

    llm = OpenAI(base_url=args.lmstudio, api_key="lm-studio")
    history = []

    print(f"[Graph Memory Chat] API={args.api} | Modelo={args.model}")
    print("Comandos: /profile  /branch <nombre>  /quit\n")

    while True:
        try:
            user_input = input("Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAdios.")
            break

        if not user_input:
            continue
        if user_input == "/quit":
            break
        if user_input == "/profile":
            print_profile(args.api)
            continue
        if user_input.startswith("/branch "):
            print_branch(args.api, user_input.split(" ", 1)[1])
            continue

        # 1. Recuperar contexto relevante ANTES de responder
        context = ""
        try:
            context = get_context(args.api, user_input)
        except Exception as e:
            print(f"  [advertencia retrieval: {e}]")

        # 2. Responder usando el contexto
        try:
            reply = chat_reply(llm, args.model, history, context, user_input)
            print(f"\nAsistente: {reply}\n")
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": reply})
        except Exception as e:
            print(f"[error LMStudio: {e}]")
            continue

        # 3. Extraer hechos del mensaje y guardar en el grafo (en background conceptual)
        try:
            stored = store_message(args.api, user_input)
            if stored["triples_stored"] > 0:
                labels = [f"({t['subject']})-[{t['predicate']}]->({t['object']})" for t in stored["triples"]]
                print(f"  [memoria: {' | '.join(labels)}]\n")
        except Exception as e:
            print(f"  [advertencia store: {e}]")


if __name__ == "__main__":
    main()
