# API

Все ответы — JSON в UTF-8.

## Публичные

| Метод и путь | Описание |
|---|---|
| `GET /api/state` | Текущее состояние: хосты, избранное, настройки поиска, статус источников, версия |
| `GET /api/events` | Server-Sent Events: событие `state` с тем же содержимым при каждом изменении; пинг раз в 15 секунд |
| `GET /api/icon/<key>` | Иконка сайта (`image/*`) или `404`. `key` — ключ хоста из `/api/state` |
| `GET /health` | `ok <версия>` |

Пример состояния:

```json
{
  "title": "Мои сервисы",
  "app_version": "1.0.0",
  "version": "3f2a9c1b0d4e",
  "hosts": [{
    "key": "local:1", "source": "Локальный NPM", "custom": false,
    "name": "proxmox", "domain": "proxmox.example.com", "domains": ["proxmox.example.com"],
    "url": "https://proxmox.example.com", "target": "https://192.168.0.200:8006",
    "enabled": true, "ssl": true, "acl": false, "group": "example.com", "description": "", "icon": ""
  }],
  "favorites": ["local:1"],
  "search": { "engine": "google", "custom": [] },
  "sources": [{ "id": "local", "name": "Локальный NPM", "type": "sqlite", "enabled": true, "ok": true, "error": "", "count": 19 }]
}
```

`version` — хеш состояния: меняется, только когда что-то изменилось.

## Требуют пароль администратора

Заголовок `X-Admin-Token: <пароль в URL-кодировке>` (`encodeURIComponent` в JS, `urllib.parse.quote` в Python).
Без пароля или с неверным — `401`.

| Метод и путь | Тело | Описание |
|---|---|---|
| `POST /api/login` | — | Проверка пароля |
| `POST /api/admin/password` | `{"current", "new"}` | Смена пароля (`403` — неверный текущий) |
| `GET /api/config` | — | Настройки без паролей + статус OpenBao |
| `PUT /api/config/general` | `{"title", "show_disabled", "search_engine", "custom_engines"}` | Общие настройки |
| `PUT /api/config/sources` | `{"sources": [...]}` | Полный список источников; пустой `password` — оставить сохранённый |
| `POST /api/sources/test` | источник | Проверка подключения: `{"ok", "count"}` или `{"ok": false, "error"}` |
| `POST /api/sites` | `{"name", "url", "group", "description", "icon"}` | Добавить свой сайт |
| `PUT /api/sites/<id>` | то же | Изменить свой сайт |
| `DELETE /api/sites/<id>` | — | Удалить свой сайт (и из избранного) |
| `POST /api/favorites` | `{"key", "on"}` | Добавить или убрать из избранного |

Пример:

```bash
curl -s -X POST http://localhost:8088/api/favorites \
  -H "X-Admin-Token: $(python3 -c 'import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))' 'пароль')" \
  -H 'Content-Type: application/json' -d '{"key":"local:1","on":true}'
```

Ошибки: `{"error": "текст"}` с кодом `400`, `401`, `403`, `404` или `500`.
