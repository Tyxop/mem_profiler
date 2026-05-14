from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .models import (
    ConversationInput,
    QueryInput,
    ContextResponse,
    StoreResponse,
    ProfileBranch,
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
            graph.store_triple(t)
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


@app.delete("/triple", summary="Elimina una tripleta específica del grafo")
def delete_triple(subject: str, predicate: str, object: str):
    graph.delete_triple(subject, predicate, object)
    return {"deleted": True}


@app.get("/health")
def health():
    return {"status": "ok"}
