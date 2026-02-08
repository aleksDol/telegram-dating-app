# services/broadcast.py
import base64
import json
import re
import time
import threading
from datetime import datetime, timedelta
from io import BytesIO
from database import execute_query
from config import config
import telebot


def _decode_photo_base64(data_url):
    """Из data URL (data:image/...;base64,...) извлекает байты изображения."""
    if not data_url or not isinstance(data_url, str):
        return None
    data_url = data_url.strip()
    if not data_url.lower().startswith("data:image"):
        return None
    try:
        match = re.match(r"data:image/[^;]+;base64,(.+)", data_url, re.DOTALL | re.IGNORECASE)
        if not match:
            return None
        return base64.b64decode(match.group(1))
    except Exception:
        return None


def _escape_html_for_telegram(text):
    """Экранирует текст для parse_mode=HTML в Telegram, сохраняя теги <b>, <i>, <a href="">."""
    if not text or not isinstance(text, str):
        return ""
    # Заменяем разрешённые теги на плейсхолдеры (чтобы не экранировать их)
    placeholders = []
    def save_tag(m):
        placeholders.append(m.group(0))
        return "\x00" + str(len(placeholders) - 1) + "\x00"
    # Теги: <b>, </b>, <i>, </i>, <a href="...">, </a>
    pattern = r'</?b>|</?i>|<a href="[^"]*">|</a>'
    temp = re.sub(pattern, save_tag, text)
    temp = temp.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for i, ph in enumerate(placeholders):
        temp = temp.replace("\x00" + str(i) + "\x00", ph)
    return temp


