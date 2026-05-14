import os
import time
from neo4j import GraphDatabase
from .models import Triple

SINGULAR_PREDICATES = {
    "VIVE_EN", "TRABAJA_EN", "TIENE_EDAD", "TIENE_PROFESION",
    "TIENE_ESTADO", "FECHA_NACIMIENTO", "TIENE_NOMBRE", "ES_DE",
}

BRANCHES = {
    # Perfil personal
    "perfil":               ["TIENE_NOMBRE", "TIENE_EDAD", "TIENE_GENERO", "FECHA_NACIMIENTO", "ES_DE", "PERSONA"],
    "ubicacion":            ["VIVE_EN", "LUGAR", "CIUDAD", "PAIS", "DIRECCION"],
    "trabajo":              ["TRABAJA_EN", "TIENE_PROFESION", "ROL", "EMPRESA", "TRABAJO", "PROFESION"],
    "salud":                ["TIENE_CONDICION", "TIENE_ENFERMEDAD", "TOMA_MEDICACION", "ALERGIA", "CONDICION", "ENFERMEDAD"],
    "relaciones":           ["CONOCE", "AMIGO", "PAREJA", "TIENE_HIJO", "FAMILIA", "HERMANO", "PADRE", "MADRE"],

    # Mascotas personales (conectadas al usuario)
    "mascotas":             ["TIENE_MASCOTA", "TIENE_ANIMAL", "MASCOTA"],
    "mascotas_especie":     ["ES_UN", "ESPECIE", "RAZA", "TIPO_ANIMAL"],
    "mascotas_salud":       ["TIENE_ESTADO", "ESTADO", "ENFERMEDAD", "MEDICACION"],
    "mascotas_comportamiento": ["PREFIERE", "HOBBIE", "JUEGA_CON", "COME", "DUERME_EN"],

    # Intereses y preferencias
    "preferencias":         ["PREFIERE", "GUSTA", "DETESTA", "FAVORITO", "HOBBIE"],
    "comida":               ["COME", "PREFIERE_COMER", "DETESTA_COMER", "DIETA", "COMIDA", "ALERGIA_COMIDA"],
    "tecnologia":           ["USA", "PROGRAMA_EN", "TRABAJA_CON", "HERRAMIENTA", "LENGUAJE", "REALIZA"],
}


