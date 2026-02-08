# api.py — REST API для Mini App (FastAPI)
# Запуск: uvicorn api:app --host 0.0.0.0 --port 8000
# Для localhost: фронт на :5173, API на :8000. В frontend/.env: VITE_API_URL=http://localhost:8000

import base64
import hmac
import hashlib
import json
import os
import re
import threading
from datetime import datetime, timedelta
from io import BytesIO
from urllib.parse import parse_qsl

import jwt
import requests
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from config import config
from database import execute_query
from utils.helpers import generate_referral_code
from services.achievements import AchievementService
from services.notifications import NotificationService
from services.recommendations import RecommendationService
from services.admin import AdminService
from services.reports import ReportService
from services.broadcast import BroadcastService


app = FastAPI(title="Dating Mini App API")

# CORS: localhost, Telegram Mini App, и доп. origins из env (например Static Site на Render)
_cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://web.telegram.org",
]
_extra = os.getenv("ADDITIONAL_CORS_ORIGINS", "").strip()
if _extra:
    _cors_origins.extend(o.strip() for o in _extra.split(",") if o.strip())
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    """Запрещаем кеширование ответов API — данные должны быть актуальными."""
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def validate_init_data(init_data: str) -> dict | None:
    """Проверка initData от Telegram Web App. Возвращает распарсенные данные или None."""
    token = (config.BOT_TOKEN or "").strip()
    if not init_data or not token:
        return None
    try:
        pairs = parse_qsl(init_data, keep_blank_values=True)
        data = dict(pairs)
        received_hash = data.pop("hash", None)
        if not received_hash:
            return None
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
        # По документации Telegram: secret_key = HMAC_SHA256(key="WebAppData", message=bot_token)
        secret_key = hmac.new(
            b"WebAppData",
            token.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        computed_hash = hmac.new(
            secret_key,
            data_check_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if computed_hash != received_hash:
            return None
        return data
    except Exception:
        return None


def get_telegram_user_from_init_data(
    x_telegram_init_data: str | None = Header(None, alias="X-Telegram-Init-Data"),
    x_dev_user_id: str | None = Header(None, alias="X-Dev-User-Id"),
) -> dict:
    """Парсит initData и возвращает dict с id и username (для Mini App). При X-Dev-User-Id возвращает только id."""
    if x_dev_user_id and os.getenv("ALLOW_DEV_USER_ID", "1").strip().lower() in ("1", "true", "yes"):
        try:
            return {"id": int(x_dev_user_id), "username": ""}
        except ValueError:
            pass
    raw = (x_telegram_init_data or "").strip()
    parsed = validate_init_data(raw)
    if not parsed:
        if raw:
            import logging
            logging.getLogger("api").warning("Telegram init_data received but validation failed (check BOT_TOKEN matches the bot that opened the Mini App)")
        raise HTTPException(status_code=401, detail="Invalid or missing Telegram init data")
    user_json = parsed.get("user")
    if not user_json:
        raise HTTPException(status_code=401, detail="No user in init data")
    try:
        user = json.loads(user_json)
        return {"id": int(user["id"]), "username": (user.get("username") or "").strip()}
    except (json.JSONDecodeError, KeyError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid user in init data")


def get_user_id(telegram_user: dict = Depends(get_telegram_user_from_init_data)) -> int:
    """Определение user_id: из initData (Mini App) или из X-Dev-User-Id (localhost)."""
    user_id = telegram_user["id"]
    username = telegram_user.get("username") or ""
    # Обновляем username при каждом запросе из Mini App (чтобы контакт в уведомлениях был актуальным)
    execute_query(
        "UPDATE users SET username = ? WHERE user_id = ?",
        (username, user_id), commit=True
    )
    return user_id


def _upload_photo_to_telegram(chat_id: int, data_url: str) -> tuple[str | None, str | None]:
    """Загружает фото из data URL в Telegram и возвращает (file_id, error_message). Сообщение в чат удаляем сразу."""
    token = (config.BOT_TOKEN or "").strip()
    if not token or not data_url.strip().lower().startswith("data:"):
        return None, "Нет токена бота или неверный формат изображения"
    try:
        match = re.match(r"data:([^;]+);base64,(.+)", data_url.strip(), re.DOTALL | re.IGNORECASE)
        if not match:
            return None, "Неверный data URL изображения"
        content_type = match.group(1).strip().lower()
        b64 = match.group(2)
        raw = base64.b64decode(b64)
        if len(raw) > 10 * 1024 * 1024:  # 10 MB лимит Telegram для фото
            return None, "Файл слишком большой (макс. 10 МБ)"
        # Проверка magic bytes — только реальные изображения (защита от подмены типа файла)
        if not raw or len(raw) < 12:
            return None, "Неверный формат изображения"
        if raw[:2] == b"\xff\xd8":
            pass  # JPEG
        elif raw[:8] == b"\x89PNG\r\n\x1a\n":
            pass  # PNG
        elif raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
            pass  # WebP
        else:
            return None, "Допустимые форматы: JPEG, PNG, WebP"
        ext = "jpg" if "jpeg" in content_type or "jpg" in content_type else "png"
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        with requests.post(
            url,
            data={"chat_id": chat_id},
            files={"photo": (f"photo.{ext}", BytesIO(raw), content_type)},
            timeout=30,
        ) as r:
            data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            if not data.get("ok"):
                desc = data.get("description", r.text or "Неизвестная ошибка Telegram")
                if "can't initiate" in desc.lower() or "blocked" in desc.lower() or "forbidden" in desc.lower():
                    desc = "Бот не может написать этому пользователю. Напишите боту /start от имени одного из админов (ADMINS в .env), затем повторите рассылку с фото."
                return None, desc
            result = data.get("result", {})
            photos = result.get("photo", [])
            if not photos:
                return None, "Telegram не вернул file_id"
            file_id = photos[-1].get("file_id")
            message_id = result.get("message_id")
            if message_id is not None:
                delete_url = f"https://api.telegram.org/bot{token}/deleteMessage"
                requests.post(
                    delete_url,
                    json={"chat_id": chat_id, "message_id": message_id},
                    timeout=10,
                )
            return file_id, None
    except requests.RequestException as e:
        return None, str(e) or "Ошибка сети"
    except Exception as e:
        return None, str(e) or "Ошибка загрузки фото"


def _photo_for_response(user_id: int, photo: str | None) -> str | None:
    """Для ответа API: если photo — file_id, возвращаем URL нашего endpoint; иначе как есть."""
    if not photo:
        return None
    if photo.startswith("data:") or photo.startswith("http://") or photo.startswith("https://"):
        return photo
    return f"/api/photo/user/{user_id}"


def _user_photos_list(row: dict) -> list:
    """Список file_id фото пользователя (из photos JSON или из одного photo)."""
    raw = row.get("photos")
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                result = [str(p) for p in parsed if p]
                if result:
                    return result
        except (json.JSONDecodeError, TypeError):
            pass
    single = row.get("photo")
    return [single] if single and str(single).strip() else []


# --- Pydantic models ---

# Лимиты длины полей — защита от DoS и переполнения
MAX_LEN_NAME = 100
MAX_LEN_CITY = 100
MAX_LEN_PURPOSE = 200
MAX_LEN_TITLE = 200
MAX_LEN_DESCRIPTION = 2000
AGE_MIN, AGE_MAX = 18, 120


class RegisterBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=MAX_LEN_NAME)
    age: int = Field(..., ge=AGE_MIN, le=AGE_MAX)
    gender: str = Field(..., max_length=50)
    city: str = Field(..., min_length=1, max_length=MAX_LEN_CITY)
    relationship_status: str = Field(..., max_length=100)
    photo: str  # обязательно: data URL (base64) или URL фото
    purpose: str | None = Field(None, max_length=MAX_LEN_PURPOSE)
    referred_by: int | None = None


class UpdateProfileBody(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=MAX_LEN_NAME)
    age: int | None = Field(None, ge=AGE_MIN, le=AGE_MAX)
    gender: str | None = Field(None, max_length=50)
    city: str | None = Field(None, max_length=MAX_LEN_CITY)
    relationship_status: str | None = Field(None, max_length=100)
    photo: str | None = None
    photos: list[str] | None = None
    purpose: str | None = Field(None, max_length=MAX_LEN_PURPOSE)


class CreateEventBody(BaseModel):
    title: str = Field(..., min_length=1, max_length=MAX_LEN_TITLE)
    description: str = Field(..., min_length=1, max_length=MAX_LEN_DESCRIPTION)
    event_date: str = Field(..., max_length=50)
    target_gender: str = Field(..., max_length=50)
    city: str = Field(..., max_length=MAX_LEN_CITY)
    category: str | None = Field(None, max_length=100)
    photo: str | None = None


def _row_to_user(row: dict) -> dict:
    photos_list = _user_photos_list(row)
    first_photo = photos_list[0] if photos_list else row.get("photo")
    user_id = row["user_id"]
    photo_urls = [f"/api/photo/user/{user_id}/{i}" for i in range(len(photos_list))]
    return {
        "user_id": row["user_id"],
        "username": row.get("username"),
        "name": row["name"],
        "age": row["age"],
        "gender": row["gender"],
        "city": row.get("city"),
        "relationship_status": row.get("relationship_status"),
        "photo": _photo_for_response(user_id, first_photo),
        "photos": photo_urls,
        "purpose": row.get("purpose") or "куда-то сходить",
        "points": row.get("points", 0),
        "reg_date": row.get("reg_date"),
        "last_active": row.get("last_active"),
        "favorite_categories": [],
        "referral_code": row.get("referral_code"),
        "referred_by": row.get("referred_by"),
        "referrals_count": row.get("referrals_count", 0),
        "is_banned": bool(row.get("is_banned", 0)),
        "ban_reason": row.get("ban_reason"),
        "banned_date": row.get("banned_date"),
    }


def _row_to_public_user(row: dict) -> dict:
    """Публичный профиль пользователя (для просмотра автора события)."""
    photos_list = _user_photos_list(row)
    uid = row["user_id"]
    first = photos_list[0] if photos_list else row.get("photo")
    photo_urls = [f"/api/photo/user/{uid}/{i}" for i in range(len(photos_list))]
    return {
        "user_id": uid,
        "name": row["name"],
        "age": row["age"],
        "gender": row["gender"],
        "city": row.get("city"),
        "relationship_status": row.get("relationship_status"),
        "photo": _photo_for_response(uid, first),
        "photos": photo_urls,
        "purpose": row.get("purpose") or "куда-то сходить",
    }


def _event_photo_url(event_id: int, event_photo: str | None) -> str | None:
    """URL фото события (картинка встречи)."""
    if not event_photo or not event_photo.strip():
        return None
    if event_photo.startswith("data:") or event_photo.startswith("http"):
        return event_photo
    return f"/api/photo/event/{event_id}"


def _row_to_event(row: dict) -> dict:
    event_id = row["id"]
    user_id = row["user_id"]
    event_photo = row.get("event_photo")
    user_photo = row.get("user_photo")
    if user_photo is None:
        user_photo = row.get("photo")
    return {
        "id": event_id,
        "user_id": user_id,
        "title": row["title"],
        "description": row["description"],
        "event_date": row["event_date"],
        "target_gender": row.get("target_gender", "Все"),
        "city": row["city"],
        "category": row.get("category"),
        "created": row.get("created"),
        "is_hidden": bool(row.get("is_hidden", 0)),
        "name": row.get("name"),
        "age": row.get("age"),
        "gender": row.get("gender"),
        "photo": _event_photo_url(event_id, event_photo),
        "organizer_photo": _photo_for_response(user_id, user_photo),
        "purpose": row.get("purpose"),
        "relationship_status": row.get("relationship_status"),
        "likes_count": row.get("likes_count"),
    }


@app.get("/api/user")
def api_get_user(user_id: int = Depends(get_user_id)):
    row = execute_query(
        "SELECT * FROM users WHERE user_id = ?", (user_id,), fetchone=True
    )
    if not row:
        return {"user": None}
    if row.get("is_banned", 0):
        raise HTTPException(status_code=403, detail="Account banned")
    return {"user": _row_to_user(row)}


@app.get("/api/users/{profile_user_id:int}")
def api_get_user_profile(
    profile_user_id: int,
    user_id: int = Depends(get_user_id),
):
    """Публичный профиль пользователя по id (для перехода из карточки события)."""
    row = execute_query(
        "SELECT user_id, name, age, gender, city, relationship_status, photo, photos, purpose FROM users WHERE user_id = ? AND (is_banned = FALSE OR is_banned IS NULL)",
        (profile_user_id,),
        fetchone=True,
    )
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": _row_to_public_user(row)}


def _stream_photo_by_file_id(file_id: str):
    """Скачивает фото по file_id из Telegram и возвращает StreamingResponse."""
    token = (config.BOT_TOKEN or "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Bot not configured")
    r = requests.get(
        f"https://api.telegram.org/bot{token}/getFile",
        params={"file_id": file_id},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise HTTPException(status_code=404, detail="File not found")
    file_path = data.get("result", {}).get("file_path")
    if not file_path:
        raise HTTPException(status_code=404, detail="File path not found")
    file_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
    resp = requests.get(file_url, timeout=15, stream=True)
    resp.raise_for_status()
    return StreamingResponse(
        resp.iter_content(chunk_size=8192),
        media_type=resp.headers.get("content-type", "image/jpeg"),
    )


@app.get("/api/photo/event/{event_id:int}")
def api_get_event_photo(event_id: int):
    """Отдаёт фото события (картинка встречи) по file_id."""
    row = execute_query(
        "SELECT photo FROM events WHERE id = ?", (event_id,), fetchone=True
    )
    if not row or not (row.get("photo") or "").strip():
        raise HTTPException(status_code=404, detail="Event photo not found")
    photo = row["photo"].strip()
    if photo.startswith("data:") or photo.startswith("http"):
        raise HTTPException(status_code=400, detail="Legacy event photo format")
    try:
        return _stream_photo_by_file_id(photo)
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Failed to fetch photo")


@app.get("/api/photo/user/{profile_user_id:int}")
@app.get("/api/photo/user/{profile_user_id:int}/{photo_index:int}")
def api_get_user_photo(profile_user_id: int, photo_index: int | None = None):
    """Отдаёт фото пользователя: без индекса — первое; с индексом — фото по слоту (0, 1, 2)."""
    row = execute_query(
        "SELECT photo, photos FROM users WHERE user_id = ?", (profile_user_id,), fetchone=True
    )
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    photos_list = _user_photos_list(row)
    idx = 0 if photo_index is None else photo_index
    if idx < 0 or idx >= len(photos_list):
        raise HTTPException(status_code=404, detail="Photo not found")
    photo = photos_list[idx].strip()
    if photo.startswith("data:") or photo.startswith("http"):
        raise HTTPException(status_code=400, detail="Legacy photo format, use file_id")
    try:
        return _stream_photo_by_file_id(photo)
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Failed to fetch photo")


@app.post("/api/register")
def api_register(
    body: RegisterBody,
    user_id: int = Depends(get_user_id),
    telegram_user: dict = Depends(get_telegram_user_from_init_data),
):
    existing = execute_query(
        "SELECT user_id, is_banned FROM users WHERE user_id = ?", (user_id,), fetchone=True
    )
    if existing:
        if existing.get("is_banned"):
            raise HTTPException(status_code=403, detail="Account banned")
        row = execute_query("SELECT * FROM users WHERE user_id = ?", (user_id,), fetchone=True)
        return {"user": _row_to_user(row)}
    if not (body.photo and body.photo.strip()):
        raise HTTPException(status_code=400, detail="Фото обязательно для регистрации")
    referral_code = generate_referral_code()
    purpose = (body.purpose or "").strip() or "куда-то сходить"
    photo_value = body.photo.strip()
    if photo_value.lower().startswith("data:"):
        file_id, _ = _upload_photo_to_telegram(user_id, photo_value)
        photo_value = file_id or photo_value
    username = (telegram_user.get("username") or "").strip()
    execute_query(
        """INSERT INTO users (user_id, username, name, age, gender, city, relationship_status, photo, purpose, reg_date, last_active, referral_code, referred_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id, username, body.name.strip(), body.age, body.gender, body.city,
            body.relationship_status or "Не в отношениях", photo_value, purpose,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            datetime.now().strftime("%Y-%m-%d"),
            referral_code, body.referred_by,
        ),
        commit=True,
    )
    # Реферал: из body или из pending_referral (если пользователь зашёл по ссылке в боте)
    referred_by_id = body.referred_by
    if referred_by_id is None:
        pending = execute_query(
            "SELECT referral_code FROM pending_referral WHERE user_id = ?",
            (user_id,), fetchone=True
        )
        if pending and pending.get("referral_code"):
            referrer = execute_query(
                "SELECT user_id FROM users WHERE referral_code = ? AND is_banned = FALSE",
                (pending["referral_code"],), fetchone=True
            )
            if referrer and referrer["user_id"] != user_id:
                referred_by_id = referrer["user_id"]
                execute_query(
                    "UPDATE users SET referred_by = ? WHERE user_id = ?",
                    (referred_by_id, user_id), commit=True
                )
        execute_query(
            "DELETE FROM pending_referral WHERE user_id = ?",
            (user_id,), commit=True
        )
    if referred_by_id:
        AchievementService.update_user_points(user_id, 50, "за регистрацию по приглашению")
        AchievementService.update_user_points(referred_by_id, 100, "за приглашение пользователя")
        execute_query(
            "UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?",
            (referred_by_id,), commit=True
        )
        referrer_stats = execute_query(
            "SELECT name, referrals_count FROM users WHERE user_id = ?",
            (referred_by_id,), fetchone=True
        )
        NotificationService.send_referral_registration_notification(
            referred_by_id,
            body.name.strip() or "новый пользователь",
            referrer_stats["referrals_count"] if referrer_stats else 1,
        )
    row = execute_query("SELECT * FROM users WHERE user_id = ?", (user_id,), fetchone=True)
    return {"user": _row_to_user(row)}


@app.put("/api/profile")
def api_update_profile(body: UpdateProfileBody, user_id: int = Depends(get_user_id)):
    row = execute_query("SELECT * FROM users WHERE user_id = ?", (user_id,), fetchone=True)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    updates = []
    params = []
    if body.name is not None:
        updates.append("name = ?"); params.append(body.name.strip())
    if body.age is not None:
        updates.append("age = ?"); params.append(body.age)
    if body.gender is not None:
        updates.append("gender = ?"); params.append(body.gender)
    if body.city is not None:
        updates.append("city = ?"); params.append(body.city)
    if body.relationship_status is not None:
        updates.append("relationship_status = ?"); params.append(body.relationship_status)
    if body.photos is not None:
        current_list = _user_photos_list(row)
        new_file_ids = []
        for p in (body.photos or [])[:3]:
            p = (p or "").strip()
            if not p:
                continue
            if p.lower().startswith("data:"):
                file_id, _ = _upload_photo_to_telegram(user_id, p)
                new_file_ids.append(file_id or p)
            elif f"/api/photo/user/{user_id}" in p:
                # URL с индексом: /api/photo/user/123/0 или без индекса: /api/photo/user/123
                # Берём последний сегмент пути (без query), это индекс фото
                parts = p.split("?")[0].rstrip("/").split("/")
                idx = 0
                if len(parts) >= 6:
                    last = parts[-1]
                    if last.isdigit():
                        try:
                            idx = int(last)
                        except ValueError:
                            pass
                if 0 <= idx < len(current_list):
                    new_file_ids.append(current_list[idx])
            else:
                new_file_ids.append(p)
        photos_json = json.dumps(new_file_ids)
        first_photo = new_file_ids[0] if new_file_ids else None
        updates.append("photos = ?"); params.append(photos_json)
        updates.append("photo = ?"); params.append(first_photo or row.get("photo"))
    elif body.photo is not None:
        photo_value = body.photo.strip()
        if photo_value.startswith("/api/photo/"):
            photo_value = None
        if photo_value is not None:
            if photo_value.lower().startswith("data:"):
                file_id, _ = _upload_photo_to_telegram(user_id, photo_value)
                if file_id:
                    photo_value = file_id
            updates.append("photo = ?"); params.append(photo_value)
    if body.purpose is not None:
        updates.append("purpose = ?"); params.append(body.purpose.strip() or "куда-то сходить")
    if not updates:
        return {"user": _row_to_user(row)}
    params.append(user_id)
    execute_query(
        f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?",
        tuple(params), commit=True
    )
    row = execute_query("SELECT * FROM users WHERE user_id = ?", (user_id,), fetchone=True)
    return {"user": _row_to_user(row)}


@app.get("/api/events")
def api_get_events(
    filter: str = "new",
    limit: int = 10,
    user_id: int = Depends(get_user_id),
):
    user = execute_query("SELECT * FROM users WHERE user_id = ?", (user_id,), fetchone=True)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if filter == "interest":
        events = RecommendationService.get_recommendations(user_id, limit=limit)
    else:
        events = RecommendationService.get_events_by_filter(user_id, filter, limit=limit)
    return {"events": [_row_to_event(e) for e in events]}


@app.get("/api/events/{event_id:int}")
def api_get_event(event_id: int, user_id: int = Depends(get_user_id)):
    row = execute_query(
        """SELECT e.id, e.user_id, e.title, e.description, e.event_date, e.target_gender, e.city, e.category, e.photo AS event_photo, e.created, e.is_hidden,
                  u.name, u.age, u.gender, u.photo AS user_photo, u.purpose, u.relationship_status
           FROM events e JOIN users u ON e.user_id = u.user_id
           WHERE e.id = ? AND e.is_hidden = FALSE AND u.is_banned = FALSE""",
        (event_id,), fetchone=True
    )
    if not row:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"event": _row_to_event(row)}


@app.post("/api/events")
def api_create_event(body: CreateEventBody, user_id: int = Depends(get_user_id)):
    user = execute_query("SELECT city FROM users WHERE user_id = ?", (user_id,), fetchone=True)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    city = body.city or (user.get("city") or "")
    event_date = body.event_date
    if "T" in event_date:
        event_date = event_date.replace("T", " ").rstrip("Z")[:19]
    event_photo_value = None
    if body.photo and body.photo.strip():
        if body.photo.strip().lower().startswith("data:"):
            event_photo_value, _ = _upload_photo_to_telegram(user_id, body.photo.strip())
            event_photo_value = event_photo_value or body.photo.strip()
        else:
            event_photo_value = body.photo.strip()
    event_id = execute_query(
        """INSERT INTO events (user_id, title, description, event_date, target_gender, city, category, photo, created)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id""",
        (
            user_id, body.title.strip(), body.description.strip(), event_date,
            body.target_gender, city, body.category, event_photo_value,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
        commit=True,
    )
    execute_query(
        "UPDATE users SET purpose = ? WHERE user_id = ?",
        (f"🎯 {body.title.strip()}", user_id), commit=True
    )
    AchievementService.update_user_points(user_id, 10, "за создание события")
    events_count = execute_query(
        "SELECT COUNT(*) as count FROM events WHERE user_id = ? AND is_hidden = FALSE",
        (user_id,), fetchone=True
    )["count"]
    if events_count == 1:
        AchievementService.unlock_achievement(user_id, "first_event")
    row = execute_query(
        """SELECT e.id, e.user_id, e.title, e.description, e.event_date, e.target_gender, e.city, e.category, e.photo AS event_photo, e.created, e.is_hidden,
                  u.name, u.age, u.gender, u.photo AS user_photo, u.purpose, u.relationship_status
           FROM events e JOIN users u ON e.user_id = u.user_id WHERE e.id = ?""",
        (event_id,), fetchone=True
    )
    return {"event": _row_to_event(row)}


@app.put("/api/events/{event_id:int}")
def api_update_event(event_id: int, body: CreateEventBody, user_id: int = Depends(get_user_id)):
    row = execute_query("SELECT user_id FROM events WHERE id = ?", (event_id,), fetchone=True)
    if not row or row["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Event not found")
    event_date = body.event_date
    if "T" in event_date:
        event_date = event_date.replace("T", " ").rstrip("Z")[:19]
    event_photo_value = None
    if body.photo is not None:
        if body.photo and body.photo.strip():
            if body.photo.strip().lower().startswith("data:"):
                event_photo_value, _ = _upload_photo_to_telegram(user_id, body.photo.strip())
                event_photo_value = event_photo_value or body.photo.strip()
            else:
                event_photo_value = body.photo.strip()
    if event_photo_value is not None:
        execute_query(
            "UPDATE events SET title = ?, description = ?, event_date = ?, target_gender = ?, city = ?, category = ?, photo = ? WHERE id = ?",
            (body.title.strip(), body.description.strip(), event_date, body.target_gender, body.city, body.category, event_photo_value, event_id),
            commit=True,
        )
    else:
        execute_query(
            """UPDATE events SET title = ?, description = ?, event_date = ?, target_gender = ?, city = ?, category = ?
               WHERE id = ?""",
            (body.title.strip(), body.description.strip(), event_date, body.target_gender, body.city, body.category, event_id),
            commit=True,
        )
    row = execute_query(
        """SELECT e.id, e.user_id, e.title, e.description, e.event_date, e.target_gender, e.city, e.category, e.photo AS event_photo, e.created, e.is_hidden,
                  u.name, u.age, u.gender, u.photo AS user_photo, u.purpose, u.relationship_status
           FROM events e JOIN users u ON e.user_id = u.user_id WHERE e.id = ?""",
        (event_id,), fetchone=True
    )
    return {"event": _row_to_event(row)}


@app.delete("/api/events/{event_id:int}")
def api_delete_event(event_id: int, user_id: int = Depends(get_user_id)):
    row = execute_query("SELECT user_id FROM events WHERE id = ?", (event_id,), fetchone=True)
    if not row or row["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Event not found")
    execute_query("DELETE FROM likes WHERE event_id = ?", (event_id,), commit=True)
    execute_query("DELETE FROM events WHERE id = ?", (event_id,), commit=True)
    return {"ok": True}


@app.get("/api/events/mine")
def api_my_events(user_id: int = Depends(get_user_id)):
    rows = execute_query(
        "SELECT * FROM events WHERE user_id = ? AND is_hidden = FALSE ORDER BY created DESC",
        (user_id,), fetchall=True
    )
    events = []
    for r in rows:
        r = dict(r)
        r["event_photo"] = r.get("photo")
        u = execute_query("SELECT name, age, gender, photo, purpose, relationship_status FROM users WHERE user_id = ?", (r["user_id"],), fetchone=True)
        if u:
            r["user_photo"] = u.get("photo")
            r["name"] = u.get("name")
            r["age"] = u.get("age")
            r["gender"] = u.get("gender")
            r["purpose"] = u.get("purpose")
            r["relationship_status"] = u.get("relationship_status")
        events.append(_row_to_event(r))
    return {"events": events}


@app.post("/api/events/{event_id:int}/like")
def api_like_event(event_id: int, user_id: int = Depends(get_user_id)):
    event = execute_query(
        "SELECT id, user_id, category FROM events WHERE id = ? AND is_hidden = FALSE",
        (event_id,), fetchone=True
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    creator_id = event["user_id"]
    if creator_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot like own event")
    existing = execute_query(
        "SELECT id FROM likes WHERE from_user = ? AND event_id = ?",
        (user_id, event_id), fetchone=True
    )
    if existing:
        return {"mutual": False}
    like_id = execute_query(
        """INSERT INTO likes (from_user, to_user, event_id, created) VALUES (?, ?, ?, ?) RETURNING id""",
        (user_id, creator_id, event_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        commit=True,
    )
    # Уведомление создателю события: короткое сообщение + кнопка «Открыть приложение»
    try:
        NotificationService.send_like_notification(
            creator_id, user_id, {"id": event_id}, like_id, bot=None
        )
    except Exception as e:
        import logging
        logging.getLogger("api").warning("Не удалось отправить уведомление о лайке в Telegram: %s", e)
    if event.get("category"):
        prefs = execute_query("SELECT liked_categories FROM user_preferences WHERE user_id = ?", (user_id,), fetchone=True)
        liked = []
        if prefs and prefs.get("liked_categories"):
            try:
                liked = json.loads(prefs["liked_categories"])
            except Exception:
                liked = []
        if event["category"] not in liked:
            liked.append(event["category"])
            if prefs:
                execute_query("UPDATE user_preferences SET liked_categories = ? WHERE user_id = ?", (json.dumps(liked), user_id), commit=True)
            else:
                execute_query("INSERT INTO user_preferences (user_id, liked_categories) VALUES (?, ?)", (user_id, json.dumps(liked)), commit=True)
    AchievementService.update_user_points(user_id, 5, "за лайк события")
    mutual_check = execute_query(
        "SELECT id FROM likes WHERE from_user = ? AND to_user = ? AND event_id = ?",
        (creator_id, user_id, event_id), fetchone=True
    )
    mutual = bool(mutual_check)
    if mutual:
        execute_query("UPDATE likes SET mutual = TRUE WHERE from_user = ? AND to_user = ? AND event_id = ?", (user_id, creator_id, event_id), commit=True)
        execute_query("UPDATE likes SET mutual = TRUE WHERE from_user = ? AND to_user = ? AND event_id = ?", (creator_id, user_id, event_id), commit=True)
        AchievementService.update_user_points(user_id, 20, "за взаимную симпатию")
        AchievementService.update_user_points(creator_id, 20, "за взаимную симпатию")
        AchievementService.check_achievements(user_id)
        AchievementService.check_achievements(creator_id)
        try:
            NotificationService.send_match_notification(user_id, creator_id, event_id, bot=None)
        except Exception:
            pass
    return {"mutual": mutual}


@app.post("/api/events/{event_id:int}/skip")
def api_skip_event(event_id: int, user_id: int = Depends(get_user_id)):
    return {"ok": True}


class RespondToLikeBody(BaseModel):
    action: str  # "mutual" | "ignore"


@app.get("/api/likes/pending")
def api_get_pending_likes(user_id: int = Depends(get_user_id)):
    """Лайки, на которые ещё не ответили (взаимностью или пропуском).
    Фронт исключает из «Новые лайки» тех, кто уже в матчинге."""
    rows = execute_query(
        """SELECT l.id AS like_id, l.from_user, l.event_id
           FROM likes l
           WHERE l.to_user = ? AND (l.response IS NULL OR l.response = '')
           ORDER BY l.created DESC""",
        (user_id,), fetchall=True
    )
    result = []
    for r in rows:
        liker = execute_query(
            """SELECT user_id, name, age, gender, city, relationship_status, photo, photos, purpose, username
               FROM users WHERE user_id = ? AND is_banned = FALSE""",
            (r["from_user"],), fetchone=True
        )
        event_row = None
        if r.get("event_id"):
            event_row = execute_query(
                """SELECT e.id, e.user_id, e.title, e.description, e.event_date, e.target_gender, e.city, e.category, e.photo AS event_photo, e.created, e.is_hidden,
                          u.name, u.age, u.gender, u.photo AS user_photo, u.purpose, u.relationship_status
                   FROM events e JOIN users u ON e.user_id = u.user_id WHERE e.id = ?""",
                (r["event_id"],), fetchone=True
            )
        liker_dict = None
        if liker:
            liker_dict = _row_to_public_user(liker)
            # username не отдаём в pending — контакт виден только при матчинге
        event_dict = _row_to_event(event_row) if event_row else None
        result.append({
            "like_id": r["like_id"],
            "liker": liker_dict,
            "event": event_dict,
        })
    return {"likes": result}


@app.get("/api/likes/matches")
def api_get_likes_matches(user_id: int = Depends(get_user_id)):
    """Взаимные симпатии (матчинг) — пользователи, с которыми взаимный лайк."""
    rows = execute_query(
        """SELECT l.from_user, l.to_user, l.event_id
           FROM likes l
           WHERE l.mutual = TRUE AND (l.from_user = ? OR l.to_user = ?)
           ORDER BY l.event_id DESC NULLS LAST""",
        (user_id, user_id), fetchall=True
    )
    seen = set()
    result = []
    for r in rows:
        other_id = r["to_user"] if r["from_user"] == user_id else r["from_user"]
        if other_id in seen:
            continue
        seen.add(other_id)
        other = execute_query(
            """SELECT user_id, name, age, gender, city, relationship_status, photo, photos, purpose, username
               FROM users WHERE user_id = ? AND is_banned = FALSE""",
            (other_id,), fetchone=True
        )
        event_dict = None
        if r.get("event_id"):
            event_row = execute_query(
                """SELECT e.id, e.user_id, e.title, e.description, e.event_date, e.target_gender, e.city, e.category, e.photo AS event_photo, e.created, e.is_hidden,
                          u.name, u.age, u.gender, u.photo AS user_photo, u.purpose, u.relationship_status
                   FROM events e JOIN users u ON e.user_id = u.user_id WHERE e.id = ?""",
                (r["event_id"],), fetchone=True
            )
            if event_row:
                event_dict = _row_to_event(event_row)
        user_dict = None
        if other:
            user_dict = _row_to_public_user(other)
            user_dict["username"] = other.get("username")
        result.append({
            "user_id": other_id,
            "user": user_dict,
            "event": event_dict,
        })
    return {"matches": result}


@app.post("/api/likes/{like_id:int}/respond")
def api_respond_to_like(
    like_id: int,
    body: RespondToLikeBody,
    user_id: int = Depends(get_user_id),
):
    """Ответ на лайк: mutual (взаимность) или ignore (пропустить)."""
    if body.action not in ("mutual", "ignore"):
        raise HTTPException(status_code=400, detail="action must be 'mutual' or 'ignore'")
    like_row = execute_query(
        "SELECT id, from_user, to_user, event_id FROM likes WHERE id = ?",
        (like_id,), fetchone=True
    )
    if not like_row:
        raise HTTPException(status_code=404, detail="Like not found")
    if like_row["to_user"] != user_id:
        raise HTTPException(status_code=403, detail="Not your like to respond")
    if body.action == "ignore":
        execute_query(
            "UPDATE likes SET response = 'ignored' WHERE id = ?",
            (like_id,), commit=True
        )
        return {"ok": True}
    # mutual
    creator_id = user_id
    liker_id = like_row["from_user"]
    event_id = like_row["event_id"]
    execute_query(
        "UPDATE likes SET mutual = TRUE, response = 'mutual' WHERE id = ?",
        (like_id,), commit=True
    )
    mutual_check = execute_query(
        "SELECT id FROM likes WHERE from_user = ? AND to_user = ? AND event_id = ? AND mutual = TRUE",
        (user_id, liker_id, event_id), fetchone=True
    )
    if not mutual_check:
        execute_query(
            """INSERT INTO likes (from_user, to_user, event_id, mutual, created)
               VALUES (?, ?, ?, TRUE, ?)""",
            (user_id, liker_id, event_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            commit=True
        )
    AchievementService.update_user_points(creator_id, 20, "за взаимную симпатию")
    AchievementService.update_user_points(liker_id, 20, "за взаимную симпатию")
    AchievementService.check_achievements(creator_id)
    AchievementService.check_achievements(liker_id)
    try:
        NotificationService.send_mutual_response_to_liker(liker_id, creator_id, event_id, bot=None)
    except Exception:
        pass
    return {"ok": True, "mutual": True}


@app.get("/api/achievements")
def api_achievements(user_id: int = Depends(get_user_id)):
    achievements = AchievementService.get_user_achievements(user_id)
    user = execute_query("SELECT points FROM users WHERE user_id = ?", (user_id,), fetchone=True)
    points = user["points"] if user else 0
    return {"achievements": achievements, "points": points}


@app.get("/api/referral")
def api_referral(user_id: int = Depends(get_user_id)):
    row = execute_query(
        "SELECT referral_code, referrals_count FROM users WHERE user_id = ?",
        (user_id,), fetchone=True
    )
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    code = row.get("referral_code")
    if not code:
        code = generate_referral_code()
        execute_query("UPDATE users SET referral_code = ? WHERE user_id = ?", (code, user_id), commit=True)
    return {"referral_code": code, "referrals_count": row.get("referrals_count", 0)}


@app.get("/health")
def health():
    return {"status": "ok"}


# --- Admin panel API (веб-админка: логин + пароль + токен из .env) ---

ADMIN_JWT_ALGORITHM = "HS256"
ADMIN_JWT_EXPIRY_HOURS = 24


class AdminLoginBody(BaseModel):
    login: str
    password: str
    token: str


def _admin_issue_token():
    payload = {"sub": "admin", "exp": datetime.utcnow() + timedelta(hours=ADMIN_JWT_EXPIRY_HOURS)}
    return jwt.encode(
        payload,
        (config.TOKEN_ADMIN or "secret").encode("utf-8"),
        algorithm=ADMIN_JWT_ALGORITHM,
    )


def _admin_verify_token(token: str) -> bool:
    if not token or not config.TOKEN_ADMIN:
        return False
    try:
        jwt.decode(
            token,
            config.TOKEN_ADMIN.encode("utf-8"),
            algorithms=[ADMIN_JWT_ALGORITHM],
        )
        return True
    except Exception:
        return False


def get_admin_authorization(
    authorization: str | None = Header(None),
) -> None:
    """Проверяет JWT админа из заголовка Authorization: Bearer <token>."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Admin authorization required")
    token = authorization[7:].strip()
    if not _admin_verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid or expired admin token")


@app.post("/admin/api/auth")
def admin_api_auth(body: AdminLoginBody):
    """Вход в админку: логин, пароль и токен из .env."""
    login = (body.login or "").strip()
    password = (body.password or "").strip()
    token = (body.token or "").strip()
    if not all([config.LOGIN_ADMIN, config.PASSWORD_ADMIN, config.TOKEN_ADMIN]):
        raise HTTPException(status_code=503, detail="Admin credentials not configured")
    if login != config.LOGIN_ADMIN or password != config.PASSWORD_ADMIN or token != config.TOKEN_ADMIN:
        raise HTTPException(status_code=401, detail="Неверный логин, пароль или токен")
    access_token = _admin_issue_token()
    return {"access_token": access_token, "token_type": "bearer"}


def _to_json_value(v):
    """Приводит значение к JSON-сериализуемому виду (Decimal, datetime и т.д.)."""
    if v is None:
        return None
    if isinstance(v, (int, str, bool)):
        return v
    if isinstance(v, float):
        return v
    try:
        from decimal import Decimal
        if isinstance(v, Decimal):
            return int(v) if v % 1 == 0 else float(v)
    except Exception:
        pass
    if hasattr(v, "isoformat"):  # datetime, date
        return str(v)
    if isinstance(v, list):
        return [_serialize_stats_value(x) for x in v]
    if hasattr(v, "keys") and not isinstance(v, dict):
        return {kk: _to_json_value(vv) for kk, vv in dict(v).items()}
    if isinstance(v, dict):
        return {kk: _to_json_value(vv) for kk, vv in v.items()}
    return str(v)


def _serialize_stats_value(v):
    """RealDictRow и списки строк в JSON-серизуемый вид."""
    if isinstance(v, list):
        return [_to_json_value(x) for x in v]
    if hasattr(v, "keys") and not isinstance(v, dict):
        return {kk: _to_json_value(vv) for kk, vv in dict(v).items()}
    return _to_json_value(v)


@app.get("/admin/api/stats")
def admin_api_stats(_: None = Depends(get_admin_authorization)):
    """Статистика для админ-панели."""
    try:
        stats = AdminService.get_admin_stats()
    except Exception as e:
        import logging
        logging.getLogger("api").exception("Admin stats failed")
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {k: _serialize_stats_value(v) for k, v in stats.items()}


def _admin_user_row_to_dict(row, base_url: str = ""):
    """Преобразует строку пользователя в dict для JSON; photo — URL если file_id."""
    if not row:
        return None
    d = dict(row)
    uid = d.get("user_id")
    photo = d.get("photo")
    if photo and not (str(photo).startswith("http") or str(photo).startswith("data:")):
        d["photo_url"] = f"{base_url}/api/photo/user/{uid}" if uid else None
    else:
        d["photo_url"] = photo
    return d


@app.get("/admin/api/users/recent")
def admin_api_users_recent(
    limit: int = 10,
    _: None = Depends(get_admin_authorization),
):
    """Последние зарегистрированные пользователи (ID, город, имя)."""
    if limit < 1 or limit > 100:
        limit = 10
    rows = execute_query(
        """SELECT user_id, name, city, reg_date
           FROM users
           WHERE is_banned = FALSE
           ORDER BY reg_date DESC NULLS LAST, user_id DESC
           LIMIT ?""",
        (limit,),
        fetchall=True,
    )
    return {"users": [{"user_id": r["user_id"], "name": r.get("name"), "city": r.get("city") or "", "reg_date": r.get("reg_date")} for r in rows]}


@app.get("/admin/api/funnel")
def admin_api_funnel(_: None = Depends(get_admin_authorization)):
    """Воронка: 4 группы пользователей, в каждой последние 10 (ID, имя, пол, город)."""
    limit = 10

    # 1. Нажали Start, но не зарегистрировались (нет в users)
    started_rows = execute_query(
        """SELECT b.user_id, b.first_name, b.started_at
           FROM bot_starts b
           WHERE b.user_id NOT IN (SELECT user_id FROM users)
           ORDER BY b.started_at DESC NULLS LAST
           LIMIT ?""",
        (limit,),
        fetchall=True,
    )
    started_not_registered = [
        {
            "user_id": r["user_id"],
            "name": (r.get("first_name") or "").strip() or "—",
            "gender": "—",
            "city": "—",
        }
        for r in started_rows
    ]

    # 2. Зарегистрировались, но не создали ни одного события
    reg_no_events = execute_query(
        """SELECT u.user_id, u.name, u.gender, u.city
           FROM users u
           WHERE u.is_banned = FALSE
             AND NOT EXISTS (SELECT 1 FROM events e WHERE e.user_id = u.user_id AND e.is_hidden = FALSE)
           ORDER BY u.reg_date DESC NULLS LAST, u.user_id DESC
           LIMIT ?""",
        (limit,),
        fetchall=True,
    )
    registered_no_events = [
        {
            "user_id": r["user_id"],
            "name": (r.get("name") or "").strip() or "—",
            "gender": (r.get("gender") or "").strip() or "—",
            "city": (r.get("city") or "").strip() or "—",
        }
        for r in reg_no_events
    ]

    # 3. Создали хотя бы одно событие
    created_events = execute_query(
        """SELECT u.user_id, u.name, u.gender, u.city
           FROM users u
           WHERE u.is_banned = FALSE
             AND EXISTS (SELECT 1 FROM events e WHERE e.user_id = u.user_id AND e.is_hidden = FALSE)
           ORDER BY (SELECT MAX(e.created) FROM events e WHERE e.user_id = u.user_id AND e.is_hidden = FALSE) DESC NULLS LAST, u.user_id DESC
           LIMIT ?""",
        (limit,),
        fetchall=True,
    )
    created_events_list = [
        {
            "user_id": r["user_id"],
            "name": (r.get("name") or "").strip() or "—",
            "gender": (r.get("gender") or "").strip() or "—",
            "city": (r.get("city") or "").strip() or "—",
        }
        for r in created_events
    ]

    # 4. Получили хотя бы один матчинг (взаимный лайк), порядок по последнему mutual
    mutual_user_ids = execute_query(
        """SELECT u.user_id
           FROM users u
           WHERE u.is_banned = FALSE
             AND (EXISTS (SELECT 1 FROM likes l WHERE l.mutual = TRUE AND l.from_user = u.user_id)
                  OR EXISTS (SELECT 1 FROM likes l WHERE l.mutual = TRUE AND l.to_user = u.user_id))
           ORDER BY (SELECT MAX(l2.created) FROM likes l2 WHERE (l2.from_user = u.user_id OR l2.to_user = u.user_id) AND l2.mutual = TRUE) DESC NULLS LAST
           LIMIT ?""",
        (limit,),
        fetchall=True,
    )
    has_matching_list = []
    if mutual_user_ids:
        ids = [r["user_id"] for r in mutual_user_ids]
        placeholders = ",".join("?" * len(ids))
        rows = execute_query(
            f"SELECT user_id, name, gender, city FROM users WHERE user_id IN ({placeholders})",
            tuple(ids),
            fetchall=True,
        )
        by_id = {r["user_id"]: r for r in rows}
        for uid in ids:
            r = by_id.get(uid)
            if r:
                has_matching_list.append({
                    "user_id": r["user_id"],
                    "name": (r.get("name") or "").strip() or "—",
                    "gender": (r.get("gender") or "").strip() or "—",
                    "city": (r.get("city") or "").strip() or "—",
                })

    return {
        "started_not_registered": started_not_registered,
        "registered_no_events": registered_no_events,
        "created_events": created_events_list,
        "has_matching": has_matching_list,
    }


@app.get("/admin/api/user/{identifier}")
def admin_api_user(
    identifier: str,
    _: None = Depends(get_admin_authorization),
):
    """Поиск пользователя по ID или username."""
    user = AdminService.get_user_full_info(identifier)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _admin_user_row_to_dict(user)


class AdminBanBody(BaseModel):
    reason: str | None = None


@app.post("/admin/api/user/{user_id:int}/ban")
def admin_api_ban_user(
    user_id: int,
    body: AdminBanBody,
    _: None = Depends(get_admin_authorization),
):
    """Заблокировать пользователя (reason в body). banned_by=0 для веб-админа."""
    reason = (body.reason or "").strip() or "Блокировка через веб-админку"
    if ReportService.ban_user(user_id, reason, 0):
        return {"ok": True}
    raise HTTPException(status_code=400, detail="Ban failed")


@app.post("/admin/api/user/{user_id:int}/unban")
def admin_api_unban_user(
    user_id: int,
    _: None = Depends(get_admin_authorization),
):
    """Разблокировать пользователя."""
    if ReportService.unban_user(user_id):
        return {"ok": True}
    raise HTTPException(status_code=400, detail="Unban failed")


@app.get("/admin/api/reports")
def admin_api_reports(
    status: str = "pending",
    _: None = Depends(get_admin_authorization),
):
    """Список жалоб по статусу (pending, resolved и т.д.)."""
    reports = ReportService.get_reports_by_status(status)
    return {"reports": [dict(r) for r in reports]}


@app.get("/admin/api/events")
def admin_api_user_events(
    user_id: int,
    _: None = Depends(get_admin_authorization),
):
    """События пользователя (для админки)."""
    rows = execute_query(
        """SELECT e.id, e.user_id, e.title, e.description, e.event_date, e.target_gender, e.city, e.category, e.photo, e.created, e.is_hidden
           FROM events e WHERE e.user_id = ? ORDER BY e.created DESC""",
        (user_id,),
        fetchall=True,
    )
    return {"events": [dict(r) for r in rows]}


# --- Рассылка (сегмент: все / мужчины / женщины) ---

class AdminBroadcastBody(BaseModel):
    text: str
    gender: str = "all"  # "all" | "Мужской" | "Женский"
    photo: str | None = None  # опционально: data URL (data:image/...;base64,...) для рассылки с фото


@app.post("/admin/api/broadcast/preview")
def admin_api_broadcast_preview(
    body: AdminBroadcastBody,
    _: None = Depends(get_admin_authorization),
):
    """Предпросмотр рассылки: количество получателей по сегменту."""
    filters = {"gender": (body.gender or "all").strip() or "all"}
    if filters["gender"] not in ("all", "Мужской", "Женский"):
        filters["gender"] = "all"
    user_ids = BroadcastService.get_users_by_filters(filters)
    count = len(user_ids)
    return {"count": count, "gender": filters["gender"]}


@app.post("/admin/api/broadcast/send")
def admin_api_broadcast_send(
    body: AdminBroadcastBody,
    _: None = Depends(get_admin_authorization),
):
    """Создать рассылку и запустить отправку (admin_id=0 — без уведомлений в Telegram). Поддерживает текст и опционально фото (data URL)."""
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Текст сообщения не может быть пустым")
    gender = (body.gender or "all").strip() or "all"
    if gender not in ("all", "Мужской", "Женский"):
        gender = "all"
    filters = {"gender": gender}
    user_ids = BroadcastService.get_users_by_filters(filters)
    total = len(user_ids)
    if total == 0:
        raise HTTPException(status_code=400, detail="Нет получателей по выбранному сегменту")

    photo_data = (body.photo or "").strip() or None
    content_type = "text"
    content = text
    caption = ""

    if photo_data and photo_data.lower().startswith("data:image"):
        # Сохраняем фото как base64 — отправка получателям без использования чата админа (избегаем "chat not found")
        content_type = "photo_base64"
        content = photo_data
        caption = text

    broadcast_id = execute_query(
        """INSERT INTO admin_broadcasts
           (admin_id, content_type, content, caption, filters, created, status)
           VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id""",
        (0, content_type, content, caption, json.dumps(filters), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "pending"),
        commit=True,
    )
    if not isinstance(broadcast_id, int):
        broadcast_id = broadcast_id[0] if isinstance(broadcast_id, (list, tuple)) else int(broadcast_id)

    if config.BOT_TOKEN:
        import telebot
        bot = telebot.TeleBot(config.BOT_TOKEN)
        thread = threading.Thread(
            target=BroadcastService.process_broadcast,
            args=(broadcast_id, 0, 0, bot),
        )
        thread.daemon = True
        thread.start()
    else:
        raise HTTPException(status_code=503, detail="Бот не настроен (BOT_TOKEN)")

    return {"broadcast_id": broadcast_id, "total_recipients": total}
