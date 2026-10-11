#!/bin/sh
# Первичная настройка OpenBao для NPM Dashboard. Можно запускать повторно.
#   - запускает OpenBao, инициализирует (ключ и root-токен -> $INIT_FILE) и распечатывает
#   - включает KV v2 на secret/, создает политику и AppRole npm-dashboard
#   - пишет BAO_* в $ENV_FILE дашборда
#   - создает случайный пароль администратора в secret/npm-dashboard/admin
set -eu
cd "$(dirname "$0")"

INIT_FILE=${INIT_FILE:-/root/openbao-init.json}
ENV_FILE=${ENV_FILE:-/opt/npm-dashboard/.env}

docker network inspect openbao >/dev/null 2>&1 || docker network create openbao >/dev/null
mkdir -p data
# в образе OpenBao процесс работает от пользователя openbao (uid 100)
chown 100:1000 data 2>/dev/null || true
docker compose up -d

bao() { docker exec -i -e BAO_ADDR=http://127.0.0.1:8200 -e BAO_TOKEN="${ROOT_TOKEN:-}" openbao bao "$@"; }
json() { python3 -c "import json,sys; print(json.load(sys.stdin)$1)"; }

i=0
until bao status -format=json >/dev/null 2>&1 || [ $? -eq 2 ]; do
  i=$((i+1)); [ $i -gt 30 ] && { echo "OpenBao не запустился"; exit 1; }; sleep 1
done

if [ "$(bao status -format=json | json "['initialized']")" = "False" ]; then
  umask 077
  bao operator init -key-shares=1 -key-threshold=1 -format=json > "$INIT_FILE"
  echo "OpenBao инициализирован, ключ распечатки и root-токен: $INIT_FILE"
fi

if [ "$(bao status -format=json | json "['sealed']")" = "True" ]; then
  bao operator unseal "$(json "['unseal_keys_b64'][0]" < "$INIT_FILE")" >/dev/null
  echo "OpenBao распечатан"
fi

ROOT_TOKEN=$(json "['root_token']" < "$INIT_FILE")

bao secrets list -format=json | grep -q '"secret/"' || bao secrets enable -path=secret kv-v2 >/dev/null
bao policy write npm-dashboard - < npm-dashboard.hcl >/dev/null
bao auth list -format=json | grep -q '"approle/"' || bao auth enable approle >/dev/null
bao write auth/approle/role/npm-dashboard token_policies=npm-dashboard token_ttl=1h token_max_ttl=24h >/dev/null

ROLE_ID=$(bao read -format=json auth/approle/role/npm-dashboard/role-id | json "['data']['role_id']")
if [ -f "$ENV_FILE" ] && grep -q "^BAO_ROLE_ID=$ROLE_ID" "$ENV_FILE" && grep -q "^BAO_SECRET_ID=." "$ENV_FILE"; then
  echo "AppRole уже прописан в $ENV_FILE"
else
  SECRET_ID=$(bao write -f -format=json auth/approle/role/npm-dashboard/secret-id | json "['data']['secret_id']")
  umask 077
  mkdir -p "$(dirname "$ENV_FILE")"
  cat > "$ENV_FILE" <<EOF
BAO_ADDR=http://openbao:8200
BAO_ROLE_ID=$ROLE_ID
BAO_SECRET_ID=$SECRET_ID
EOF
  echo "AppRole записан в $ENV_FILE"
fi

if ! bao kv get secret/npm-dashboard/admin >/dev/null 2>&1; then
  PW=$(python3 -c "import secrets; print(secrets.token_urlsafe(18))")
  bao kv put secret/npm-dashboard/admin password="$PW" >/dev/null
  echo "Пароль администратора создан: secret/npm-dashboard/admin"
fi

echo "Готово."
