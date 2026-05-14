# Graph Memory System

Sistema de memoria persistente en grafo para conversaciones con LLMs. Almacena hechos como tripletas **Sujeto → Predicado → Objeto** en Neo4j, usa LMStudio como LLM local para extraer y recuperar contexto compacto, y guarda notas de conversación para información que no encaja en el grafo.

## Arquitectura

```
Mensaje de usuario
      │
      ▼
 LMStudio — extrae intención y tripletas S-P-O
      │
      ▼
   Neo4j — almacena entidades, relaciones y notas
      │
      ▼
 Búsqueda inteligente + BFS multi-hop
      │  contexto compacto
      ▼
 LMStudio — responde usando memoria o pregunta si falta info
```

Cada hecho se guarda como tripleta:
```
(Usuario) --[TIENE_MASCOTA]--> (Toby)
(Toby)    --[ES_UN]---------> (Perro)
(Toby)    --[TIENE_ESTADO]--> (Enfermo)
(Usuario) --[VIVE_EN]-------> (Madrid)
```

Los hechos que no encajan en S-P-O (resúmenes de conversación, contexto narrativo) se guardan como **MemoryNote** con timestamp, tema y entidades vinculadas.

## Características

- **Extracción automática**: LMStudio convierte cada mensaje en tripletas permanentes
- **Recuperación inteligente**: extrae la intención de la pregunta para buscar en el grafo los nodos correctos (no solo palabras literales)
- **Upsert**: predicados singulares (VIVE_EN, TRABAJA_EN…) actualizan el valor en lugar de duplicarlo
- **Cambio de tema**: limpia el historial corto del LLM, guarda un resumen como nota y carga el contexto del nuevo tema desde el grafo
- **Notas de conversación**: metadata enriquecida para información narrativa vinculada a nodos
- **Visualizador interactivo**: grafo 2D en el navegador con editor de nodos y relaciones
- **Chat CLI visual**: interfaz con colores, paneles y tablas via Rich

## Requisitos

- [Docker](https://www.docker.com/) y Docker Compose
- [LMStudio](https://lmstudio.ai/) corriendo en `localhost:1234` con un modelo cargado
- Python 3.11+ (solo para el CLI de chat)

## Instalación

```bash
git clone https://github.com/Tyxop/mem_profiler.git
cd mem_profiler

# Configuración
cp .env.example .env
# Editar .env con el nombre del modelo activo en LMStudio

# Arrancar Neo4j + API
make up

# Instalar dependencias del chat CLI
pip install rich httpx openai

# Iniciar el chat
python chat.py --model "nombre-del-modelo"
```

Para desarrollo local (Neo4j en Docker + API sin contenedor):

```bash
make dev
```

## Chat CLI

```
╔══════════════════════════════╗
║  ⬡  Graph Memory Chat        ║
╚══════════════════════════════╝

┌─ Comandos ─────────────────────────────────────────────────────────┐
│ /tema <nombre>   Cambiar tema: guarda resumen, limpia historial    │
│ /profile         Muestra todo el grafo de memoria                  │
│ /branch <rama>   Ver rama semántica del grafo                      │
│ /notas [tema]    Lista notas de conversación guardadas             │
│ /quit            Salir                                             │
└────────────────────────────────────────────────────────────────────┘
```

**Colores:**
- `Azul` — mensajes del usuario
- `Verde` — respuestas del asistente
- `Amarillo` — tripletas guardadas en memoria

**Cambio de tema:**
```
Tú › /tema mascotas

  ℹ  Guardando resumen del tema 'programacion'...
  ✓  Nota guardada para 'programacion': El usuario trabaja con Python...
  ℹ  Cargando contexto del tema 'mascotas' desde el grafo...
  ✓  6 tripletas + 1 nota anterior cargadas

──────── Tema: mascotas ────────
```

## Visualizador interactivo

Abre **http://localhost:8000/viz** para explorar el grafo visualmente.

- **Física simulada** — nodos con repulsión y resortes
- **Click en nodo** → panel lateral con todas sus relaciones
- **✏ Editar** — renombra cualquier nodo inline (ej: Madrid → Barcelona)
- **✕ Eliminar** — borra nodos o relaciones individuales
- **+ Relación** — añade tripletas manualmente con formulario
- **Borrar todo** — limpia el grafo con confirmación
- **Refresco automático** cada 5 segundos

Colores por tipo: `PERSONA` (estrella azul) · `MASCOTA` (naranja) · `LUGAR` (verde) · `HOBBIE` (morado) · `CONDICION` (rojo) · `TRABAJO` (turquesa)

**Neo4j Browser:** http://localhost:7474 — usuario: `neo4j`, contraseña: `graphmemory`

## API REST

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/conversation` | Extrae tripletas de un mensaje y las guarda |
| `POST` | `/query` | Recupera contexto compacto para una consulta |
| `GET`  | `/branch/{rama}` | Recupera una rama semántica |
| `GET`  | `/topic/{nombre}/context` | Tripletas + notas para iniciar conversación sobre un tema |
| `GET`  | `/profile` | Todo el grafo |
| `GET`  | `/branches` | Lista de ramas disponibles |
| `POST` | `/api/triple` | Añade una tripleta manual |
| `PATCH`| `/node/{nombre}` | Renombra un nodo |
| `DELETE`| `/node/{nombre}` | Elimina un nodo y sus relaciones |
| `DELETE`| `/triple` | Elimina una relación específica |
| `DELETE`| `/graph` | Borra todo el grafo |
| `POST` | `/memory/note` | Guarda una nota de conversación |
| `GET`  | `/memory/notes` | Lista notas guardadas |
| `GET`  | `/viz` | Visualizador interactivo del grafo |
| `GET`  | `/api/graph` | Datos del grafo en formato vis-network |

## Ramas semánticas

| Rama | Contenido |
|------|-----------|
| `perfil` | Nombre, edad, género |
| `ubicacion` | Dónde vive, ciudad, país |
| `trabajo` | Profesión, empresa, rol |
| `salud` | Condiciones, enfermedades, medicación |
| `relaciones` | Amigos, familia, pareja |
| `mascotas` | Mascotas personales del usuario |
| `mascotas_especie` | Especie, raza, tipo de animal |
| `mascotas_salud` | Estado de salud de la mascota |
| `mascotas_comportamiento` | Preferencias, juegos, comida |
| `preferencias` | Gustos y aversiones generales |
| `comida` | Dieta, alergias, preferencias alimentarias |
| `tecnologia` | Lenguajes, herramientas, proyectos |

## Comandos make

```bash
make up          # Arranca todo con Docker
make down        # Para los contenedores
make dev         # Solo Neo4j en Docker + API local
make logs        # Logs de la API
make test-store  # Prueba guardar un mensaje
make test-query  # Prueba recuperar contexto
make test-branch # Prueba rama de mascotas
make test-profile # Ver el grafo completo
```

## Stack

- **FastAPI** — API REST
- **Neo4j 5.15 + APOC** — base de datos de grafos (Docker)
- **LMStudio** — LLM local (API OpenAI-compatible, `localhost:1234`)
- **vis-network** — visualización del grafo en el navegador
- **Rich** — interfaz visual del chat CLI
- **Docker Compose** — orquestación

## Licencia

MIT
