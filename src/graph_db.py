import os
from neo4j import GraphDatabase
from .models import Triple

BRANCHES = {
    "perfil": ["PERSONA", "EDAD", "NOMBRE", "GENERO"],
    "ubicacion": ["LUGAR", "VIVE_EN", "TRABAJA_EN", "CIUDAD", "PAIS"],
    "preferencias": ["PREFIERE", "GUSTA", "DETESTA", "COMIDA", "MUSICA", "HOBBIE"],
    "relaciones": ["FAMILIA", "AMIGO", "PAREJA", "TRABAJO", "CONOCE"],
    "mascotas": ["MASCOTA", "PERRO", "GATO", "TIENE_MASCOTA"],
    "salud": ["ESTADO", "CONDICION", "ENFERMEDAD", "MEDICACION"],
    "trabajo": ["TRABAJO", "PROFESION", "EMPRESA", "ROL"],
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
            try:
                s.run(
                    "CREATE FULLTEXT INDEX entity_search IF NOT EXISTS "
                    "FOR (e:Entity) ON EACH [e.name, e.type]"
                )
            except Exception:
                pass

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

    def search_nodes(self, query: str, limit: int = 5) -> list[str]:
        """Fulltext search, falls back to CONTAINS if index missing."""
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
            # Fallback: simple CONTAINS
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
        """BFS expansion up to `hops` from seed nodes, returns triples."""
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

        # Deduplicate
        seen = set()
        unique = []
        for t in all_triples:
            key = (t["subject"], t["predicate"], t["object"])
            if key not in seen:
                seen.add(key)
                unique.append(t)
        return unique

    def get_branch(self, branch_name: str) -> list[dict]:
        """Return triples related to a semantic branch."""
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

    def delete_node(self, name: str):
        with self.driver.session() as s:
            s.run(
                "MATCH (e:Entity {name: $name}) DETACH DELETE e",
                name=name,
            )

    def clear_all(self):
        with self.driver.session() as s:
            s.run("MATCH (e:Entity) DETACH DELETE e")

    def close(self):
        self.driver.close()
