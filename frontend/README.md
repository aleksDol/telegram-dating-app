# MiniApp — фронтенд для бота знакомств

React + TypeScript + Vite. Работает как Telegram Mini App.

## Функционал

- **Регистрация** — имя, возраст, пол, город, статус, цель, фото (URL)
- **Профиль** — просмотр и данные пользователя
- **События** — поиск по фильтрам (новые, ближайшие, сегодня, завтра, случайные, по интересам)
- **Карточка события** — лайк / пропустить
- **Создание события** — название, описание, дата, для кого, город, категория
- **Мои события** — список своих событий
- **Достижения** — список достижений и очков
- **Реферальная программа** — код и ссылка
- **О боте** — описание и инструкции

## Запуск

```bash
cd frontend
npm install
npm run dev
```

Сборка для продакшена:

```bash
npm run build
```

Файлы появятся в `dist/`. Разместите их на HTTPS-хостинге и укажите URL в настройках бота (BotFather → Mini App).

## Подключение к API

1. Скопируйте `.env.example` в `.env`.
2. Укажите `VITE_API_URL` — базовый URL REST API (для localhost: `http://localhost:8000`, бэкенд в папке `backend/`).
3. Бэкенд принимает заголовок `X-Telegram-Init-Data` (Mini App в Telegram) или `X-Dev-User-Id` (localhost без Telegram).

Эндпоинты, которые ожидает фронтенд:

- `GET /api/user` — текущий пользователь (по initData)
- `POST /api/register` — регистрация
- `PUT /api/profile` — обновление профиля
- `GET /api/events?filter=&limit=` — список событий
- `GET /api/events/:id` — одно событие
- `POST /api/events` — создание события
- `PUT /api/events/:id` — обновление
- `DELETE /api/events/:id` — удаление
- `GET /api/events/mine` — мои события
- `POST /api/events/:id/like` — лайк
- `POST /api/events/:id/skip` — пропустить
- `GET /api/achievements` — достижения и очки
- `GET /api/referral` — реферальный код и счётчик

Без `VITE_API_URL` приложение работает в демо-режиме (регистрация в памяти, списки событий пустые).

## Структура

```
frontend/
├── src/
│   ├── api/         # API-клиент
│   ├── context/     # AppContext (user state)
│   ├── hooks/       # useTelegram
│   ├── pages/       # Страницы
│   ├── constants.ts # Города, категории, достижения
│   ├── types.ts     # Типы
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── index.html
├── package.json
├── vite.config.ts
└── tsconfig.json
```

## Запуск Mini App из бота

В боте добавьте кнопку/команду, открывающую Mini App:

```python
# Пример: кнопка с url вашего Mini App
keyboard = telebot.types.InlineKeyboardMarkup()
keyboard.add(telebot.types.InlineKeyboardButton(
    "Открыть приложение",
    web_app=telebot.types.WebAppInfo(url="https://your-miniapp-url.com")
))
```

Или команда `/app`, которая отправляет эту кнопку.
