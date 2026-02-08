# api.py — REST API для Mini App (FastAPI)
# Запуск: uvicorn api:app --host 0.0.0.0 --port 8000
# Для localhost: фронт на :5173, API на :8000. В frontend/.env: VITE_API_URL=http://localhost:8000

import base64
import hmac
import hashlib
import json
import os
import re
from datetime import datetime
from io import BytesIO
from urllib.parse import parse_qsl

import requests
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from config import config
from database import execute_query
from utils.helpers import generate_referral_code
from services.achievements import AchievementService
from services.notifications import NotificationService
from services.recommendations import RecommendationService


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


def _upload_photo_to_telegram(chat_id: int, data_url: str) -> str | None:
    """Загружает фото из data URL в Telegram и возвращает file_id (короткая строка для БД)."""
    token = (config.BOT_TOKEN or "").strip()
    if not token or not data_url.strip().lower().startswith("data:"):
        return None
    try:
        match = re.match(r"data:([^;]+);base64,(.+)", data_url.strip(), re.DOTALL | re.IGNORECASE)
        if not match:
            return None
        content_type = match.group(1).strip().lower()
        b64 = match.group(2)
        raw = base64.b64decode(b64)
        ext = "jpg" if "jpeg" in content_type or "jpg" in content_type else "png"
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        with requests.post(
            url,
            data={"chat_id": chat_id},
            files={"photo": (f"photo.{ext}", BytesIO(raw), content_type)},
            timeout=30,
        ) as r:
            r.raise_for_status()
            data = r.json()
            if not data.get("ok"):
                return None
            photos = data.get("result", {}).get("photo", [])
            if not photos:
                return None
            return photos[-1].get("file_id")
    except Exception:
        return None


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

class RegisterBody(BaseModel):
    name: str
    age: int
    gender: str
    city: str
    relationship_status: str
    photo: str  # обязательно: data URL (base64) или URL фото
    purpose: str | None = None
    referred_by: int | None = None


class UpdateProfileBody(BaseModel):
    name: str | None = None
    age: int | None = None
    gender: str | None = None
    city: str | None = None
    relationship_status: str | None = None
    photo: str | None = None
    photos: list[str] | None = None
    purpose: str | None = None


class CreateEventBody(BaseModel):
    title: str
    description: str
    event_date: str
    target_gender: str
    city: str
    category: str | None = None


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


def _row_to_event(row: dict) -> dict:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
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
        "photo": _photo_for_response(row["user_id"], row.get("photo")),
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
        "SELECT user_id, name, age, gender, city, relationship_status, photo, purpose FROM users WHERE user_id = ? AND (is_banned = FALSE OR is_banned IS NULL)",
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
        file_id = _upload_photo_to_telegram(user_id, photo_value)
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
    if body.referred_by:
        AchievementService.update_user_points(user_id, 50, "за регистрацию по приглашению")
        AchievementService.update_user_points(body.referred_by, 100, "за приглашение пользователя")
        execute_query(
            "UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?",
            (body.referred_by,), commit=True
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
                file_id = _upload_photo_to_telegram(user_id, p)
                new_file_ids.append(file_id or p)
            elif f"/api/photo/user/{user_id}" in p:
                # URL с индексом: /api/photo/user/123/0 или без индекса: /api/photo/user/123
                parts = p.rstrip("/").split("/")
                # Если в пути 6 частей (..., user, id, index) — последняя это индекс; иначе 0
                idx = 0
                if len(parts) >= 6 and parts[-1].isdigit():
                    try:
                        idx = int(parts[-1])
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
                file_id = _upload_photo_to_telegram(user_id, photo_value)
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
        """SELECT e.*, u.name, u.age, u.gender, u.photo, u.purpose, u.relationship_status
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
    event_id = execute_query(
        """INSERT INTO events (user_id, title, description, event_date, target_gender, city, category, created)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id""",
        (
            user_id, body.title.strip(), body.description.strip(), event_date,
            body.target_gender, city, body.category,
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
        """SELECT e.*, u.name, u.age, u.gender, u.photo, u.purpose, u.relationship_status
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
    execute_query(
        """UPDATE events SET title = ?, description = ?, event_date = ?, target_gender = ?, city = ?, category = ?
           WHERE id = ?""",
        (body.title.strip(), body.description.strip(), event_date, body.target_gender, body.city, body.category, event_id),
        commit=True,
    )
    row = execute_query(
        """SELECT e.*, u.name, u.age, u.gender, u.photo, u.purpose, u.relationship_status
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
        u = execute_query("SELECT name, age, gender, photo, purpose, relationship_status FROM users WHERE user_id = ?", (r["user_id"],), fetchone=True)
        if u:
            r = dict(r, **u)
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
            """SELECT user_id, name, age, gender, city, relationship_status, photo, purpose, username
               FROM users WHERE user_id = ? AND is_banned = FALSE""",
            (r["from_user"],), fetchone=True
        )
        event_row = None
        if r.get("event_id"):
            event_row = execute_query(
                """SELECT e.id, e.user_id, e.title, e.description, e.event_date, e.target_gender, e.city, e.category, e.created,
                          u.name, u.age, u.gender, u.photo, u.purpose, u.relationship_status
                   FROM events e JOIN users u ON e.user_id = u.user_id WHERE e.id = ?""",
                (r["event_id"],), fetchone=True
            )
        liker_dict = None
        if liker:
            liker_dict = _row_to_public_user(liker)
            liker_dict["username"] = liker.get("username")
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
            """SELECT user_id, name, age, gender, city, relationship_status, photo, purpose, username
               FROM users WHERE user_id = ? AND is_banned = FALSE""",
            (other_id,), fetchone=True
        )
        event_dict = None
        if r.get("event_id"):
            event_row = execute_query(
                """SELECT e.id, e.user_id, e.title, e.description, e.event_date, e.target_gender, e.city, e.category, e.created,
                          u.name, u.age, u.gender, u.photo, u.purpose, u.relationship_status
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
