# services/notifications.py
from datetime import datetime
import telebot

from database import execute_query
from config import config
from utils.helpers import escape_markdown


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
    def send_like_notification(creator_id, liker_id, event, like_id, bot=None):
        """Короткое уведомление о лайке + кнопка «Открыть приложение» (обработка лайков в Mini App)."""
        if not config.BOT_TOKEN:
            print("❌ BOT_TOKEN не задан — уведомление о лайке не отправлено")
            return
        bot = NotificationService._get_bot(bot)
        user = execute_query(
            "SELECT is_banned FROM users WHERE user_id = ?",
            (creator_id,), fetchone=True
        )
        if user and user.get('is_banned'):
            return
        open_likes_url = NotificationService._get_mini_app_likes_url()
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(
            telebot.types.InlineKeyboardButton(
                "📱 Открыть приложение",
                web_app=telebot.types.WebAppInfo(url=open_likes_url),
            )
        )
        try:
            bot.send_message(
                creator_id,
                "💌 *Пришёл новый лайк!*\n\nОткройте приложение, чтобы посмотреть кто это и ответить взаимностью или пропустить.",
                parse_mode='Markdown',
                reply_markup=keyboard,
            )
        except Exception as e:
            print(f"❌ Ошибка отправки уведомления о лайке (creator_id={creator_id}): {e}")

    @staticmethod
    def send_mutual_response_to_liker(liker_id, creator_id, event_id, bot=None):
        """Короткое уведомление о взаимной симпатии + кнопка «Открыть приложение» (профиль смотреть в приложении)."""
        if not config.BOT_TOKEN:
            return
        bot = NotificationService._get_bot(bot)
        user = execute_query(
            "SELECT is_banned FROM users WHERE user_id = ?",
            (liker_id,), fetchone=True
        )
        if user and user.get('is_banned'):
            return
        open_likes_url = NotificationService._get_mini_app_likes_url()
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(
            telebot.types.InlineKeyboardButton(
                "📱 Открыть приложение",
                web_app=telebot.types.WebAppInfo(url=open_likes_url),
            )
        )
        try:
            bot.send_message(
                liker_id,
                "💞 *Взаимная симпатия!*\n\nПользователь ответил на ваш лайк. Откройте приложение, чтобы посмотреть профиль и связаться.",
                parse_mode='Markdown',
                reply_markup=keyboard,
            )
        except Exception as e:
            print(f"❌ Ошибка отправки уведомления о взаимности (liker_id={liker_id}): {e}")

    @staticmethod
    def send_match_notification(user1_id, user2_id, event_id, bot=None):
        """Отправить уведомление о матчинге обоим пользователям (bot опционален)."""
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
