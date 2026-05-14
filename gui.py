#!/usr/bin/env python3
"""
Graph Memory — GUI
Uso: python gui.py [--api URL] [--lmstudio URL] [--model nombre]
"""

import argparse
import threading
import uuid
import webbrowser
import tkinter as tk
from tkinter import messagebox, simpledialog

import customtkinter as ctk
import httpx
from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────

API      = "http://localhost:8000"
LMSTUDIO = "http://localhost:1234/v1"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

SYSTEM_BASE = """Eres un asistente conversacional con memoria persistente en grafo.
1. Si el contexto del grafo contiene la respuesta, úsala con naturalidad.
2. Si el usuario pregunta algo personal sin contexto, pregúntaselo amablemente.
3. Si corrige información, responde confirmando. El sistema lo guardará.
4. Responde de forma conversacional. No menciones grafos, nodos ni tecnicismos."""

COLORS = {
    "bg":          "#0f1117",
    "sidebar":     "#1a1d27",
    "border":      "#2a2d3e",
    "user_name":   "#60a5fa",
    "user_msg":    "#dbeafe",
    "asst_name":   "#4ade80",
    "asst_msg":    "#e0e0e0",
    "memory":      "#fbbf24",
    "separator":   "#2a2d3e",
    "topic":       "#a78bfa",
    "info":        "#6b7280",
    "warn":        "#f87171",
}

FONT_NAME = "Segoe UI" if tk.Tk().tk.call("tk", "windowingsystem") == "win32" else "Helvetica Neue"


# ── API helpers (sync, run from threads) ─────────────────────────────────────

def api_get(api: str, path: str, **kw) -> dict:
    r = httpx.get(f"{api}{path}", timeout=60, **kw)
    r.raise_for_status()
    return r.json()


def api_post(api: str, path: str, **kw) -> dict:
    r = httpx.post(f"{api}{path}", timeout=60, **kw)
    r.raise_for_status()
    return r.json()


def fetch_context(api: str, query: str) -> str:
    data = api_post(api, "/query", json={"query": query, "max_hops": 2})
    return data.get("context", "")


def fetch_topic_ctx(api: str, topic: str) -> str:
    data = api_get(api, f"/topic/{topic}/context")
    lines = []
    for t in data.get("triples", []):
        lines.append(f"({t['subject']}) --[{t['predicate']}]--> ({t['object']})")
    for n in data.get("memory_notes", []):
        lines.append(f"[Nota '{n['topic']}']: {n['summary']}")
    return "\n".join(lines)


def store_message(api: str, message: str) -> list:
    data = api_post(api, "/conversation", json={"message": message})
    return data.get("triples", [])


def save_note(api: str, topic: str, summary: str, entities: list, session_id: str):
    api_post(api, "/memory/note", params={
        "topic": topic, "summary": summary,
        "entities": ",".join(entities), "session_id": session_id,
    })


def fetch_profile(api: str) -> list:
    return api_get(api, "/profile").get("triples", [])


def fetch_notes(api: str) -> list:
    return api_get(api, "/memory/notes").get("notes", [])


def fetch_graph_count(api: str) -> int:
    return api_get(api, "/profile").get("total", 0)


# ── Dialog windows ────────────────────────────────────────────────────────────

