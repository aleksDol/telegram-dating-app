# Backend — REST API + Telegram-бот

Python 3.8+. Одна БД (`dating.db`), общая для API и бота.

## Установка

```bash
cd backend
cp .env.example .env
# В .env: BOT_TOKEN, ADMINS; для localhost без Telegram — ALLOW_DEV_USER_ID=1

pip install -r requirements.txt
```

## Запуск

**Всё одной командой (API + бот):**
```bash
python run_all.py
```
API будет на `http://0.0.0.0:8000`, бот — в режиме polling. Остановка: Ctrl+C.

Опционально в `.env` можно задать `API_HOST` и `API_PORT`.

**По отдельности:**

REST API (для Mini App):
```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

Telegram-бот:
```bash
python main.py
```

## Структура

- `api.py` — FastAPI: `/api/user`, `/api/register`, `/api/events`, `/api/achievements`, `/api/referral` и др.
- `bot.py`, `main.py` — Telegram-бот (pyTelegramBotAPI)
- `config.py`, `database.py`, `models.py` — конфиг, SQLite, модели
- `handlers/` — обработчики бота
- `keyboards/` — клавиатуры бота
- `services/` — достижения, рекомендации, уведомления, рассылки, жалобы
- `utils/` — хелперы (referral code, escape markdown и т.д.)