class BroadcastService:
    @staticmethod
    def get_users_by_filters(filters):
        """Получает пользователей по фильтрам"""
        query = "SELECT user_id FROM users WHERE 1=1"
        params = []

        query += " AND is_banned = FALSE"

        if filters.get('gender') and filters['gender'] != 'all':
            query += " AND gender = ?"
            params.append(filters['gender'])

        if filters.get('min_age'):
            query += " AND age >= ?"
            params.append(int(filters['min_age']))

        if filters.get('max_age'):
            query += " AND age <= ?"
            params.append(int(filters['max_age']))

        if filters.get('cities') and filters['cities'] != ['all']:
            placeholders = ','.join(['?'] * len(filters['cities']))
            query += f" AND city IN ({placeholders})"
            params.extend(filters['cities'])

        if filters.get('active_days'):
            date_limit = (datetime.now(
            ) - timedelta(days=int(filters['active_days']))).strftime("%Y-%m-%d")
            query += " AND last_active >= ?"
            params.append(date_limit)

        if filters.get('referral_status') == 'with_referral':
            query += " AND referred_by IS NOT NULL"
        elif filters.get('referral_status') == 'without_referral':
            query += " AND referred_by IS NULL"

        query += " LIMIT ?"
        params.append(config.BROADCAST_LIMIT)

        users = execute_query(query, params, fetchall=True)
        return [user['user_id'] for user in users]

    @staticmethod
    def process_broadcast(broadcast_id, admin_id, chat_id, bot):
        """Обрабатывает рассылку в отдельном потоке"""
        try:
            broadcast = execute_query(
                "SELECT * FROM admin_broadcasts WHERE id = ?",
                (broadcast_id,), fetchone=True
            )

            if not broadcast:
                if admin_id:
                    bot.send_message(admin_id, "❌ Рассылка не найдена")
                return

            execute_query(
                "UPDATE admin_broadcasts SET status = 'sending' WHERE id = ?",
                (broadcast_id,), commit=True
            )

            filters = json.loads(broadcast['filters'])

            user_ids = BroadcastService.get_users_by_filters(filters)
            total_users = len(user_ids)

            if total_users == 0:
                if admin_id:
                    bot.send_message(
                        admin_id, "❌ Нет пользователей, соответствующих фильтрам"
                    )
                execute_query(
                    "UPDATE admin_broadcasts SET status = 'failed' WHERE id = ?",
                    (broadcast_id,), commit=True
                )
                return

            execute_query(
                "UPDATE admin_broadcasts SET total_users = ? WHERE id = ?",
                (total_users, broadcast_id), commit=True
            )

            if admin_id:
                bot.send_message(
                    admin_id,
                    f"🚀 *Начинаем рассылку #{broadcast_id}*\n\n"
                    f"📊 Получателей: {total_users:,}\n"
                    f"⏳ Начало: {datetime.now().strftime('%H:%M:%S')}\n\n"
                    f"📨 Отправка...",
                    parse_mode='Markdown'
                )

            sent = 0
            failed = 0

            for i, user_id in enumerate(user_ids):
                try:
                    if broadcast['content_type'] == 'text':
                        body = _escape_html_for_telegram(broadcast['content'])
                        bot.send_message(
                            user_id, body, parse_mode='HTML'
                        )
                    elif broadcast['content_type'] == 'photo':
                        caption = broadcast.get('caption', '') or None
                        if caption:
                            caption = _escape_html_for_telegram(caption)
                        bot.send_photo(
                            user_id,
                            broadcast['content'],
                            caption=caption,
                            parse_mode='HTML' if caption else None
                        )
                    elif broadcast['content_type'] == 'photo_base64':
                        # Фото хранится как data URL — декодируем и отправляем напрямую (без чата админа)
                        raw = _decode_photo_base64(broadcast['content'])
                        if raw:
                            buf = BytesIO(raw)
                            buf.seek(0)
                            caption = broadcast.get('caption', '') or None
                            if caption:
                                caption = _escape_html_for_telegram(caption)
                            bot.send_photo(
                                user_id,
                                buf,
                                caption=caption,
                                parse_mode='HTML' if caption else None
                            )
                        else:
                            failed += 1
                            continue
                    elif broadcast['content_type'] == 'link':
                        body = _escape_html_for_telegram(f'<a href="{broadcast["content"]}">Ссылка</a>')
                        bot.send_message(
                            user_id, body, parse_mode='HTML'
                        )

                    sent += 1

                    # Отправляем прогресс каждые 50 сообщений или в конце
                    if (i + 1) % 50 == 0 or (i + 1) == total_users:
                        BroadcastService._send_broadcast_progress(
                            broadcast_id, admin_id, total_users, sent, failed, bot
                        )

                    time.sleep(0.1)

                except Exception as e:
                    failed += 1
                    print(f"Ошибка отправки пользователю {user_id}: {e}")

            BroadcastService._complete_broadcast(
                broadcast_id, admin_id, total_users, sent, failed, bot
            )

        except Exception as e:
            print(f"Ошибка в process_broadcast: {e}")
            import traceback
            traceback.print_exc()

            if admin_id:
                try:
                    bot.send_message(
                        admin_id,
                        f"❌ *Ошибка рассылки #{broadcast_id}*\n\n"
                        f"Ошибка: {str(e)[:200]}",
                        parse_mode='Markdown'
                    )
                except:
                    pass

    @staticmethod
    def _send_broadcast_progress(broadcast_id, admin_id, total, sent, failed, bot):
        """Отправляет сообщение о прогрессе рассылки"""
        progress = (sent / total * 100) if total > 0 else 0

        execute_query(
            "UPDATE admin_broadcasts SET sent_users = ?, failed_users = ? WHERE id = ?",
            (sent, failed, broadcast_id), commit=True
        )

        if admin_id and (sent % max(50, total // 10) == 0 or sent == total):
            try:
                bot.send_message(
                    admin_id,
                    f"📨 *Рассылка #{broadcast_id}*\n\n"
                    f"📊 Прогресс: {sent}/{total} ({progress:.1f}%)\n"
                    f"✅ Успешно: {sent}\n"
                    f"❌ Ошибок: {failed}\n"
                    f"⏳ Осталось: {total - sent}",
                    parse_mode='Markdown'
                )
            except:
                pass

    @staticmethod
    def _complete_broadcast(broadcast_id, admin_id, total, sent, failed, bot):
        """Завершает рассылку и отправляет отчет"""
        execute_query(
            "UPDATE admin_broadcasts SET status = 'completed', sent_users = ?, failed_users = ?, completed = ? WHERE id = ?",
            (sent, failed, datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"), broadcast_id),
            commit=True
        )

        if admin_id:
            try:
                bot.send_message(
                    admin_id,
                    f"✅ *Рассылка #{broadcast_id} завершена!*\n\n"
                    f"📊 Итоги:\n"
                    f"• Всего получателей: {total}\n"
                    f"• Успешно отправлено: {sent}\n"
                    f"• Ошибок: {failed}\n"
                    f"• Успешность: {sent/total*100:.1f}%\n\n"
                    f"🕐 Время: {datetime.now().strftime('%H:%M:%S')}",
                    parse_mode='Markdown'
                )
            except:
                pass
