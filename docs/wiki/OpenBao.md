# OpenBao

Логины и пароли удалённых NPM и пароль администратора Home хранятся только в [OpenBao](https://openbao.org/) —
открытом форке HashiCorp Vault. В `config.json` их нет.

| Что | Путь (KV v2) | Ключи |
|---|---|---|
| Учётные данные удалённого NPM | `secret/npm-dashboard/sources/<id источника>` | `email`, `password` |
| Пароль администратора | `secret/npm-dashboard/admin` | `password` |

Секреты источников Home создаёт и удаляет сам при сохранении настроек.

## OpenBao рядом с Home

Каталог `openbao/` содержит compose-файл (файловое хранилище, порт только на `127.0.0.1:8200`) и скрипты.

```bash
./openbao/setup.sh
docker compose -f docker-compose.yml -f docker-compose.openbao.yml up -d
```

`setup.sh` (можно запускать повторно):

1. создаёт docker-сеть `openbao` и запускает контейнер;
2. инициализирует OpenBao (1 ключ распечатки) и сохраняет ключ и root-токен в `/root/openbao-init.json` с правами `600`;
3. распечатывает его;
4. включает KV v2 на `secret/`, создаёт политику `npm-dashboard` и AppRole;
5. прописывает `BAO_ADDR`, `BAO_ROLE_ID`, `BAO_SECRET_ID` в `.env` (остальные строки не трогает);
6. генерирует пароль администратора, если его ещё нет.

> **Сохраните `/root/openbao-init.json` в менеджере паролей и удалите с сервера.** Без ключа распечатки данные не восстановить.

### После перезапуска

OpenBao после рестарта запечатан. Пока он запечатан, локальный NPM на странице работает, а удалённые NPM и настройки — нет.

```bash
./openbao/unseal.sh     # возьмёт ключ из /root/openbao-init.json или спросит его
```

## Свой OpenBao

Политика:

```hcl
path "secret/data/npm-dashboard/*"     { capabilities = ["create", "read", "update"] }
path "secret/metadata/npm-dashboard/*" { capabilities = ["delete"] }
path "auth/token/lookup-self"          { capabilities = ["read"] }
```

AppRole:

```bash
bao policy write npm-dashboard npm-dashboard.hcl
bao auth enable approle
bao write auth/approle/role/npm-dashboard token_policies=npm-dashboard token_ttl=1h token_max_ttl=24h
bao read auth/approle/role/npm-dashboard/role-id
bao write -f auth/approle/role/npm-dashboard/secret-id
```

Укажите в `.env` `BAO_ADDR`, `BAO_ROLE_ID`, `BAO_SECRET_ID`. Если OpenBao в другой docker-сети или на другом хосте —
используйте его адрес, для самоподписанного сертификата `BAO_SKIP_VERIFY=true`.

Home сам перелогинивается через AppRole, когда токен истекает. Статус подключения виден в **Настройки → Источники NPM**.
