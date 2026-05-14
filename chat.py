#!/usr/bin/env python3
"""
Graph Memory Chat — CLI con memoria persistente en grafo.
Uso: python chat.py [--api URL] [--lmstudio URL] [--model nombre]
"""

import argparse
import uuid

import httpx
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from rich import box

API      = "http://localhost:8000"
LMSTUDIO = "http://localhost:1234/v1"

console = Console()

SYSTEM_BASE = """Eres un asistente conversacional con memoria persistente en grafo.

REGLAS:
1. USAR EL CONTEXTO: Si el contexto del grafo contiene la respuesta, úsala con naturalidad. No digas "según mi base de datos".
2. PREGUNTAR SI FALTA INFO: Si el usuario pregunta algo personal que no está en el contexto, pregúntaselo. Ejemplo: "No recuerdo dónde vives, ¿me lo puedes decir?"
3. ACTUALIZAR DATOS: Si el usuario corrige información ("ahora vivo en Barcelona"), responde confirmando. El sistema lo guardará.
4. NATURAL: Responde de forma conversacional. No menciones "grafos", "nodos" ni tecnicismos.
"""

# ── UI helpers ───────────────────────────────────────────────────────────────

def print_header(api: str, model: str, topic: str):
    console.print()
    console.print(Panel(
        Text.assemble(
            ("⬡  Graph Memory Chat\n", "bold magenta"),
            (f"API: {api}   Modelo: {model}", "dim"),
        ),
        box=box.DOUBLE_EDGE,
        border_style="magenta",
        expand=False,
    ))


def print_commands():
    table = Table(
        box=box.SIMPLE,
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
        expand=False,
    )
    table.add_column("Comando", style="bold yellow", no_wrap=True)
    table.add_column("Descripción", style="white")

    cmds = [
        ("/tema <nombre>",  "Cambiar tema: guarda resumen, limpia historial y carga contexto del grafo"),
        ("/profile",        "Muestra todo el grafo de memoria"),
        ("/branch <rama>",  "Muestra una rama semántica (mascotas, ubicacion, trabajo…)"),
        ("/notas [tema]",   "Lista notas de conversación guardadas"),
        ("/quit",           "Salir del chat"),
    ]
    for cmd, desc in cmds:
        table.add_row(cmd, desc)

    console.print(Panel(table, title="[bold cyan]Comandos[/]", border_style="cyan", box=box.ROUNDED))


def print_topic_bar(topic: str):
    console.print(Rule(f"[bold magenta]Tema: {topic}[/]", style="dim magenta"))
    console.print()


def print_user(text: str):
    console.print(Text.assemble(("  Tú  ", "bold white on blue"), (" ", ""), (text, "bold white")))
    console.print()


def print_assistant(text: str):
    console.print(
        Panel(
            Text(text, style="white"),
            title="[bold green]Asistente[/]",
            border_style="green",
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )
    console.print()


def print_memory(triples: list):
    if not triples:
        return
    parts = []
    for t in triples:
        parts.append(f"({t['subject']})-[{t['predicate']}]->({t['object']})")
    console.print(Text.assemble(
        ("  ⬡ memoria  ", "bold black on yellow"),
        ("  ", ""),
        (" | ".join(parts), "dim yellow"),
    ))
    console.print()


def print_info(msg: str):
    console.print(f"  [dim cyan]ℹ  {msg}[/]")


def print_warn(msg: str):
    console.print(f"  [dim red]⚠  {msg}[/]")


def print_success(msg: str):
    console.print(f"  [dim green]✓  {msg}[/]")


def print_separator():
    console.print(Rule(style="dim"))


# ── API calls ────────────────────────────────────────────────────────────────

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


def save_note(api: str, topic: str, summary: str, entities: list, session_id: str):
    api_post(api, "/memory/note", params={
        "topic": topic, "summary": summary,
        "entities": ",".join(entities), "session_id": session_id,
    })


def load_topic_context(api: str, topic: str) -> dict:
    return api_get(api, f"/topic/{topic}/context")


# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_profile(api: str):
    data = api_get(api, "/profile")
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold magenta",
                  border_style="dim", expand=False)
    table.add_column("Sujeto", style="cyan")
    table.add_column("Predicado", style="yellow")
    table.add_column("Objeto", style="green")
    for t in data["triples"]:
        table.add_row(t["subject"], t["predicate"], t["object"])
    console.print(Panel(
        table,
        title=f"[bold magenta]Grafo completo — {data['total']} tripletas[/]",
        border_style="magenta", box=box.ROUNDED,
    ))
    console.print()


def cmd_branch(api: str, branch: str):
    try:
        data = api_get(api, f"/branch/{branch}")
        table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan",
                      border_style="dim", expand=False)
        table.add_column("Sujeto", style="cyan")
        table.add_column("Predicado", style="yellow")
        table.add_column("Objeto", style="green")
        for t in data["triples"]:
            table.add_row(t["subject"], t["predicate"], t["object"])
        console.print(Panel(
            table,
            title=f"[bold cyan]Rama '{branch}' — {len(data['triples'])} tripletas[/]",
            border_style="cyan", box=box.ROUNDED,
        ))
    except httpx.HTTPStatusError:
        branches = api_get(api, "/branches")
        print_warn(f"Rama no encontrada. Disponibles: {', '.join(branches['branches'])}")
    console.print()


