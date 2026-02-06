# Деплой на VPS Timeweb (Ubuntu) с Docker

Инструкция по развёртыванию Telegram Dating App на VPS с Ubuntu (в т.ч. Timeweb Cloud).

**Подробная инструкция по SSH и Nginx (подключение с Windows, настройка HTTPS, прокси):** см. **[SSH-AND-NGINX.md](SSH-AND-NGINX.md)** в этой же папке.

## Требования

- VPS с **Ubuntu 22.04** (или 24.04)
- Доступ по SSH
- Домен (опционально; можно использовать IP)

## 1. Подготовка сервера (один раз)

Подключитесь по SSH и выполните:

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker (официальный способ)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# Группа docker применится только после нового входа. Сделайте:
#   1. В текущей сессии наберите:  exit   (или Ctrl+D)
#   2. Подключитесь по SSH снова:  ssh user@ваш_сервер
# После этого команда  docker  будет работать без sudo.

# Установка Docker Compose (плагин)
sudo apt install -y docker-compose-plugin
```

Проверка:

```bash
docker --version
docker compose version
```

После установки скрипт может вывести предупреждение про «Docker daemon» и «root access». Для личного VPS это нормально: доступ к Docker даёт расширенные права на сервер, поэтому важно защищать SSH (ключи, надёжный пароль) и не добавлять в группу `docker` посторонних. Режим rootless (rootless mode) безопаснее, но для одного сервера с одним владельцем стандартная установка обычно достаточна.

## 2. Клонирование проекта

```bash
cd ~
git clone https://github.com/YOUR_USER/telegram-dating-app.git
cd telegram-dating-app
```

Либо загрузите архив проекта через SFTP/SCP.

## 3. Переменные окружения

Создайте файл `.env` в корне проекта (рядом с `docker-compose.yml`):

```bash
cp .env.example .env
nano .env
```

Заполните (обязательно):

| Переменная | Описание | Пример |
|------------|----------|--------|
| `BOT_TOKEN` | Токен бота от @BotFather | `7123456789:AAH...` |
| `ADMINS` | ID админов через запятую | `123456789,987654321` |
| `POSTGRES_USER` | Пользователь PostgreSQL | `postgres` |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL (смените!) | `ваш_надёжный_пароль` |
| `POSTGRES_DB` | Имя БД | `dating` |

Опционально:

| Переменная | Описание |
|------------|----------|
| `MINI_APP_URL` | Публичный URL Mini App (для кнопки «Открыть приложение» в боте), например `https://yourdomain.com` |
| `FRONTEND_PORT` | Порт веб-приложения на хосте (по умолчанию 80) |
| `BROADCAST_LIMIT` | Лимит рассылки (по умолчанию 1000) |
| `ADDITIONAL_CORS_ORIGINS` | Доп. CORS origins через запятую |
| `VITE_API_URL` | Оставьте пустым, если фронт и API на одном домене; иначе укажите полный URL API |

Пример `.env`:

```env
BOT_TOKEN=7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ADMINS=123456789
POSTGRES_USER=postgres
POSTGRES_PASSWORD=СложныйПароль123
POSTGRES_DB=dating
MINI_APP_URL=https://yourdomain.com
FRONTEND_PORT=80
```

## 4. Запуск

```bash
docker compose up -d --build
```

Проверка контейнеров:

```bash
docker compose ps
```

Логи:

```bash
docker compose logs -f
# или по сервисам:
docker compose logs -f backend
docker compose logs -f frontend
```

## 5. Доступ к приложению

- **Сайт (Mini App):** `http://ВАШ_IP` или `http://ваш_домен` (порт 80, если не меняли `FRONTEND_PORT`).
- **API:** доступен по тому же адресу по пути `/api/` (проксируется nginx на backend).

Если порт 80 занят или нужен другой порт, задайте в `.env`:

```env
FRONTEND_PORT=8080
```

Тогда Mini App будет по `http://ВАШ_IP:8080`.

## 6. HTTPS (рекомендуется для продакшена)

На Ubuntu можно поставить Nginx на хост и использовать Let's Encrypt (Certbot), а Docker-контейнеры слушать на внутренних портах.

Вариант 1 — Nginx на хосте:

1. Установите Nginx и Certbot:
   ```bash
   sudo apt install -y nginx certbot python3-certbot-nginx
   ```
2. Настройте виртуальный хост с проксированием на `127.0.0.1:80` (или на `FRONTEND_PORT`).
3. Выпустите сертификат: `sudo certbot --nginx -d yourdomain.com`.

Вариант 2 — Traefik или Caddy в Docker как reverse proxy (описание выносится в отдельную инструкцию при необходимости).

После настройки HTTPS укажите в `.env`:

```env
MINI_APP_URL=https://yourdomain.com
```

И в BotFather укажите HTTPS-URL для Mini App.

## 7. Обновление проекта

```bash
cd ~/telegram-dating-app
git pull
docker compose up -d --build
```

## 8. Остановка и удаление

```bash
docker compose down
# С удалением тома БД (осторожно — потеря данных):
docker compose down -v
```

## Структура контейнеров

| Сервис | Описание | Порт (внутренний) |
|--------|----------|--------------------|
| `postgres` | PostgreSQL 16 | 5432 (внутри сети) |
| `backend` | FastAPI + Telegram-бот | 8000 (внутри сети) |
| `frontend` | Nginx + статика Mini App, прокси `/api` на backend | 80 → хост |

Данные PostgreSQL хранятся в Docker-томе `postgres_data` и сохраняются при перезапуске контейнеров.

## Возможные проблемы

- **Бот не отвечает:** проверьте `BOT_TOKEN` и логи `docker compose logs backend`.
- **Ошибка подключения к БД:** дождитесь готовности PostgreSQL (healthcheck), перезапустите: `docker compose restart backend`.
- **CORS при отдельном домене для API:** задайте `ADDITIONAL_CORS_ORIGINS=https://your-miniapp-domain.com` и при необходимости `VITE_API_URL=https://api.yourdomain.com` при сборке фронта.

Если нужен отдельный домен для API (например `api.yourdomain.com`), соберите фронт с `VITE_API_URL=https://api.yourdomain.com` и настройте на сервере проксирование этого домена на контейнер `backend:8000`.