class GraphMemory:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(
                os.getenv("NEO4J_USER", "neo4j"),
                os.getenv("NEO4J_PASSWORD", "graphmemory"),
            ),
        )
        self._init_schema()

    def _init_schema(self):
        with self.driver.session() as s:
            s.run("CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)")
            s.run("CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)")
            s.run("CREATE INDEX memory_topic IF NOT EXISTS FOR (m:MemoryNote) ON (m.topic)")
            try:
                s.run(
                    "CREATE FULLTEXT INDEX entity_search IF NOT EXISTS "
                    "FOR (e:Entity) ON EACH [e.name, e.type]"
                )
            except Exception:
                pass

    # ── Triples ─────────────────────────────────────────────────────────────

    def upsert_triple(self, triple: Triple):
        if triple.predicate in SINGULAR_PREDICATES:
            with self.driver.session() as s:
                s.run(
                    "MATCH (sub:Entity {name: $subject})-[r:RELATION {name: $predicate}]->() DELETE r",
                    subject=triple.subject,
                    predicate=triple.predicate,
                )
        self.store_triple(triple)

    def store_triple(self, triple: Triple):
        with self.driver.session() as s:
            s.run(
                """
                MERGE (sub:Entity {name: $subject})
                SET sub.type = $subject_type, sub.updated_at = timestamp()
                MERGE (obj:Entity {name: $object})
                SET obj.type = $object_type, obj.updated_at = timestamp()
                MERGE (sub)-[r:RELATION {name: $predicate}]->(obj)
                SET r.confidence = $confidence, r.updated_at = timestamp()
                """,
                subject=triple.subject,
                subject_type=triple.subject_type,
                object=triple.object,
                object_type=triple.object_type,
                predicate=triple.predicate,
                confidence=triple.confidence,
            )

    # ── Search & retrieval ───────────────────────────────────────────────────

    def get_nodes_by_predicate(self, predicates: list[str]) -> list[str]:
        with self.driver.session() as s:
            result = s.run(
                """
                MATCH (s:Entity)-[r:RELATION]->(o:Entity)
                WHERE r.name IN $predicates
                RETURN DISTINCT s.name AS name
                UNION
                MATCH (s:Entity)-[r:RELATION]->(o:Entity)
                WHERE r.name IN $predicates
                RETURN DISTINCT o.name AS name
                """,
                predicates=predicates,
            )
            return [r["name"] for r in result]

    def get_nodes_by_type(self, types: list[str]) -> list[str]:
        with self.driver.session() as s:
            result = s.run(
                "MATCH (e:Entity) WHERE e.type IN $types RETURN e.name AS name",
                types=types,
            )
            return [r["name"] for r in result]

    def search_nodes(self, query: str, limit: int = 5) -> list[str]:
        with self.driver.session() as s:
            try:
                result = s.run(
                    """
                    CALL db.index.fulltext.queryNodes('entity_search', $term)
                    YIELD node, score
                    RETURN node.name AS name
                    ORDER BY score DESC LIMIT $limit
                    """,
                    term=query,
                    limit=limit,
                )
                names = [r["name"] for r in result]
                if names:
                    return names
            except Exception:
                pass
            result = s.run(
                """
                MATCH (e:Entity)
                WHERE toLower(e.name) CONTAINS toLower($term)
                   OR toLower(e.type) CONTAINS toLower($term)
                RETURN e.name AS name LIMIT $limit
                """,
                term=query,
                limit=limit,
            )
            return [r["name"] for r in result]

    def get_neighborhood(self, seed_names: list[str], hops: int = 2) -> list[dict]:
        visited = set(seed_names)
        frontier = set(seed_names)
        all_triples = []

        with self.driver.session() as s:
            for _ in range(hops):
                if not frontier:
                    break
                result = s.run(
                    """
                    MATCH (start:Entity)-[r:RELATION]->(end:Entity)
                    WHERE start.name IN $names OR end.name IN $names
                    RETURN start.name AS subject, start.type AS subject_type,
                           r.name AS predicate,
                           end.name AS object, end.type AS object_type
                    """,
                    names=list(frontier),
                )
                rows = [dict(r) for r in result]
                new_frontier = set()
                for row in rows:
                    all_triples.append(row)
                    for n in (row["subject"], row["object"]):
                        if n not in visited:
                            visited.add(n)
                            new_frontier.add(n)
                frontier = new_frontier

        seen = set()
        unique = []
        for t in all_triples:
            key = (t["subject"], t["predicate"], t["object"])
            if key not in seen:
                seen.add(key)
                unique.append(t)
        return unique

    def get_branch(self, branch_name: str) -> list[dict]:
        keywords = BRANCHES.get(branch_name.lower(), [branch_name.upper()])
        with self.driver.session() as s:
            result = s.run(
                """
                MATCH (s:Entity)-[r:RELATION]->(o:Entity)
                WHERE r.name IN $keywords
                   OR s.type IN $keywords
                   OR o.type IN $keywords
                RETURN s.name AS subject, s.type AS subject_type,
                       r.name AS predicate,
                       o.name AS object, o.type AS object_type
                """,
                keywords=keywords,
            )
            return [dict(row) for row in result]

    def get_personal_pet_nodes(self) -> list[str]:
        """Returns node names of the user's own pets."""
        with self.driver.session() as s:
            result = s.run(
                """
                MATCH (u:Entity {name: 'Usuario'})-[r:RELATION]->(pet:Entity)
                WHERE r.name IN ['TIENE_MASCOTA', 'TIENE_ANIMAL']
                RETURN pet.name AS name
                """
            )
            return [r["name"] for r in result]

    def get_all_triples(self) -> list[dict]:
        with self.driver.session() as s:
            result = s.run(
                """
                MATCH (s:Entity)-[r:RELATION]->(o:Entity)
                RETURN s.name AS subject, s.type AS subject_type,
                       r.name AS predicate,
                       o.name AS object, o.type AS object_type
                ORDER BY r.updated_at DESC
                """
            )
            return [dict(row) for row in result]

    # ── Memory notes (metadata de conversación) ──────────────────────────────

    def store_memory_note(
        self,
        topic: str,
        summary: str,
        entity_names: list[str],
        session_id: str = "default",
    ) -> str:
        note_id = f"{session_id}_{int(time.time())}"
        with self.driver.session() as s:
            s.run(
                """
                CREATE (m:MemoryNote {
                    id: $id,
                    session_id: $session_id,
                    topic: $topic,
                    summary: $summary,
                    created_at: timestamp()
                })
                """,
                id=note_id,
                session_id=session_id,
                topic=topic,
                summary=summary,
            )
            for name in entity_names:
                s.run(
                    """
                    MATCH (m:MemoryNote {id: $id})
                    MATCH (e:Entity {name: $name})
                    MERGE (m)-[:ABOUT]->(e)
                    """,
                    id=note_id,
                    name=name,
                )
        return note_id

    def get_memory_notes(self, topic: str = None, limit: int = 20) -> list[dict]:
        with self.driver.session() as s:
            if topic:
                result = s.run(
                    """
                    MATCH (m:MemoryNote) WHERE m.topic = $topic
                    OPTIONAL MATCH (m)-[:ABOUT]->(e:Entity)
                    WITH m, collect(e.name) AS entities
                    RETURN m.id AS id, m.topic AS topic, m.summary AS summary,
                           m.created_at AS created_at, m.session_id AS session_id,
                           entities
                    ORDER BY m.created_at DESC LIMIT $limit
                    """,
                    topic=topic,
                    limit=limit,
                )
            else:
                result = s.run(
                    """
                    MATCH (m:MemoryNote)
                    OPTIONAL MATCH (m)-[:ABOUT]->(e:Entity)
                    WITH m, collect(e.name) AS entities
                    RETURN m.id AS id, m.topic AS topic, m.summary AS summary,
                           m.created_at AS created_at, m.session_id AS session_id,
                           entities
                    ORDER BY m.created_at DESC LIMIT $limit
                    """,
                    limit=limit,
                )
            return [dict(r) for r in result]

    def get_topic_context(self, topic: str) -> dict:
        """Returns graph triples + memory notes for a topic, ready to seed a conversation."""
        branch_triples = self.get_branch(topic)
        notes = self.get_memory_notes(topic=topic, limit=5)

        # For pet topics, also pull personal pet sub-graph
        if "mascota" in topic:
            pet_nodes = self.get_personal_pet_nodes()
            if pet_nodes:
                pet_triples = self.get_neighborhood(pet_nodes, hops=2)
                seen = {(t["subject"], t["predicate"], t["object"]) for t in branch_triples}
                for t in pet_triples:
                    key = (t["subject"], t["predicate"], t["object"])
                    if key not in seen:
                        branch_triples.append(t)
                        seen.add(key)

        return {"triples": branch_triples, "notes": notes}

    # ── Mutations ────────────────────────────────────────────────────────────

    def delete_triple(self, subject: str, predicate: str, object_: str):
        with self.driver.session() as s:
            s.run(
                """
                MATCH (s:Entity {name: $subject})-[r:RELATION {name: $predicate}]->(o:Entity {name: $object})
                DELETE r
                """,
                subject=subject,
                predicate=predicate,
                object=object_,
            )

    def rename_node(self, old_name: str, new_name: str):
        with self.driver.session() as s:
            s.run(
                "MATCH (e:Entity {name: $old}) SET e.name = $new",
                old=old_name,
                new=new_name,
            )

    def delete_node(self, name: str):
        with self.driver.session() as s:
            s.run("MATCH (e:Entity {name: $name}) DETACH DELETE e", name=name)

    def clear_all(self):
        with self.driver.session() as s:
            s.run("MATCH (n) DETACH DELETE n")

    def close(self):
        self.driver.close()
