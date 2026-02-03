# 🤖 Знакомства через встречи — Mini App + бот

Приложение для знакомств через совместные мероприятия: **Mini App** (React) + **REST API** (FastAPI) + опционально **Telegram-бот**.

## 📁 Структура проекта

```
telegram-dating-app/
├── backend/                 # Python: API, бот, БД, сервисы
│   ├── api.py              # REST API для Mini App (FastAPI)
│   ├── bot.py              # Telegram-бот (pyTelegramBotAPI)
│   ├── main.py             # Точка входа бота
│   ├── config.py           # Конфигурация
│   ├── database.py         # PostgreSQL
│   ├── models.py           # Модели данных
│   ├── handlers/           # Обработчики бота
│   ├── keyboards/          # Клавиатуры бота
│   ├── services/           # Достижения, рекомендации, уведомления и т.д.
│   ├── utils/              # Вспомогательные функции
│   ├── images/             # Картинки для бота (например Spon.png)
│   ├── requirements.txt
│   └── .env.example        # → скопировать в .env
├── frontend/               # Mini App (React + TypeScript + Vite)
│   ├── src/
│   ├── package.json
│   └── .env.example        # → скопировать в .env (VITE_API_URL)
├── .env.example            # Подсказка: настройка в backend/ и frontend/
├── .gitignore
└── README.md
```

## 🚀 Запуск (localhost)

### 1. Бэкенд (REST API + при желании бот)

```bash
cd backend
cp .env.example .env
# В .env указать: BOT_TOKEN, ADMINS, DATABASE_URL; для проверки без Telegram — ALLOW_DEV_USER_ID=1

# Создать БД PostgreSQL (один раз):
# createdb dating
# или: psql -c "CREATE DATABASE dating;"

pip install -r requirements.txt
```

**Только API (Mini App):**
```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

**Только бот:**
```bash
python main.py
```

Бот и API используют одну БД **PostgreSQL** (строка подключения в `DATABASE_URL`). Таблицы создаются автоматически при первом запуске. Бот и API можно запускать по отдельности.

### 2. Фронтенд (Mini App)

```bash
cd frontend
cp .env.example .env
# В .env указать: VITE_API_URL=http://localhost:8000

npm install
npm run dev
```

Откройте в браузере: **http://localhost:5173**  
Без Telegram запросы идут с заголовком `X-Dev-User-Id` (по умолчанию 1), если в `backend/.env` задано `ALLOW_DEV_USER_ID=1`.

## 🔧 Основной функционал

- **Mini App:** регистрация, профиль, события (поиск, создание, лайки), достижения, реферальная программа.
- **Бот:** те же сценарии в Telegram + админ-панель (`/admin`), рассылки, жалобы и блокировки.

Конфигурация и секреты: `backend/.env` и `frontend/.env`. База данных: **PostgreSQL** (URL в `DATABASE_URL`).

---

## 🌐 Деплой на Render (без файлов в репозитории)

Всё настраивается вручную в [dashboard.render.com](https://dashboard.render.com). Репозиторий подключаете один раз, сервисы создаёте через веб-интерфейс.

### 1. PostgreSQL

- **Dashboard** → **New** → **PostgreSQL**.
- Имя: например `dating-db`, регион — ближайший.
- **Create Database**.

**Откуда взять DATABASE_URL:**
- Откройте созданную БД в списке сервисов.
- В карточке БД найдите блок **Connect** (или **Info**). Там будут строки:
  - **Internal Database URL** — для сервисов, которые работают на Render (API, бот). Именно её используйте как `DATABASE_URL`.
  - **External Database URL** — для подключения с вашего компьютера (например, для миграций с локальной машины).
- Скопируйте **Internal Database URL** целиком (строка вида `postgresql://user:pass@hostname/dbname?...`). Это и есть значение для `DATABASE_URL`.

### 2. Backend (REST API)

- **New** → **Web Service**.
- Подключите репозиторий с проектом.
- Настройки:
  - **Name:** например `dating-api`.
  - **Root Directory:** `backend`.
  - **Runtime:** Python 3.
  - **Build Command:** `pip install -r requirements.txt`
  - **Start Command:** `uvicorn api:app --host 0.0.0.0 --port $PORT`
- **Environment** (вкладка **Environment** в настройках сервиса):
  - Нажмите **Add Environment Variable**.
  - **Обязательно** (иначе ошибка psycopg2 с Python 3.13): **Key:** `PYTHON_VERSION`, **Value:** `3.12.7`.
  - **Key:** `DATABASE_URL`  
  - **Value:** вставьте скопированный **Internal Database URL** из шага 1 (то, что скопировали из блока Connect у PostgreSQL).
  - Добавьте ещё: `BOT_TOKEN` (токен от BotFather), `ADMINS` (ID админов через запятую, например `123456789`).
- **Create Web Service**. Дождитесь деплоя и скопируйте URL сервиса, например `https://dating-api.onrender.com`.

На Render по умолчанию может быть Python 3.13, с которым psycopg2 несовместим. Поэтому **нужно** задать `PYTHON_VERSION` = `3.12.7` в Environment (и для Web Service API, и для Background Worker бота).

### 3. Frontend (Mini App)

- **New** → **Static Site**.
- Тот же репозиторий.
- Настройки:
  - **Name:** например `dating-app`.
  - **Root Directory:** `frontend`.
  - **Build Command:** `npm install && npm run build`
  - **Publish Directory:** `dist`
- **Environment** (обязательно для сборки):
  - `VITE_API_URL` — URL бэкенда из шага 2, например `https://dating-api.onrender.com`.
- **Create Static Site**. После деплоя получите URL статики, например `https://dating-app.onrender.com`.

В Telegram Mini App укажите этот URL (или свой домен, если настроите).

### 4. CORS и «бесконечная загрузка»

- Если фронт открыт по своему URL (например `https://dating-app.onrender.com` в браузере), API должен разрешить этот домен. В **Environment** бэкенда (Web Service) добавьте переменную **`ADDITIONAL_CORS_ORIGINS`** = `https://ваш-static-site.onrender.com` (ваш точный URL Static Site). В коде API уже есть поддержка этой переменной (несколько origins через запятую).
- На фронте добавлен **таймаут 12 секунд** на запрос к API: если сервер не отвечает (например, «засыпает» на бесплатном тарифе Render), загрузка прервётся и появится сообщение об ошибке. Можно нажать «Посмотреть все страницы» и пользоваться демо без API.
- Если открываете приложение **в браузере** (не в Telegram), авторизации не будет — нажмите «Посмотреть все страницы», чтобы войти в демо-режим.

### 5. Бот (по желанию)

- **New** → **Background Worker**.
- Тот же репозиторий.
- **Root Directory:** `backend`.
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python main.py`
- **Environment:** на вкладке **Environment** добавьте те же переменные, что и у API: `DATABASE_URL` (тот же Internal Database URL), `BOT_TOKEN`, `ADMINS`.
- **Create Background Worker**.

Бот и API могут работать в одном проекте: один Web Service (API), один Worker (бот), одна БД.

### Кратко

| Сервис      | Тип             | Root    | Start / Publish                    |
|------------|------------------|---------|------------------------------------|
| PostgreSQL | PostgreSQL       | —       | создаётся автоматически           |
| API        | Web Service      | `backend` | `uvicorn api:app --host 0.0.0.0 --port $PORT` |
| Frontend   | Static Site      | `frontend` | Publish: `dist`                    |
| Бот        | Background Worker| `backend` | `python main.py`                   |

Файлы `render.yaml` в репозитории не нужны — всё настраивается в дашборде Render.
