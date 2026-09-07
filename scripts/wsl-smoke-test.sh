#!/usr/bin/env bash
set -e
PASS=$(grep '^PERSEUS_ADMIN_PASSWORD=' ~/perseus/.env | cut -d= -f2- | tr -d '\r\n')
echo "== admin 行 =="
docker exec perseus-postgres psql -U perseus -d perseus -c "SELECT username, email, length(password) AS pw_len, is_active FROM users WHERE username='admin';" 2>/dev/null || \
docker exec perseus-postgres psql -U perseus -d perseus -c "SELECT username, email, length(password) AS pw_len FROM users WHERE username='admin';"
echo "== login =="
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d "$(printf '{"username":"admin","password":"%s"}' "$PASS")" | cut -c1-160
echo