class TableDialog(ctk.CTkToplevel):
    def __init__(self, parent, title: str, columns: list, rows: list):
        super().__init__(parent)
        self.title(title)
        self.geometry("800x500")
        self.resizable(True, True)
        self.grab_set()

        txt = tk.Text(
            self, bg=COLORS["bg"], fg=COLORS["asst_msg"],
            font=(FONT_NAME, 12), relief="flat", padx=16, pady=12,
            wrap=tk.WORD,
        )
        txt.pack(fill="both", expand=True)
        scroll = ctk.CTkScrollbar(self, command=txt.yview)
        scroll.pack(side="right", fill="y")
        txt.configure(yscrollcommand=scroll.set)

        txt.tag_configure("header", foreground=COLORS["topic"],
                          font=(FONT_NAME, 11, "bold"))
        txt.tag_configure("cell",   foreground=COLORS["asst_msg"],
                          font=(FONT_NAME, 12))
        txt.tag_configure("dim",    foreground=COLORS["info"],
                          font=(FONT_NAME, 11))

        txt.insert("end", "  ".join(f"{c:<20}" for c in columns) + "\n", "header")
        txt.insert("end", "─" * 60 + "\n", "dim")
        for row in rows:
            txt.insert("end", "  ".join(f"{str(v)[:20]:<20}" for v in row) + "\n", "cell")
        txt.configure(state="disabled")

        ctk.CTkButton(self, text="Cerrar", command=self.destroy,
                      fg_color=COLORS["border"], hover_color="#3a3d4e"
                      ).pack(pady=8)


class NewTopicDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Nueva conversación")
        self.geometry("340x160")
        self.resizable(False, False)
        self.grab_set()
        self.result = None

        ctk.CTkLabel(self, text="Nombre del tema:",
                     font=ctk.CTkFont(size=13)).pack(pady=(20, 6))
        self.entry = ctk.CTkEntry(self, width=260, placeholder_text="ej: mascotas, trabajo…")
        self.entry.pack(pady=4)
        self.entry.bind("<Return>", lambda e: self._ok())

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=12)
        ctk.CTkButton(btn_frame, text="Cancelar", width=100,
                      fg_color=COLORS["border"], hover_color="#3a3d4e",
                      command=self.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btn_frame, text="Crear", width=100,
                      fg_color="#4c1d95", hover_color="#5b21b6",
                      command=self._ok).pack(side="left", padx=6)
        self.entry.focus()

    def _ok(self):
        v = self.entry.get().strip()
        if v:
            self.result = v
            self.destroy()


# ── Main app ──────────────────────────────────────────────────────────────────

