# services/notifications.py
from datetime import datetime
import telebot

from database import execute_query
from config import config
from utils.helpers import escape_markdown


class NotificationService:
    @staticmethod
    def send_like_notification(creator_id, liker_id, event, like_id, bot):
        """Отправить уведомление о лайке создателю события"""
        # Проверяем блокировку
        user = execute_query(
            "SELECT is_banned FROM users WHERE user_id = ?",
            (creator_id,), fetchone=True
        )

        if user and user['is_banned'] == 1:
            return

        # Получаем полную информацию о событии
        event_full = execute_query(
            "SELECT title, description, event_date, category FROM events WHERE id = ?",
            (event['id'],), fetchone=True
        )

        # Получаем информацию о пользователе, который лайкнул
        liker = execute_query(
            "SELECT name, age, gender, city, relationship_status, photo, purpose, username FROM users WHERE user_id=? AND is_banned = FALSE",
            (liker_id,), fetchone=True
        )

        if liker:
            username_display = f"@{liker['username']}" if liker.get(
                'username') else "не указан"

            profile_text = f"""💌 *Новый лайк!*

👤 *Профиль пользователя:*

📛 *Имя:* {escape_markdown(liker['name'])}
🎂 *Возраст:* {escape_markdown(str(liker['age']))}
⚧️ *Пол:* {escape_markdown(liker['gender'])}
🏙️ *Город:* {escape_markdown(liker['city']) if liker['city'] else 'Не указан'}
💖 *Статус:* {escape_markdown(liker['relationship_status']) if liker['relationship_status'] else 'Не указан'}
🎯 *Цель:* {escape_markdown(liker['purpose']) if liker['purpose'] else 'куда\\-то сходить'}
📱 *Контакт:* {escape_markdown(username_display)}

*Лайкнул ваше событие:*
🎉 *{escape_markdown(event_full['title'])}*
🏷️ *Категория:* {escape_markdown(event_full.get('category', '🎯 Разное'))}
📅 *Дата:* {escape_markdown(event_full['event_date'])}
📝 *Описание:* {escape_markdown(event_full['description'][:100])}{'...' if len(event_full['description']) > 100 else ''}"""

            from keyboards.user_keyboards import get_mutual_notification_keyboard
            keyboard = get_mutual_notification_keyboard(like_id)

            # Добавляем кнопку для жалобы
            keyboard.add(
                telebot.types.InlineKeyboardButton(
                    "🚨 Пожаловаться на пользователя", callback_data=f"report_user_{liker_id}")
            )

            try:
                if liker['photo']:
                    bot.send_photo(
                        creator_id,
                        liker['photo'],
                        caption=profile_text,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                else:
                    bot.send_message(
                        creator_id,
                        profile_text + "\n\n📸 *Пользователь не загрузил фото*",
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
            except Exception as e:
                print(f"❌ Ошибка отправки уведомления: {e}")

    @staticmethod
    def send_match_notification(user1_id, user2_id, event_id, bot):
        """Отправить уведомление о матчинге обоим пользователям"""
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
