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
- **Create Database**. После создания скопируйте **Internal Database URL** (или External, если фронт/бот будут снаружи).

### 2. Backend (REST API)

- **New** → **Web Service**.
- Подключите репозиторий с проектом.
- Настройки:
  - **Name:** например `dating-api`.
  - **Root Directory:** `backend`.
  - **Runtime:** Python 3.
  - **Build Command:** `pip install -r requirements.txt`
  - **Start Command:** `uvicorn api:app --host 0.0.0.0 --port $PORT`
- **Environment:**
  - `DATABASE_URL` — вставьте Internal Database URL из шага 1 (или добавьте через **Connect** к вашей БД).
  - `BOT_TOKEN` — токен бота от BotFather.
  - `ADMINS` — ID админов через запятую, например `123456789`.
- **Create Web Service**. Дождитесь деплоя и скопируйте URL сервиса, например `https://dating-api.onrender.com`.

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

### 4. CORS для Mini App

В коде API уже разрешён `https://web.telegram.org`. Если Mini App открывается с другого домена (например `https://dating-app.onrender.com`), добавьте его в `backend/api.py` в `allow_origins` у CORSMiddleware.

### 5. Бот (по желанию)

- **New** → **Background Worker**.
- Тот же репозиторий.
- **Root Directory:** `backend`.
- **Build Command:** `pip install -r requirements.txt`
  - **Start Command:** `python main.py`
- **Environment:** те же `DATABASE_URL`, `BOT_TOKEN`, `ADMINS`, что и у API.
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