def cmd_notes(api: str, topic: str = None):
    params = {"topic": topic} if topic else {}
    data = api_get(api, "/memory/notes", params=params)
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold yellow",
                  border_style="dim", expand=False)
    table.add_column("Tema", style="yellow", no_wrap=True)
    table.add_column("Resumen", style="white")
    table.add_column("Entidades", style="dim cyan")
    for n in data["notes"]:
        table.add_row(
            n["topic"],
            n["summary"][:80] + ("…" if len(n["summary"]) > 80 else ""),
            ", ".join(n.get("entities", [])),
        )
    console.print(Panel(
        table,
        title=f"[bold yellow]Notas de conversación — {data['total']}[/]",
        border_style="yellow", box=box.ROUNDED,
    ))
    console.print()


# ── Topic switch ─────────────────────────────────────────────────────────────

def summarize_and_save(api: str, llm: OpenAI, model: str,
                       history: list, topic: str, session_id: str):
    if not history:
        return
    convo = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history[-12:])
    prompt = f"""Resume en 2-3 frases los hechos clave de esta conversación sobre '{topic}'.
Solo hechos concretos útiles para recordar. Sin preámbulos.
Luego añade "ENTIDADES:" con los nombres propios mencionados separados por coma.

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
        entities, summary_lines = [], []
        for line in raw.split("\n"):
            if line.upper().startswith("ENTIDADES:"):
                entities = [e.strip() for e in line.split(":", 1)[-1].split(",") if e.strip()]
            else:
                summary_lines.append(line)
        summary = "\n".join(summary_lines).strip()
        if summary:
            save_note(api, topic, summary, entities, session_id)
            print_success(f"Nota guardada para '{topic}': {summary[:70]}…")
    except Exception as e:
        print_warn(f"No se pudo guardar resumen: {e}")


def format_topic_ctx(data: dict) -> str:
    lines = []
    for t in data.get("triples", []):
        lines.append(f"({t['subject']}) --[{t['predicate']}]--> ({t['object']})")
    for n in data.get("memory_notes", []):
        lines.append(f"[Nota '{n['topic']}']: {n['summary']}")
    return "\n".join(lines)


# ── Chat core ─────────────────────────────────────────────────────────────────

def chat_reply(llm: OpenAI, model: str, history: list,
               context: str, topic_ctx: str, user_msg: str) -> str:
    messages = [{"role": "system", "content": SYSTEM_BASE}]
    if topic_ctx:
        messages.append({"role": "system", "content": f"Contexto inicial del tema:\n{topic_ctx}"})
    if context:
        messages.append({"role": "system", "content": f"Contexto relevante de memoria:\n{context}"})
    else:
        messages.append({"role": "system",
                         "content": "No tienes contexto relevante. Si el usuario pregunta algo personal, pregúntaselo."})
    messages += history[-8:]
    messages.append({"role": "user", "content": user_msg})
    resp = llm.chat.completions.create(model=model, messages=messages, temperature=0.7)
    return resp.choices[0].message.content.strip()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api",      default=API)
    parser.add_argument("--lmstudio", default=LMSTUDIO)
    parser.add_argument("--model",    default="local-model")
    args = parser.parse_args()

    llm        = OpenAI(base_url=args.lmstudio, api_key="lm-studio")
    history    = []
    topic      = "general"
    topic_ctx  = ""
    session_id = str(uuid.uuid4())[:8]

    print_header(args.api, args.model, topic)
    console.print()
    print_commands()
    console.print()
    print_topic_bar(topic)

    while True:
        try:
            user_input = console.input("[bold blue]  Tú ›[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Hasta luego.[/]")
            break

        if not user_input:
            continue

        # ── Comandos ──────────────────────────────────────────────────────────
        if user_input == "/quit":
            console.print("[dim]Hasta luego.[/]")
            break

        if user_input == "/profile":
            cmd_profile(args.api)
            continue

        if user_input.startswith("/branch "):
            cmd_branch(args.api, user_input.split(" ", 1)[1])
            continue

        if user_input.startswith("/notas"):
            parts = user_input.split(" ", 1)
            cmd_notes(args.api, parts[1].strip() if len(parts) > 1 else None)
            continue

        if user_input.startswith("/tema "):
            new_topic = user_input.split(" ", 1)[1].strip()
            console.print()

            if history:
                print_info(f"Guardando resumen del tema '{topic}'…")
                summarize_and_save(args.api, llm, args.model, history, topic, session_id)

            history   = []
            topic     = new_topic
            topic_ctx = ""

            print_info(f"Cargando contexto del tema '{new_topic}' desde el grafo…")
            try:
                ctx_data  = load_topic_context(args.api, new_topic)
                topic_ctx = format_topic_ctx(ctx_data)
                tc, nc    = ctx_data["triples_count"], ctx_data["notes_count"]
                if topic_ctx:
                    print_success(f"{tc} tripletas + {nc} notas anteriores cargadas")
                else:
                    print_warn(f"No hay información previa sobre '{new_topic}' en el grafo")
            except Exception as e:
                print_warn(f"Sin contexto previo: {e}")

            console.print()
            print_topic_bar(topic)
            continue

        # ── Flujo normal ──────────────────────────────────────────────────────
        print_user(user_input)
        print_separator()

        context = ""
        try:
            context = get_context(args.api, user_input)
        except Exception as e:
            print_warn(f"Retrieval: {e}")

        try:
            reply = chat_reply(llm, args.model, history, context, topic_ctx, user_input)
            print_assistant(reply)
            history.append({"role": "user",      "content": user_input})
            history.append({"role": "assistant", "content": reply})
        except Exception as e:
            print_warn(f"LMStudio: {e}")
            continue

        try:
            stored = store_message(args.api, user_input)
            print_memory(stored.get("triples", []))
        except Exception as e:
            print_warn(f"Store: {e}")


if __name__ == "__main__":
    main()
