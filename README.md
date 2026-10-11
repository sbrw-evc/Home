# NPM main page

Стартовая страница (SPA) с карточками сайтов из одного или нескольких [Nginx Proxy Manager](https://nginxproxymanager.com/), своими сайтами, избранным и строкой поиска.

## Возможности

- **Несколько источников NPM**: локальная база `database.sqlite` (только чтение) и удалённые NPM через их REST API по интернету.
- **Логины и пароли — только в [OpenBao](https://openbao.org/)** (KV v2). В `config.json` их нет. Пароль администратора дашборда тоже можно хранить в OpenBao.
- **Строка поиска** с выбором поисковой системы (Google, Яндекс, DuckDuckGo, Bing, Startpage и свои), автофокус при открытии:
  - при вводе фильтрует карточки;
  - `Enter` ищет в выбранной системе, а если введён адрес (`example.com`), открывает его;
  - `Ctrl+Enter` открывает первую найденную карточку, `Esc` очищает строку, `/` ставит фокус в поиск.
- **Свои сайты**: можно добавить сайты, которых нет в NPM (название, адрес, группа, описание, иконка).
- **Избранное**: звёздочка на карточке. Избранное хранится на сервере, поэтому одинаково на всех устройствах.
- Обновляется на лету (Server-Sent Events): изменения в NPM, настройках, избранном и своих сайтах появляются без перезагрузки страницы.
- Меню по источникам и доменам, режимы «плитка» и «список», тёмная тема, мобильная вёрстка.
- Без зависимостей: Python 3 stdlib + vanilla JS.

## Запуск

```bash
cp .env.example .env    # заполните BAO_ADDR и BAO_TOKEN или BAO_ROLE_ID/BAO_SECRET_ID
docker compose up -d --build
```

Страница будет доступна на `http://<host>:8088`, настройки — на `#/settings`.

Чтобы подключить локальный NPM, смонтируйте его каталог `data` (тот, что у NPM смонтирован как `/data`):

```yaml
volumes:
  - /path/to/npm/data:/npm:ro
```

Если файл `/npm/database.sqlite` существует, при первом запуске источник «Локальный NPM» добавится сам.

## OpenBao

### Быстрый старт: OpenBao рядом с дашбордом

В каталоге [`openbao/`](openbao) лежат compose-файл OpenBao (файловое хранилище, порт только на `127.0.0.1`) и скрипт настройки:

```bash
./openbao/setup.sh
docker compose -f docker-compose.yml -f docker-compose.openbao.yml up -d --build
```

`setup.sh` можно запускать повторно. Он:
1. запускает OpenBao, инициализирует его и сохраняет ключ распечатки и root-токен в `/root/openbao-init.json` (права 600);
2. включает KV v2 на `secret/`, создаёт политику [`npm-dashboard`](openbao/npm-dashboard.hcl) и AppRole;
3. записывает `BAO_ADDR`, `BAO_ROLE_ID` и `BAO_SECRET_ID` в `/opt/npm-dashboard/.env` (права 600);
4. создаёт случайный пароль администратора в `secret/npm-dashboard/admin`.

> **Важно.** Сохраните содержимое `/root/openbao-init.json` в надёжном месте (например, в менеджере паролей) и удалите файл с сервера. Без ключа распечатки данные OpenBao не восстановить.

После перезапуска OpenBao нужно распечатать. Если файла с ключом на сервере уже нет, скрипт спросит ключ:

```bash
./openbao/unseal.sh
```

Узнать пароль администратора дашборда:

```bash
docker exec -it -e BAO_ADDR=http://127.0.0.1:8200 openbao sh -c 'bao login && bao kv get -field=password secret/npm-dashboard/admin'
```

### Свой OpenBao

Нужен движок секретов KV v2 (по умолчанию `secret/`).

| Что                           | Путь в OpenBao                                  | Ключи              |
|-------------------------------|-------------------------------------------------|--------------------|
| Учётные данные удалённого NPM | `secret/npm-dashboard/sources/<id источника>`   | `email`, `password`|
| Пароль администратора         | `secret/npm-dashboard/admin`                    | `password`         |

Секреты источников дашборд записывает и удаляет сам, когда вы сохраняете источники в настройках. Пароль администратора задаётся вручную:

```bash
bao kv put secret/npm-dashboard/admin password='...'
```

Пример политики для AppRole:

```hcl
path "secret/data/npm-dashboard/*"     { capabilities = ["create", "read", "update"] }
path "secret/metadata/npm-dashboard/*" { capabilities = ["delete"] }
path "auth/token/lookup-self"          { capabilities = ["read"] }
```

```bash
bao policy write npm-dashboard npm-dashboard.hcl
bao auth enable approle
bao write auth/approle/role/npm-dashboard token_policies=npm-dashboard token_ttl=1h token_max_ttl=24h
bao read auth/approle/role/npm-dashboard/role-id
bao write -f auth/approle/role/npm-dashboard/secret-id
```

Если OpenBao не настроен, работают локальная база, свои сайты и избранное. Удалённый NPM без OpenBao добавить нельзя: хранить пароли где-то ещё дашборд не умеет.

> Пароль администратора защищает все изменения (настройки, свои сайты, избранное). Если его нет ни в `ADMIN_PASSWORD`, ни в OpenBao, менять всё может любой, кто открыл страницу.

## Переменные окружения

| Переменная         | По умолчанию              | Описание |
|--------------------|---------------------------|----------|
| `BAO_ADDR`         | —                         | Адрес OpenBao, например `https://bao.example.com:8200` |
| `BAO_TOKEN`        | —                         | Токен OpenBao |
| `BAO_ROLE_ID`, `BAO_SECRET_ID` | —             | Вход через AppRole (вместо токена) |
| `BAO_KV_MOUNT`     | `secret`                  | Точка монтирования KV v2 |
| `BAO_PATH_PREFIX`  | `npm-dashboard/sources`   | Где хранить учётные данные источников |
| `BAO_ADMIN_PATH`   | `npm-dashboard/admin`     | Где лежит пароль администратора |
| `BAO_NAMESPACE`    | —                         | Пространство имён OpenBao |
| `BAO_SKIP_VERIFY`  | `false`                   | Не проверять TLS-сертификат OpenBao |
| `ADMIN_PASSWORD`   | —                         | Пароль администратора (важнее значения из OpenBao) |
| `TITLE`            | `Мои сервисы`             | Заголовок при первом запуске |
| `POLL_SECONDS`     | `2`                       | Как часто проверять локальную базу |
| `API_POLL_SECONDS` | `30`                      | Как часто опрашивать удалённые NPM (можно задать для каждого источника) |
| `CONFIG`           | `/config/config.json`     | Файл настроек |
| `NPM_DB`           | `/npm/database.sqlite`    | Путь к локальной базе по умолчанию |

## API

- `GET /api/state` — хосты, избранное, настройки поиска, статус источников
- `GET /api/events` — поток SSE, событие `state` при каждом изменении
- `GET /health`

Требуют пароль администратора (заголовок `X-Admin-Token`):
`GET /api/config`, `PUT /api/config/general`, `PUT /api/config/sources`, `POST /api/sources/test`,
`POST /api/sites`, `PUT|DELETE /api/sites/<id>`, `POST /api/favorites`.

Если дашборд стоит за прокси, отключите буферизацию для `/api/events`. Приложение уже отправляет для этого заголовок `X-Accel-Buffering: no`.

Поле `meta` хостов NPM, где лежат ключи DNS-провайдеров, дашборд не читает и никуда не передаёт.
