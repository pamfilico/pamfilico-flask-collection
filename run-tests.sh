#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "Starting test stack..."
docker compose -f docker-compose.test.yml up -d --build

echo "Waiting for PostgreSQL..."
for i in {1..30}; do
  if docker compose -f docker-compose.test.yml exec -T db pg_isready -U test -d testdb 2>/dev/null; then
    echo "PostgreSQL ready."
    break
  fi
  [ $i -eq 30 ] && { echo "PostgreSQL failed."; docker compose -f docker-compose.test.yml down; exit 1; }
  sleep 1
done

echo "Waiting for API..."
for i in {1..30}; do
  if curl -s -o /dev/null -w "%{http_code}" http://localhost:5097/health 2>/dev/null | grep -q 200; then
    echo "API ready."
    break
  fi
  [ $i -eq 30 ] && { echo "API failed."; docker compose -f docker-compose.test.yml down; exit 1; }
  sleep 1
done

export COLLECTION_TEST_API_URL=http://localhost:5097

poetry run pytest -v
EXIT_CODE=$?

docker compose -f docker-compose.test.yml down
echo "Done."
exit $EXIT_CODE
