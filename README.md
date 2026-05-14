# Graph Memory System

Sistema de memoria persistente en grafo para conversaciones con LLMs. Almacena hechos como tripletas **Sujeto → Predicado → Objeto** en Neo4j y usa LMStudio como LLM local para extraer y recuperar contexto compacto.

## Arquitectura

```
Mensaje de usuario
      │
      ▼
 LMStudio (extracción)
      │  tripletas S-P-O
      ▼
   Neo4j (grafo)
      │
      ▼
 Búsqueda + BFS multi-hop
      │  contexto compacto
      ▼
 LMStudio (respuesta con memoria)
```

Cada hecho se guarda como tripleta:
```
(Usuario) --[TIENE_MASCOTA]--> (Toby)
(Toby)    --[ES_UN]---------> (Perro)
(Toby)    --[ESTADO]--------> (Enfermo)
(Usuario) --[VIVE_EN]-------> (Madrid)
```

## Requisitos

- [Docker](https://www.docker.com/) y Docker Compose
- [LMStudio](https://lmstudio.ai/) corriendo en `localhost:1234` con un modelo cargado

## Instalación y uso

```bash
# 1. Clonar el repositorio
git clone https://github.com/Tyxop/mem_profiler.git
cd mem_profiler

# 2. Copiar y editar configuración
cp .env.example .env
# Editar .env con el modelo activo en LMStudio

# 3. Arrancar todo con Docker
make up

# 4. Abrir el chat con memoria
python chat.py --model "nombre-del-modelo"
```

Para desarrollo local (Neo4j en Docker + API sin contenedor):

```bash
make dev
```

## API REST

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/conversation` | Extrae tripletas de un mensaje y las guarda |
| `POST` | `/query` | Recupera contexto compacto para una consulta |
| `GET` | `/branch/{rama}` | Recupera una rama semántica del grafo |
| `GET` | `/profile` | Devuelve todo el grafo de memoria |
| `GET` | `/branches` | Lista las ramas disponibles |
| `DELETE` | `/triple` | Elimina una tripleta específica |

### Ramas semánticas disponibles

`perfil` · `ubicacion` · `preferencias` · `relaciones` · `mascotas` · `salud` · `trabajo`

### Ejemplos

```bash
# Guardar un hecho
curl -X POST http://localhost:8000/conversation \
  -H "Content-Type: application/json" \
  -d '{"message": "Mi perro Toby está enfermo, vivo en Madrid"}'

# Recuperar contexto
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "como esta mi mascota?"}'

# Ver rama de mascotas
curl http://localhost:8000/branch/mascotas
```

## Comandos del chat CLI

| Comando | Acción |
|---------|--------|
| `/profile` | Muestra todo el grafo |
| `/branch <nombre>` | Muestra una rama semántica |
| `/quit` | Salir |

## Neo4j Browser

Visualiza el grafo en: `http://localhost:7474`  
Usuario: `neo4j` · Contraseña: `graphmemory`

## Stack

- **FastAPI** — API REST
- **Neo4j 5.15 + APOC** — base de datos de grafos
- **LMStudio** — LLM local (API compatible con OpenAI)
- **Docker Compose** — orquestación

## Licencia

MIT