class GraphMemoryApp(ctk.CTk):
    def __init__(self, api: str, lmstudio_url: str, model: str):
        super().__init__()

        self.api        = api
        self.llm        = OpenAI(base_url=lmstudio_url, api_key="lm-studio")
        self.model      = model
        self.session_id = str(uuid.uuid4())[:8]

        # State per conversation topic
        self.conversations: dict[str, dict] = {}
        self._ensure_topic("general")
        self.current_topic = "general"

        self.title("⬡ Graph Memory")
        self.geometry("1150x720")
        self.minsize(900, 550)
        self.configure(fg_color=COLORS["bg"])

        self._build_ui()
        self._refresh_conv_buttons()
        self._set_active_topic_btn("general")
        self._update_status("Conectando…")
        threading.Thread(target=self._check_api, daemon=True).start()

    # ── Data ─────────────────────────────────────────────────────────────────

    def _ensure_topic(self, topic: str):
        if topic not in self.conversations:
            self.conversations[topic] = {"history": [], "topic_ctx": ""}

    # ── UI build ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=230, corner_radius=0,
                                    fg_color=COLORS["sidebar"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self._build_sidebar()

        # Main
        self.main_frame = ctk.CTkFrame(self, corner_radius=0,
                                       fg_color=COLORS["bg"])
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self._build_main()

    def _build_sidebar(self):
        # Header
        ctk.CTkLabel(
            self.sidebar, text="⬡ Graph Memory",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["topic"],
        ).pack(pady=(18, 2), padx=14, anchor="w")

        ctk.CTkLabel(
            self.sidebar, text="Conversaciones",
            font=ctk.CTkFont(size=10), text_color=COLORS["info"],
        ).pack(pady=(0, 6), padx=14, anchor="w")

        ctk.CTkButton(
            self.sidebar, text="＋  Nueva conversación",
            command=self._new_conversation,
            fg_color=COLORS["border"], hover_color="#3a3d4e",
            height=30, font=ctk.CTkFont(size=12), anchor="w",
        ).pack(padx=10, pady=(0, 6), fill="x")

        # Conversation list
        self.conv_scroll = ctk.CTkScrollableFrame(
            self.sidebar, fg_color="transparent", height=260,
        )
        self.conv_scroll.pack(padx=6, fill="both", expand=True)

        # Divider
        ctk.CTkFrame(self.sidebar, height=1,
                     fg_color=COLORS["border"]).pack(fill="x", padx=10, pady=10)

        # Action buttons
        actions = [
            ("🌐   Abrir visualizador", self._open_viz,     "#2d1b69", "#4c1d95"),
            ("📊   Ver perfil",          self._show_profile, "#1e3a5f", "#1d4ed8"),
            ("📝   Ver notas",           self._show_notes,   "#14532d", "#15803d"),
            ("🗑    Borrar grafo",        self._clear_graph,  "#450a0a", "#7f1d1d"),
        ]
        for label, cmd, fg, hv in actions:
            ctk.CTkButton(
                self.sidebar, text=label, command=cmd,
                fg_color=fg, hover_color=hv,
                height=30, font=ctk.CTkFont(size=12), anchor="w",
            ).pack(padx=10, pady=2, fill="x")

        # Status
        self.status_var = tk.StringVar(value="")
        ctk.CTkLabel(
            self.sidebar, textvariable=self.status_var,
            font=ctk.CTkFont(size=10), text_color=COLORS["info"],
        ).pack(pady=(10, 6))

    def _build_main(self):
        # Topic bar
        topic_bar = ctk.CTkFrame(self.main_frame, height=38,
                                 fg_color=COLORS["sidebar"], corner_radius=0)
        topic_bar.grid(row=0, column=0, sticky="ew")
        topic_bar.grid_propagate(False)

        self.topic_label = ctk.CTkLabel(
            topic_bar, text="  Tema: general",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["topic"],
        )
        self.topic_label.pack(side="left", padx=8)

        self.thinking_label = ctk.CTkLabel(
            topic_bar, text="",
            font=ctk.CTkFont(size=11), text_color=COLORS["info"],
        )
        self.thinking_label.pack(side="right", padx=12)

        # Chat display
        chat_container = ctk.CTkFrame(self.main_frame, corner_radius=0,
                                      fg_color=COLORS["bg"])
        chat_container.grid(row=1, column=0, sticky="nsew")
        chat_container.grid_rowconfigure(0, weight=1)
        chat_container.grid_columnconfigure(0, weight=1)

        self.chat_txt = tk.Text(
            chat_container,
            bg=COLORS["bg"], fg=COLORS["asst_msg"],
            font=(FONT_NAME, 13),
            relief="flat", bd=0,
            padx=20, pady=16,
            wrap=tk.WORD,
            state=tk.DISABLED,
            cursor="arrow",
        )
        self.chat_txt.grid(row=0, column=0, sticky="nsew")

        scrollbar = ctk.CTkScrollbar(chat_container, command=self.chat_txt.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.chat_txt.configure(yscrollcommand=scrollbar.set)

        self._configure_text_tags()

        # Input area
        input_bar = ctk.CTkFrame(self.main_frame, height=72,
                                 fg_color=COLORS["sidebar"], corner_radius=0)
        input_bar.grid(row=2, column=0, sticky="ew")
        input_bar.grid_propagate(False)
        input_bar.grid_columnconfigure(0, weight=1)

        self.input_box = ctk.CTkTextbox(
            input_bar, height=46,
            fg_color="#12151f",
            font=ctk.CTkFont(size=13),
            corner_radius=8,
            border_color=COLORS["border"],
            border_width=1,
            wrap="word",
        )
        self.input_box.grid(row=0, column=0, padx=(14, 8), pady=13, sticky="ew")
        self.input_box.bind("<Return>",       self._on_enter)
        self.input_box.bind("<Shift-Return>", lambda e: "break")

        self.send_btn = ctk.CTkButton(
            input_bar, text="Enviar",
            command=self._send,
            width=84, height=46,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#4c1d95", hover_color="#5b21b6",
            corner_radius=8,
        )
        self.send_btn.grid(row=0, column=1, padx=(0, 14), pady=13)

    def _configure_text_tags(self):
        t = self.chat_txt
        t.tag_configure("user_name",  foreground=COLORS["user_name"],
                        font=(FONT_NAME, 11, "bold"))
        t.tag_configure("user_msg",   foreground=COLORS["user_msg"],
                        font=(FONT_NAME, 13), lmargin1=8, lmargin2=8)
        t.tag_configure("asst_name",  foreground=COLORS["asst_name"],
                        font=(FONT_NAME, 11, "bold"))
        t.tag_configure("asst_msg",   foreground=COLORS["asst_msg"],
                        font=(FONT_NAME, 13), lmargin1=8, lmargin2=8)
        t.tag_configure("memory",     foreground=COLORS["memory"],
                        font=(FONT_NAME, 10), lmargin1=8)
        t.tag_configure("separator",  foreground=COLORS["border"],
                        font=(FONT_NAME, 8))
        t.tag_configure("info",       foreground=COLORS["info"],
                        font=(FONT_NAME, 11, "italic"), lmargin1=8)
        t.tag_configure("warn",       foreground=COLORS["warn"],
                        font=(FONT_NAME, 11, "italic"), lmargin1=8)
        t.tag_configure("topic_hdr",  foreground=COLORS["topic"],
                        font=(FONT_NAME, 12, "bold"), justify="center")

    # ── Conversation list ─────────────────────────────────────────────────────

    def _refresh_conv_buttons(self):
        for w in self.conv_scroll.winfo_children():
            w.destroy()
        self.conv_buttons = {}
        for topic in self.conversations:
            btn = ctk.CTkButton(
                self.conv_scroll,
                text=f"  ○  {topic}",
                command=lambda t=topic: self._switch_topic(t),
                fg_color="transparent",
                hover_color=COLORS["border"],
                text_color=COLORS["info"],
                height=30,
                font=ctk.CTkFont(size=12),
                anchor="w",
                corner_radius=6,
            )
            btn.pack(fill="x", pady=2, padx=4)
            self.conv_buttons[topic] = btn

    def _set_active_topic_btn(self, topic: str):
        for t, btn in self.conv_buttons.items():
            if t == topic:
                btn.configure(
                    text=f"  ●  {t}",
                    text_color=COLORS["topic"],
                    fg_color=COLORS["border"],
                )
            else:
                btn.configure(
                    text=f"  ○  {t}",
                    text_color=COLORS["info"],
                    fg_color="transparent",
                )

    # ── Chat text helpers ─────────────────────────────────────────────────────

    def _chat_append(self, text: str, tag: str = "asst_msg"):
        self.chat_txt.configure(state=tk.NORMAL)
        self.chat_txt.insert(tk.END, text, tag)
        self.chat_txt.configure(state=tk.DISABLED)
        self.chat_txt.see(tk.END)

    def _add_separator(self):
        self._chat_append("\n" + "─" * 60 + "\n", "separator")

    def _add_user_message(self, text: str):
        self._chat_append("\nTú\n", "user_name")
        self._chat_append(text + "\n", "user_msg")

    def _add_assistant_message(self, text: str):
        self._chat_append("\nAsistente\n", "asst_name")
        self._chat_append(text + "\n", "asst_msg")

    def _add_memory_tag(self, triples: list):
        if not triples:
            return
        parts = " | ".join(
            f"({t['subject']})-[{t['predicate']}]->({t['object']})"
            for t in triples
        )
        self._chat_append(f"⬡  {parts}\n", "memory")

    def _add_info(self, text: str):
        self._chat_append(f"ℹ  {text}\n", "info")

    def _add_warn(self, text: str):
        self._chat_append(f"⚠  {text}\n", "warn")

    def _add_topic_header(self, topic: str):
        self._chat_append(f"\n{'─'*20} Tema: {topic} {'─'*20}\n\n", "topic_hdr")

    def _clear_chat(self):
        self.chat_txt.configure(state=tk.NORMAL)
        self.chat_txt.delete("1.0", tk.END)
        self.chat_txt.configure(state=tk.DISABLED)

    # ── Status bar ────────────────────────────────────────────────────────────

    def _update_status(self, msg: str):
        self.status_var.set(msg)

    def _set_thinking(self, on: bool):
        self.thinking_label.configure(text="⏳ pensando…" if on else "")
        self.send_btn.configure(state="disabled" if on else "normal")

    def _check_api(self):
        try:
            count = fetch_graph_count(self.api)
            self.after(0, self._update_status, f"✓ {count} tripletas en grafo")
        except Exception:
            self.after(0, self._update_status, "⚠ API no disponible")

    # ── Topic switching ───────────────────────────────────────────────────────

    def _switch_topic(self, new_topic: str):
        if new_topic == self.current_topic:
            return

        # Save current history
        self.conversations[self.current_topic]["history"] = list(
            self.conversations[self.current_topic]["history"]
        )

        # Summarize old topic in background
        old_topic   = self.current_topic
        old_history = list(self.conversations[old_topic]["history"])
        if old_history:
            threading.Thread(
                target=self._summarize_and_save,
                args=(old_topic, old_history),
                daemon=True,
            ).start()

        self._ensure_topic(new_topic)
        self.current_topic = new_topic
        self._set_active_topic_btn(new_topic)
        self.topic_label.configure(text=f"  Tema: {new_topic}")

        # Load topic context if not cached
        self._clear_chat()
        self._add_topic_header(new_topic)

        hist = self.conversations[new_topic]["history"]
        if hist:
            # Replay existing conversation
            for msg in hist:
                if msg["role"] == "user":
                    self._add_user_message(msg["content"])
                else:
                    self._add_assistant_message(msg["content"])
        else:
            self._add_info(f"Cargando contexto del tema '{new_topic}'…")
            threading.Thread(
                target=self._load_topic_ctx,
                args=(new_topic,),
                daemon=True,
            ).start()

    def _load_topic_ctx(self, topic: str):
        try:
            ctx = fetch_topic_ctx(self.api, topic)
            self.conversations[topic]["topic_ctx"] = ctx
            if ctx:
                n = len([l for l in ctx.splitlines() if l.strip()])
                self.after(0, self._add_info, f"{n} elementos cargados desde el grafo")
            else:
                self.after(0, self._add_info, f"Sin información previa sobre '{topic}' en el grafo")
        except Exception as e:
            self.after(0, self._add_warn, f"Sin contexto previo: {e}")

    def _summarize_and_save(self, topic: str, history: list):
        convo = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history[-12:])
        prompt = f"""Resume en 2-3 frases los hechos clave de esta conversación sobre '{topic}'.
Solo hechos concretos útiles para recordar. Sin preámbulos.
Luego añade "ENTIDADES:" con los nombres propios mencionados separados por coma.

Conversación:
{convo}

Respuesta:"""
        try:
            resp = self.llm.chat.completions.create(
                model=self.model,
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
                save_note(self.api, topic, summary, entities, self.session_id)
        except Exception:
            pass

    # ── Send message ──────────────────────────────────────────────────────────

    def _on_enter(self, event):
        self._send()
        return "break"

    def _send(self):
        text = self.input_box.get("1.0", tk.END).strip()
        if not text:
            return
        self.input_box.delete("1.0", tk.END)
        self._add_separator()
        self._add_user_message(text)
        self._set_thinking(True)
        threading.Thread(
            target=self._process_message, args=(text,), daemon=True
        ).start()

    def _process_message(self, text: str):
        topic = self.current_topic
        conv  = self.conversations[topic]

        # 1. Retrieve context
        context = ""
        try:
            context = fetch_context(self.api, text)
        except Exception as e:
            self.after(0, self._add_warn, f"Retrieval: {e}")

        # 2. Build messages
        messages = [{"role": "system", "content": SYSTEM_BASE}]
        if conv["topic_ctx"]:
            messages.append({"role": "system",
                             "content": f"Contexto inicial del tema:\n{conv['topic_ctx']}"})
        if context:
            messages.append({"role": "system",
                             "content": f"Contexto relevante de memoria:\n{context}"})
        else:
            messages.append({"role": "system",
                             "content": "No tienes contexto relevante. Si el usuario pregunta algo personal, pregúntaselo."})
        messages += conv["history"][-8:]
        messages.append({"role": "user", "content": text})

        # 3. LMStudio reply
        try:
            resp = self.llm.chat.completions.create(
                model=self.model, messages=messages, temperature=0.7
            )
            reply = resp.choices[0].message.content.strip()
            conv["history"].append({"role": "user",      "content": text})
            conv["history"].append({"role": "assistant", "content": reply})
            self.after(0, self._add_assistant_message, reply)
        except Exception as e:
            self.after(0, self._add_warn, f"LMStudio: {e}")
            self.after(0, self._set_thinking, False)
            return

        # 4. Extract triples and store
        try:
            triples = store_message(self.api, text)
            if triples:
                self.after(0, self._add_memory_tag, triples)
                self.after(0, self._check_api)
        except Exception as e:
            self.after(0, self._add_warn, f"Store: {e}")

        self.after(0, self._set_thinking, False)

    # ── Sidebar actions ───────────────────────────────────────────────────────

    def _new_conversation(self):
        dlg = NewTopicDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            topic = dlg.result.strip().lower().replace(" ", "_")
            self._ensure_topic(topic)
            self._refresh_conv_buttons()
            self._switch_topic(topic)

    def _open_viz(self):
        webbrowser.open(f"{self.api}/viz")

    def _show_profile(self):
        def _fetch():
            try:
                triples = fetch_profile(self.api)
                rows = [(t["subject"], t["predicate"], t["object"]) for t in triples]
                self.after(0, lambda: TableDialog(
                    self,
                    f"Perfil completo — {len(triples)} tripletas",
                    ["Sujeto", "Predicado", "Objeto"],
                    rows,
                ))
            except Exception as e:
                self.after(0, messagebox.showerror, "Error", str(e))
        threading.Thread(target=_fetch, daemon=True).start()

    def _show_notes(self):
        def _fetch():
            try:
                notes = fetch_notes(self.api)
                rows = [
                    (n["topic"], n["summary"][:60] + "…" if len(n["summary"]) > 60 else n["summary"],
                     ", ".join(n.get("entities", [])))
                    for n in notes
                ]
                self.after(0, lambda: TableDialog(
                    self,
                    f"Notas de conversación — {len(notes)}",
                    ["Tema", "Resumen", "Entidades"],
                    rows,
                ))
            except Exception as e:
                self.after(0, messagebox.showerror, "Error", str(e))
        threading.Thread(target=_fetch, daemon=True).start()

    def _clear_graph(self):
        if messagebox.askyesno(
            "Borrar grafo",
            "¿Borrar TODO el grafo? Esta acción no se puede deshacer.",
            icon="warning",
        ):
            def _do():
                try:
                    httpx.delete(f"{self.api}/graph", timeout=10)
                    self.after(0, self._update_status, "Grafo borrado")
                    self.after(0, self._add_info, "Grafo borrado completamente.")
                except Exception as e:
                    self.after(0, messagebox.showerror, "Error", str(e))
            threading.Thread(target=_do, daemon=True).start()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api",      default=API)
    parser.add_argument("--lmstudio", default=LMSTUDIO)
    parser.add_argument("--model",    default="local-model")
    args = parser.parse_args()

    app = GraphMemoryApp(args.api, args.lmstudio, args.model)
    app.mainloop()


if __name__ == "__main__":
    main()
