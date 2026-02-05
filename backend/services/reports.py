# services/reports.py
from datetime import datetime
from database import execute_query
from config import config
from utils.helpers import escape_markdown
import telebot


class ReportService:
    @staticmethod
    def create_report(reporter_id, reported_user_id, reason):
        """Создает жалобу на пользователя"""
        try:
            report_id = execute_query(
                '''INSERT INTO reports (reporter_id, reported_user_id, reason, created) 
                   VALUES (?, ?, ?, ?) RETURNING id''',
                (reporter_id, reported_user_id, reason,
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                commit=True
            )

            reporter = execute_query(
                "SELECT name FROM users WHERE user_id = ?",
                (reporter_id,), fetchone=True
            )

            reported_user = execute_query(
                "SELECT name, user_id FROM users WHERE user_id = ?",
                (reported_user_id,), fetchone=True
            )

            reporter_name = reporter['name'] if reporter else f"ID: {reporter_id}"
            reported_name = reported_user[
                'name'] if reported_user else f"ID: {reported_user_id}"

            # Отправляем уведомление админам
            bot = telebot.TeleBot(config.BOT_TOKEN)

            for admin_id in config.ADMINS:
                try:
                    markup = telebot.types.InlineKeyboardMarkup()
                    markup.add(
                        telebot.types.InlineKeyboardButton(
                            "👁️ Просмотреть профиль",
                            callback_data=f"admin_view_user_{reported_user_id}"
                        ),
                        telebot.types.InlineKeyboardButton(
                            "⛔ Заблокировать",
                            callback_data=f"admin_ban_{reported_user_id}_from_report"
                        ),
                        telebot.types.InlineKeyboardButton(
                            "✅ Отклонить жалобу",
                            callback_data=f"admin_dismiss_report_{report_id}"
                        )
                    )

                    bot.send_message(
                        admin_id,
                        f"🚨 *Новая жалоба на пользователя!*\n\n"
                        f"👤 *Жалобщик:* {escape_markdown(reporter_name)}\n"
                        f"⚠️ *На кого:* {escape_markdown(reported_name)}\n"
                        f"📝 *Причина:* {escape_markdown(reason)}\n\n"
                        f"🆔 ID жалобы: `{report_id}`\n"
                        f"🆔 ID пользователя: `{reported_user_id}`",
                        parse_mode='Markdown',
                        reply_markup=markup
                    )
                except Exception as e:
                    print(
                        f"Ошибка отправки уведомления админу {admin_id}: {e}")

            return report_id
        except Exception as e:
            print(f"Ошибка создания жалобы: {e}")
            return None

    @staticmethod
    def get_reports_by_status(status='pending'):
        """Получает жалобы по статусу"""
        return execute_query(
            "SELECT * FROM reports WHERE status = ? ORDER BY created DESC",
            (status,), fetchall=True
        )

    @staticmethod
    def update_report_status(report_id, status, admin_notes=None):
        """Обновляет статус жалобы"""
        execute_query(
            '''UPDATE reports SET status = ?, admin_notes = ?, resolved = ? 
               WHERE id = ?''',
            (status, admin_notes, datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"), report_id),
            commit=True
        )

    @staticmethod
    def ban_user(user_id, reason, banned_by):
        """Блокирует пользователя"""
        try:
            execute_query(
                '''UPDATE users SET is_banned = 1, ban_reason = ?, banned_date = ? 
                   WHERE user_id = ?''',
                (reason, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id),
                commit=True
            )

            execute_query(
                '''INSERT INTO bans (user_id, reason, banned_by, banned_date) 
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT (user_id) DO UPDATE SET
                     reason = EXCLUDED.reason,
                     banned_by = EXCLUDED.banned_by,
                     banned_date = EXCLUDED.banned_date''',
                (user_id, reason, banned_by,
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                commit=True
            )

            execute_query(
                "UPDATE events SET is_hidden = 1 WHERE user_id = ?",
                (user_id,), commit=True
            )

            return True
        except Exception as e:
            print(f"Ошибка при блокировке пользователя: {e}")
            return False

    @staticmethod
    def unban_user(user_id):
        """Разблокирует пользователя"""
        try:
            execute_query(
                '''UPDATE users SET is_banned = 0, ban_reason = NULL, banned_date = NULL 
                   WHERE user_id = ?''',
                (user_id,), commit=True
            )

            execute_query(
                "DELETE FROM bans WHERE user_id = ?",
                (user_id,), commit=True
            )

            execute_query(
                "UPDATE events SET is_hidden = 0 WHERE user_id = ?",
                (user_id,), commit=True
            )

            return True
        except Exception as e:
            print(f"Ошибка при разблокировке пользователя: {e}")
            return False

    @staticmethod
    def appeal_ban(user_id, appeal_text):
        """Подача апелляции на блокировку"""
        try:
            # Раньше апелляция работала только если существовала "закрытая" жалоба (status='resolved').
            # Если бан выдан напрямую админом без закрытия жалобы — апелляции некуда было записаться.
            # Теперь: пытаемся привязать к последнему репорту, а если его нет — создаём служебную запись.
            report = execute_query(
                '''SELECT id FROM reports
                   WHERE reported_user_id = ?
                   ORDER BY created DESC LIMIT 1''',
                (user_id,), fetchone=True
            )

            if report:
                report_id = report['id']
                execute_query(
                    '''UPDATE reports
                       SET appeal_status = 'pending', appeal_text = ?
                       WHERE id = ?''',
                    (appeal_text, report_id),
                    commit=True
                )
            else:
                # Служебная запись, чтобы апелляцию можно было хранить и трекать
                report_id = execute_query(
                    '''INSERT INTO reports (reporter_id, reported_user_id, reason, status, created, appeal_status, appeal_text)
                       VALUES (?, ?, ?, 'resolved', ?, 'pending', ?) RETURNING id''',
                    (
                        user_id,
                        user_id,
                        "Апелляция на блокировку (без исходной жалобы)",
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        appeal_text,
                    ),
                    commit=True
                )

            # Уведомляем админов (всегда, независимо от того была ли запись в reports)
            bot = telebot.TeleBot(config.BOT_TOKEN)

            user = execute_query(
                "SELECT name FROM users WHERE user_id = ?",
                (user_id,), fetchone=True
            )

            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton(
                    "👁️ Просмотреть профиль",
                    callback_data=f"admin_view_user_{user_id}"
                ),
                telebot.types.InlineKeyboardButton(
                    "✅ Разблокировать",
                    callback_data=f"admin_unban_{user_id}"
                ),
                telebot.types.InlineKeyboardButton(
                    "❌ Отклонить апелляцию",
                    callback_data=f"admin_reject_appeal_{user_id}"
                )
            )

            for admin_id in config.ADMINS:
                try:
                    bot.send_message(
                        admin_id,
                        f"📢 *Новая апелляция на блокировку!*\n\n"
                        f"👤 *Пользователь:* {escape_markdown(user['name'] if user else f'ID: {user_id}')}\n"
                        f"🆔 *ID:* `{user_id}`\n"
                        f"🆔 *ID обращения:* `{report_id}`\n"
                        f"📝 *Текст апелляции:*\n{escape_markdown(appeal_text)}",
                        parse_mode='Markdown',
                        reply_markup=markup
                    )
                except Exception as e:
                    print(f"Ошибка отправки уведомления админу {admin_id}: {e}")

            return True
        except Exception as e:
            print(f"Ошибка при подаче апелляции: {e}")
            return False
