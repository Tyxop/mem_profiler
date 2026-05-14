.PHONY: up down logs test shell

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f api

neo4j-logs:
	docker compose logs -f neo4j

# Correr solo Neo4j localmente y la API sin Docker
dev:
	docker compose up neo4j -d
	PYTHONPATH=. uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Ejemplos de uso con curl
test-store:
	curl -s -X POST http://localhost:8000/conversation \
	  -H "Content-Type: application/json" \
	  -d '{"message": "Mi perro Toby está enfermo, vive conmigo en Madrid y le encanta jugar"}' | python3 -m json.tool

test-query:
	curl -s -X POST http://localhost:8000/query \
	  -H "Content-Type: application/json" \
	  -d '{"query": "como esta mi mascota?"}' | python3 -m json.tool

test-branch:
	curl -s http://localhost:8000/branch/mascotas | python3 -m json.tool

test-profile:
	curl -s http://localhost:8000/profile | python3 -m json.tool

shell:
	docker compose exec api bash
