from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from .viz_html import VIZ_HTML

from .models import (
    ConversationInput,
    QueryInput,
    ContextResponse,
    StoreResponse,
    ProfileBranch,
    Triple,
)
from .graph_db import GraphMemory, BRANCHES
from .llm_client import LMStudioClient
from .retriever import Retriever

graph: GraphMemory
llm: LMStudioClient
retriever: Retriever


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph, llm, retriever
    graph = GraphMemory()
    llm = LMStudioClient()
    retriever = Retriever(graph, llm)
    yield
    graph.close()


app = FastAPI(
    title="Graph Memory API",
    description="Sistema de memoria en grafo usando LMStudio + Neo4j",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/conversation", response_model=StoreResponse, summary="Procesa un mensaje y extrae tripletas al grafo")
def process_conversation(body: ConversationInput):
    """
    Recibe un mensaje de conversación, lo pasa por LMStudio para extraer
    tripletas S-P-O y las almacena en Neo4j.
    """
    triples = llm.extract_triples(body.message)
    stored = 0
    for t in triples:
        try:
            graph.upsert_triple(t)
            stored += 1
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error guardando tripleta: {e}")

    return StoreResponse(
        triples_extracted=len(triples),
        triples_stored=stored,
        triples=triples,
    )


@app.post("/query", response_model=ContextResponse, summary="Recupera contexto relevante para una consulta")
def query_context(body: QueryInput):
    """
    Busca en el grafo los nodos más relevantes para la consulta,
    expande el vecindario y devuelve un contexto compacto listo para inyectar al LLM.
    """
    return retriever.retrieve(
        query=body.query,
        max_hops=body.max_hops,
        max_nodes=body.max_nodes,
    )


@app.get("/branch/{branch_name}", response_model=ProfileBranch, summary="Recupera una rama semántica del grafo")
def get_branch(branch_name: str):
    """
    Devuelve todos los tripletas de una rama temática del perfil.
    Ramas disponibles: perfil, ubicacion, preferencias, relaciones, mascotas, salud, trabajo
    """
    if branch_name not in BRANCHES:
        raise HTTPException(
            status_code=404,
            detail=f"Rama '{branch_name}' no encontrada. Disponibles: {list(BRANCHES.keys())}",
        )
    triples = graph.get_branch(branch_name)
    nodes = list({t["subject"] for t in triples} | {t["object"] for t in triples})
    return ProfileBranch(branch=branch_name, nodes=[{"name": n} for n in nodes], triples=triples)


@app.get("/profile", summary="Muestra todo el grafo de memoria")
def get_full_profile():
    """Devuelve todas las tripletas almacenadas en el grafo."""
    triples = graph.get_all_triples()
    return {"total": len(triples), "triples": triples}


@app.get("/branches", summary="Lista las ramas semánticas disponibles")
def list_branches():
    return {"branches": list(BRANCHES.keys()), "keywords": BRANCHES}


@app.get("/branches/auto", summary="Ramas descubiertas automáticamente del grafo")
def auto_branches():
    """
    Devuelve los nodos intermedios del grafo (los que tienen hijos),
    que son las ramas naturales del árbol de conocimiento.
    Estas ramas se generan solas cuando el LLM crea nuevos nodos.
    """
    branches = graph.get_auto_branches()
    return {"total": len(branches), "branches": branches}


@app.get("/subtree/{node_name}", summary="Subárbol de un nodo")
def get_subtree(node_name: str, hops: int = 3):
    """Devuelve todas las tripletas del subárbol que cuelga de un nodo."""
    triples = graph.get_subtree(node_name, hops=hops)
    nodes = list({t["subject"] for t in triples} | {t["object"] for t in triples})
    return {"root": node_name, "triples": triples, "nodes": nodes, "total": len(triples)}


@app.get("/topic/{name}/context", summary="Contexto completo de un tema para iniciar conversación")
def get_topic_context(name: str):
    """Devuelve tripletas + notas de memoria para pre-cargar una conversación sobre ese tema."""
    ctx = graph.get_topic_context(name)
    return {
        "topic": name,
        "triples": ctx["triples"],
        "memory_notes": ctx["notes"],
        "triples_count": len(ctx["triples"]),
        "notes_count": len(ctx["notes"]),
    }


@app.post("/memory/note", summary="Guarda una nota de conversación con metadata")
def save_memory_note(
    topic: str,
    summary: str,
    entities: str = "",
    session_id: str = "default",
):
    entity_list = [e.strip() for e in entities.split(",") if e.strip()]
    note_id = graph.store_memory_note(topic, summary, entity_list, session_id)
    return {"saved": True, "id": note_id}


@app.get("/memory/notes", summary="Lista notas de conversación guardadas")
def get_memory_notes(topic: str = None, limit: int = 20):
    notes = graph.get_memory_notes(topic=topic, limit=limit)
    return {"total": len(notes), "notes": notes}


@app.delete("/triple", summary="Elimina una tripleta específica del grafo")
def delete_triple(subject: str, predicate: str, object: str):
    graph.delete_triple(subject, predicate, object)
    return {"deleted": True}


@app.patch("/node/{name}", summary="Renombra un nodo")
def rename_node(name: str, new_name: str):
    graph.rename_node(name, new_name)
    return {"renamed": True, "from": name, "to": new_name}


@app.delete("/node/{name}", summary="Elimina un nodo y todas sus relaciones")
def delete_node(name: str):
    graph.delete_node(name)
    return {"deleted": True, "node": name}


@app.delete("/graph", summary="Borra todo el grafo")
def clear_graph():
    graph.clear_all()
    return {"cleared": True}


@app.post("/api/triple", summary="Añade una tripleta manual al grafo")
def add_triple_manual(triple: Triple):
    graph.store_triple(triple)
    return {"stored": True, "triple": triple}


@app.get("/viz", response_class=HTMLResponse, summary="Visualización interactiva del grafo")
def viz():
    return VIZ_HTML


@app.get("/api/graph", summary="Datos del grafo en formato vis-network")
def get_graph_data():
    triples = graph.get_all_triples()
    nodes: dict[str, dict] = {}
    edges = []
    for t in triples:
        if t["subject"] not in nodes:
            nodes[t["subject"]] = {"id": t["subject"], "label": t["subject"], "type": t["subject_type"]}
        if t["object"] not in nodes:
            nodes[t["object"]] = {"id": t["object"], "label": t["object"], "type": t["object_type"]}
        edges.append({"from": t["subject"], "to": t["object"], "label": t["predicate"]})
    return {"nodes": list(nodes.values()), "edges": edges}


@app.get("/health")
def health():
    return {"status": "ok"}
