#!/bin/bash
set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/neo4j_$TIMESTAMP.dump"

backup() {
  mkdir -p "$BACKUP_DIR"
  echo "Parando Neo4j..."
  docker compose stop neo4j

  echo "Generando backup en $BACKUP_FILE..."
  docker compose run --rm neo4j neo4j-admin database dump neo4j --to-path=/data
  docker run --rm \
    -v mem_profiler_neo4j_data:/data \
    -v "$(pwd)/$BACKUP_DIR":/backup \
    alpine cp /data/neo4j.dump "/backup/neo4j_$TIMESTAMP.dump"

  echo "Reiniciando Neo4j..."
  docker compose start neo4j

  echo "Backup completado: $BACKUP_FILE"
}

restore() {
  if [ -z "$2" ]; then
    echo "Uso: bash backup.sh restore <archivo.dump>"
    echo "Backups disponibles:"
    ls -1 "$BACKUP_DIR"/*.dump 2>/dev/null || echo "  (ninguno)"
    exit 1
  fi

  RESTORE_FILE="$2"
  if [ ! -f "$RESTORE_FILE" ]; then
    echo "Error: archivo no encontrado: $RESTORE_FILE"
    exit 1
  fi

  echo "Parando Neo4j..."
  docker compose stop neo4j

  echo "Copiando dump al volumen..."
  docker run --rm \
    -v mem_profiler_neo4j_data:/data \
    -v "$(pwd)":/backup \
    alpine cp "/backup/$RESTORE_FILE" /data/neo4j.dump

  echo "Restaurando base de datos..."
  docker compose run --rm neo4j neo4j-admin database load neo4j --from-path=/data --overwrite-destination

  echo "Reiniciando Neo4j..."
  docker compose start neo4j

  echo "Restauración completada desde: $RESTORE_FILE"
}

case "$1" in
  backup)  backup "$@" ;;
  restore) restore "$@" ;;
  *)
    echo "Uso: bash backup.sh [backup|restore <archivo.dump>]"
    exit 1
    ;;
esac
