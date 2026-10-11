# Home

Стартовая страница для домашней лаборатории: карточки всех сайтов из [Nginx Proxy Manager](https://nginxproxymanager.com/),
свои сайты, избранное и строка поиска. Обновляется на лету, без перезагрузки страницы.

[Релизы](https://github.com/sbrw-evc/Home/releases) · [Образ](https://github.com/sbrw-evc/Home/pkgs/container/home) · [Wiki](https://github.com/sbrw-evc/Home/wiki)

## Возможности

- **Сайты из NPM** — локальная база `database.sqlite` (только чтение) и/или удалённые NPM через REST API.
- **Обновление на лету** через Server-Sent Events: изменения в NPM появляются за пару секунд, изменённые карточки подсвечиваются.
- **Поиск** с автофокусом и выбором поисковой системы: при вводе фильтрует карточки, `Enter` ищет в интернете.
- **Свои сайты и избранное** — хранятся на сервере, одинаково на всех устройствах.
- **Иконки сайтов** ищутся на сервере: `<link rel="icon">`, манифест, `/favicon.ico`, в том числе через бэкенд NPM.
- **Секреты только в [OpenBao](https://openbao.org/)**: логины и пароли удалённых NPM и пароль администратора.
- Настройки, проверка подключения и смена пароля — в интерфейсе.
- Без зависимостей: Python 3 stdlib + vanilla JS. Образ для `linux/amd64` и `linux/arm64`.

## Быстрый старт

```bash
curl -L https://github.com/sbrw-evc/Home/releases/download/v1.0.0/home-1.0.0-deploy.tar.gz | tar xz
cd home-1.0.0
cp .env.example .env          # NPM_DATA_DIR — каталог data локального NPM
./openbao/setup.sh            # OpenBao рядом с Home: ключи в /root/openbao-init.json, AppRole в .env
docker compose -f docker-compose.yml -f docker-compose.openbao.yml up -d
```

Страница — `http://<хост>:8088`, настройки — `#/settings`.

> Сохраните `/root/openbao-init.json` (ключ распечатки и root-токен) в менеджере паролей и удалите с сервера.
> После перезапуска OpenBao распечатайте его: `./openbao/unseal.sh`.

Без OpenBao: задайте `ADMIN_PASSWORD` в `.env` и запустите `docker compose up -d` — всё, кроме удалённых NPM, будет работать.

## Документация

| | |
|---|---|
| [Установка](https://github.com/sbrw-evc/Home/wiki/Установка) | Варианты установки, первый вход, обновление |
| [Настройка](https://github.com/sbrw-evc/Home/wiki/Настройка) | Переменные окружения и `config.json` |
| [Источники NPM](https://github.com/sbrw-evc/Home/wiki/Источники-NPM) | Локальная база и удалённые NPM |
| [OpenBao](https://github.com/sbrw-evc/Home/wiki/OpenBao) | Хранение секретов, политика, AppRole |
| [Безопасность](https://github.com/sbrw-evc/Home/wiki/Безопасность) | Пароль администратора и рекомендации |
| [API](https://github.com/sbrw-evc/Home/wiki/API) | REST API и SSE |
| [Решение проблем](https://github.com/sbrw-evc/Home/wiki/Решение-проблем) | Диагностика |

Исходники wiki — в [`docs/wiki`](docs/wiki).
