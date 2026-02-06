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
    def send_like_notification(creator_id, liker_id, event, like_id, bot=None):
        """Короткое уведомление о лайке + кнопка «Открыть приложение» (обработка лайков в Mini App)."""
        bot = NotificationService._get_bot(bot)
        user = execute_query(
            "SELECT is_banned FROM users WHERE user_id = ?",
            (creator_id,), fetchone=True
        )
        if user and user['is_banned'] == 1:
            return
        import os
        mini_app_url = (os.getenv("MINI_APP_URL") or "").rstrip("/")
        if not mini_app_url:
            mini_app_url = "https://telegram-dating-app1.onrender.com"
        open_likes_url = f"{mini_app_url}/likes"
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
            print(f"❌ Ошибка отправки уведомления: {e}")

    @staticmethod
    def send_mutual_response_to_liker(liker_id, creator_id, event_id, bot=None):
        """Отправить тому, кто поставил лайк: уведомление о взаимности + полный профиль ответившего + событие + username."""
        bot = NotificationService._get_bot(bot)
        creator = execute_query(
            "SELECT name, age, gender, city, relationship_status, photo, purpose, username FROM users WHERE user_id = ? AND is_banned = FALSE",
            (creator_id,), fetchone=True
        )
        if not creator:
            return
        username_display = f"@{creator['username']}" if creator.get('username') else "не указан"
        profile_block = f"""👤 *Профиль пользователя:*

📛 *Имя:* {escape_markdown(creator['name'])}
🎂 *Возраст:* {escape_markdown(str(creator['age']))}
⚧️ *Пол:* {escape_markdown(creator['gender'])}
🏙️ *Город:* {escape_markdown(creator['city']) if creator['city'] else 'Не указан'}
💖 *Статус:* {escape_markdown(creator['relationship_status']) if creator['relationship_status'] else 'Не указан'}
🎯 *Цель:* {escape_markdown(creator['purpose']) if creator['purpose'] else 'куда\\-то сходить'}
📱 *Контакт в Telegram:* {escape_markdown(username_display)}"""
        event_block = ""
        if event_id:
            event_row = execute_query(
                "SELECT title, description, event_date, category FROM events WHERE id = ?",
                (event_id,), fetchone=True
            )
            if event_row:
                event_block = f"""

*Ответ на лайк к вашему событию:*
🎉 *{escape_markdown(event_row['title'])}*
🏷️ *Категория:* {escape_markdown(event_row.get('category') or '🎯 Разное')}
📅 *Дата:* {escape_markdown(event_row['event_date'])}
📝 *Описание:* {escape_markdown(event_row['description'][:100])}{'...' if len(event_row['description']) > 100 else ''}"""
        text = f"""💞 *Взаимная симпатия!*

Пользователь ответил взаимностью на ваш лайк.

{profile_block}{event_block}

💬 *Можете написать в Telegram:* {escape_markdown(username_display)}"""
        try:
            if creator.get('photo'):
                bot.send_photo(
                    liker_id,
                    creator['photo'],
                    caption=text,
                    parse_mode='Markdown',
                )
            else:
                bot.send_message(liker_id, text + "\n\n📸 *Фото не загружено*", parse_mode='Markdown')
        except Exception as e:
            print(f"❌ Ошибка отправки уведомления о взаимности (liker): {e}")

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
