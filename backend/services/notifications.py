# services/notifications.py
import logging
from datetime import datetime
import telebot

from database import execute_query
from config import config
from utils.helpers import escape_markdown

_log = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    def _get_bot(bot=None):
        """Единый экземпляр бота для отправки (из бота передаётся bot, из API создаётся новый)."""
        if bot is not None:
            return bot
        return telebot.TeleBot(config.BOT_TOKEN)

    @staticmethod
    def _get_mini_app_likes_url():
        url = (config.MINI_APP_URL or "").strip()
        if not url:
            url = "https://telegram-dating-app1.onrender.com"
        return f"{url.rstrip('/')}/likes"

    @staticmethod
    def _send_with_fallback(bot, chat_id: int, text: str, open_url: str):
        """Отправить сообщение с кнопкой «Открыть приложение»; при ошибке — без кнопки, с ссылкой в тексте."""
        chat_id = int(chat_id)
        keyboard = telebot.types.InlineKeyboardMarkup()
        if open_url.startswith("https://"):
            keyboard.add(
                telebot.types.InlineKeyboardButton(
                    "📱 Открыть приложение",
                    web_app=telebot.types.WebAppInfo(url=open_url),
                )
            )
        else:
            keyboard.add(
                telebot.types.InlineKeyboardButton("📱 Открыть приложение", url=open_url)
            )
        try:
            bot.send_message(chat_id, text, parse_mode='Markdown', reply_markup=keyboard)
            return True
        except Exception as e1:
            err_str = str(e1).lower()
            if "can't initiate" in err_str or "blocked" in err_str or "forbidden" in err_str:
                _log.warning(
                    "Уведомление не доставлено (chat_id=%s): пользователь не начал диалог с ботом или заблокировал бота. Нужно нажать /start в боте.",
                    chat_id,
                )
            else:
                _log.warning("Отправка с кнопкой не удалась (chat_id=%s), пробуем без кнопки: %s", chat_id, e1)
            try:
                fallback_text = text + f"\n\n📱 Открыть приложение: {open_url}"
                bot.send_message(chat_id, fallback_text, parse_mode='Markdown')
                return True
            except Exception as e2:
                _log.exception("Не удалось отправить уведомление (chat_id=%s): %s", chat_id, e2)
                return False
        return False

    @staticmethod
    def send_like_notification(creator_id, liker_id, event, like_id, bot=None):
        """Короткое уведомление о лайке + кнопка «Открыть приложение» (обработка лайков в Mini App)."""
        if not config.BOT_TOKEN:
            _log.warning("BOT_TOKEN не задан — уведомление о лайке не отправлено")
            return
        try:
            bot = NotificationService._get_bot(bot)
        except Exception as e:
            _log.exception("Не удалось создать бота для уведомления: %s", e)
            return
        user = execute_query(
            "SELECT is_banned FROM users WHERE user_id = ?",
            (creator_id,), fetchone=True
        )
        if user and user.get('is_banned'):
            return
        open_likes_url = NotificationService._get_mini_app_likes_url()
        text = "💌 *Пришёл новый лайк!*\n\nОткройте приложение, чтобы посмотреть кто это и ответить взаимностью или пропустить."
        NotificationService._send_with_fallback(
            bot, int(creator_id), text, open_likes_url
        )

    @staticmethod
    def send_mutual_response_to_liker(liker_id, creator_id, event_id, bot=None):
        """Короткое уведомление о взаимной симпатии + кнопка «Открыть приложение» (профиль смотреть в приложении)."""
        if not config.BOT_TOKEN:
            _log.warning("BOT_TOKEN не задан — уведомление о взаимности не отправлено")
            return
        try:
            bot = NotificationService._get_bot(bot)
        except Exception as e:
            _log.exception("Не удалось создать бота для уведомления: %s", e)
            return
        user = execute_query(
            "SELECT is_banned FROM users WHERE user_id = ?",
            (liker_id,), fetchone=True
        )
        if user and user.get('is_banned'):
            return
        open_likes_url = NotificationService._get_mini_app_likes_url()
        text = "💞 *Взаимная симпатия!*\n\nПользователь ответил на ваш лайк. Откройте приложение, чтобы посмотреть профиль и связаться."
        NotificationService._send_with_fallback(
            bot, int(liker_id), text, open_likes_url
        )

    @staticmethod
    def send_match_notification(user1_id, user2_id, event_id, bot=None):
        """Отправить уведомление о матчинге обоим пользователям (bot опционален)."""
        if not config.BOT_TOKEN and bot is None:
            _log.warning("BOT_TOKEN не задан — уведомление о матчинге не отправлено")
            return
        bot = NotificationService._get_bot(bot)
        if event_id:
            event = execute_query(
                "SELECT title, description, event_date FROM events WHERE id = ?",
                (event_id,), fetchone=True
            )
        else:
            event = None

        user1 = execute_query(
            "SELECT name, username FROM users WHERE user_id = ? AND is_banned = FALSE",
            (user1_id,), fetchone=True
        )

        user2 = execute_query(
            "SELECT name, username FROM users WHERE user_id = ? AND is_banned = FALSE",
            (user2_id,), fetchone=True
        )

        if not user1 or not user2:
            return

        user1_contact = f"@{user1['username']}" if user1.get(
            'username') else "не указан"
        user2_contact = f"@{user2['username']}" if user2.get(
            'username') else "не указан"

        if event:
            notification_user1 = f"""🤝 *Матч! Взаимная симпатия!*

👤 *Вы нашли взаимность с пользователем:*
📛 Имя: {escape_markdown(user2['name'])}
📱 Контакт: {escape_markdown(user2_contact)}

🎉 *К событию:*
*{escape_markdown(event['title'])}*
📅 Дата: {escape_markdown(event['event_date'])}
📝 Описание: {escape_markdown(event['description'][:150])}{'...' if len(event['description']) > 150 else ''}

💬 *Теперь вы можете связаться для обсуждения встречи!*

💡 *Совет:* Напишите первое сообщение и договоритесь о деталях встречи!"""

            notification_user2 = f"""🤝 *Матч! Взаимная симпатия!*

👤 *Вы нашли взаимность с пользователем:*
📛 Имя: {escape_markdown(user1['name'])}
📱 Контакт: {escape_markdown(user1_contact)}

🎉 *К событию:*
*{escape_markdown(event['title'])}*
📅 Дата: {escape_markdown(event['event_date'])}
📝 Описание: {escape_markdown(event['description'][:150])}{'...' if len(event['description']) > 150 else ''}

💬 *Теперь вы можете связаться для обсуждения встречи!*

💡 *Совет:* Напишите первое сообщение и договоритесь о деталях встречи!"""
        else:
            notification_user1 = f"""🤝 *Матч! Взаимная симпатия!*

👤 *Вы нашли взаимность с пользователем:*
📛 Имя: {escape_markdown(user2['name'])}
📱 Контакт: {escape_markdown(user2_contact)}

💬 *Теперь вы можете связаться для обсуждения встречи!*

💡 *Совет:* Напишите первое сообщение и договоритесь о деталях встречи!"""

            notification_user2 = f"""🤝 *Матч! Взаимная симпатия!*

👤 *Вы нашли взаимность с пользователем:*
📛 Имя: {escape_markdown(user1['name'])}
📱 Контакт: {escape_markdown(user1_contact)}

💬 *Теперь вы можете связаться для обсуждения встречи!*

💡 *Совет:* Напишите первое сообщение и договоритесь о деталях встречи!"""

        try:
            bot.send_message(user1_id, notification_user1,
                             parse_mode='Markdown')
            bot.send_message(user2_id, notification_user2,
                             parse_mode='Markdown')
        except Exception as e:
            print(f"Ошибка отправки уведомлений о матчинге: {e}")

    @staticmethod
    def send_points_notification(user_id, points_to_add, reason):
        """Отправить уведомление о начислении очков"""
        try:
            bot = telebot.TeleBot(config.BOT_TOKEN)
            bot.send_message(user_id, f"🎉 +{points_to_add} очков! {reason}")
        except:
            pass

    @staticmethod
    def send_achievement_notification(user_id, achievement):
        """Отправить уведомление о получении достижения"""
        try:
            bot = telebot.TeleBot(config.BOT_TOKEN)
            bot.send_message(
                user_id,
                f"""{achievement['emoji']} *Новое достижение!*

🏆 *{achievement['name']}*
📝 {achievement['description']}

🎯 +{achievement.get('points', 0)} очков рейтинга!""",
                parse_mode='Markdown'
            )
        except:
            pass
