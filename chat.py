#!/usr/bin/env python3
"""
CLI de chat con memoria de grafos.
Cada mensaje se extrae al grafo, y antes de responder se inyecta contexto relevante.

Uso: python chat.py [--api http://localhost:8000] [--lmstudio http://localhost:1234/v1]
"""

import argparse
import json
import sys
import httpx
from openai import OpenAI

API = "http://localhost:8000"
LMSTUDIO = "http://localhost:1234/v1"


def store_message(api: str, message: str) -> dict:
    r = httpx.post(f"{api}/conversation", json={"message": message}, timeout=30)
    r.raise_for_status()
    return r.json()


def get_context(api: str, query: str) -> str:
    r = httpx.post(f"{api}/query", json={"query": query, "max_hops": 2}, timeout=30)
    r.raise_for_status()
    return r.json().get("context", "")


def chat_with_context(llm: OpenAI, model: str, history: list, context: str, user_msg: str) -> str:
    system = "Eres un asistente con memoria persistente. Usa el contexto del grafo cuando sea relevante."
    messages = [{"role": "system", "content": system}]

    if context:
        messages.append({
            "role": "system",
            "content": f"Contexto de memoria (grafo):\n{context}",
        })

    messages += history[-6:]  # últimos 3 turnos para no saturar
    messages.append({"role": "user", "content": user_msg})

    resp = llm.chat.completions.create(model=model, messages=messages, temperature=0.7)
    return resp.choices[0].message.content.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default=API)
    parser.add_argument("--lmstudio", default=LMSTUDIO)
    parser.add_argument("--model", default="local-model")
    args = parser.parse_args()

    llm = OpenAI(base_url=args.lmstudio, api_key="lm-studio")
    history = []

    print(f"[Graph Memory Chat] API={args.api} | LMStudio={args.lmstudio}")
    print("Comandos especiales: /profile, /branch <nombre>, /quit\n")

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
            r = httpx.get(f"{args.api}/profile", timeout=10)
            data = r.json()
            print(f"\n[Grafo completo: {data['total']} tripletas]")
            for t in data["triples"]:
                print(f"  ({t['subject']}) --[{t['predicate']}]--> ({t['object']})")
            print()
            continue

        if user_input.startswith("/branch "):
            branch = user_input.split(" ", 1)[1]
            r = httpx.get(f"{args.api}/branch/{branch}", timeout=10)
            if r.status_code == 404:
                r2 = httpx.get(f"{args.api}/branches", timeout=10)
                print(f"Rama no encontrada. Disponibles: {r2.json()['branches']}")
            else:
                data = r.json()
                print(f"\n[Rama '{branch}': {len(data['triples'])} tripletas]")
                for t in data["triples"]:
                    print(f"  ({t['subject']}) --[{t['predicate']}]--> ({t['object']})")
            print()
            continue

        # 1. Extraer hechos del mensaje al grafo
        try:
            stored = store_message(args.api, user_input)
            if stored["triples_stored"] > 0:
                print(f"  [memoria: +{stored['triples_stored']} tripletas guardadas]")
        except Exception as e:
            print(f"  [advertencia: no se pudo guardar en grafo: {e}]")

        # 2. Recuperar contexto relevante
        context = ""
        try:
            context = get_context(args.api, user_input)
        except Exception:
            pass

        # 3. Responder con contexto inyectado
        try:
            reply = chat_with_context(llm, args.model, history, context, user_input)
            print(f"\nAsistente: {reply}\n")
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": reply})
        except Exception as e:
            print(f"[error LMStudio: {e}]")


if __name__ == "__main__":
    main()
