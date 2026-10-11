#!/bin/sh
# Распечатать OpenBao после перезапуска. Ключ берется из $INIT_FILE, если он есть, иначе спрашивается.
set -eu
INIT_FILE=${INIT_FILE:-/root/openbao-init.json}
if [ -f "$INIT_FILE" ]; then
  KEY=$(python3 -c "import json; print(json.load(open('$INIT_FILE'))['unseal_keys_b64'][0])")
else
  printf "Ключ распечатки: "; stty -echo; read -r KEY; stty echo; echo
fi
docker exec -e BAO_ADDR=http://127.0.0.1:8200 openbao bao operator unseal "$KEY" | grep -E "^Sealed"
