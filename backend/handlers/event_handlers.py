# handlers/event_handlers.py
from datetime import datetime
import telebot

from database import execute_query
from config import config
from keyboards.user_keyboards import *
from utils.helpers import escape_markdown
from services.achievements import AchievementService
from services.recommendations import RecommendationService


class EventHandlers:
    def __init__(self, bot):
        self.bot = bot
        self.user_state = {}
        self.user_data = {}

    def show_next_event(self, message, user_id, event_index=0, filter_type=None):
        """Показать следующее событие для просмотра"""
        chat_id = message.chat.id

        # Проверяем регистрацию
        user = execute_query(
            "SELECT * FROM users WHERE user_id=?", (user_id,), fetchone=True
        )

        if not user:
            return

        current_user = execute_query(
            "SELECT gender, city FROM users WHERE user_id=?", (user_id,), fetchone=True
        )

        if not current_user:
            self.bot.send_message(
                chat_id, "❌ Ошибка: данные пользователя не найдены")
            return

        # Получаем события по фильтру
        events = RecommendationService.get_events_by_filter(
            user_id, filter_type, limit=10)

        if not events:
            self.bot.send_message(chat_id, "🎉 Пока нет событий для просмотра!")
            return

        if event_index >= len(events):
            self.bot.send_message(
                chat_id, "🎉 Вы просмотрели все доступные события!")
            return

        event = events[event_index]

        # Формируем текст события
        event_text = f"""🎉 *{escape_markdown(event['title'])}*
🏷️ Категория: {event.get('category', '🎯 Разное')}

📝 {escape_markdown(event['description'])}
📅 Дата: {escape_markdown(event['event_date'])}
👤 Организатор: {escape_markdown(event['name'])} ({event['age']}, {event['gender']})
🏙️ Город: {escape_markdown(event['city'])}
👥 Для кого: {escape_markdown(event['target_gender'])}"""

        if event.get('relationship_status'):
            event_text += f"\n💖 Статус: {escape_markdown(event['relationship_status'])}"

        if event.get('purpose'):
            event_text += f"\n\n🎯 Цель: {escape_markdown(event['purpose'])}"
        else:
            event_text += f"\n\n🎯 Цель: куда-то сходить"

        if 'likes_count' in event:
            event_text += f"\n\n❤️ Лайков: {event['likes_count']}"

        # Сохраняем данные для навигации
        if user_id not in self.user_data:
            self.user_data[user_id] = {}

        self.user_data[user_id] = {
            'current_events': events,
            'current_index': event_index,
            'filter_type': filter_type
        }

        # Создаем клавиатуру
        keyboard = get_event_navigation_keyboard(
            event['id'], len(events), event_index, event.get('category'),
            is_search=True, show_organizer_profile=True, organizer_id=event['user_id']
        )

        try:
            if event.get('photo'):
                self.bot.send_photo(
                    chat_id, event['photo'], caption=event_text,
                    parse_mode='Markdown', reply_markup=keyboard
                )
            else:
                self.bot.send_message(
                    chat_id, event_text, parse_mode='Markdown', reply_markup=keyboard
                )
        except Exception as e:
            print(f"❌ Ошибка отправки сообщения: {e}")
            self.bot.send_message(
                chat_id, event_text, parse_mode='Markdown', reply_markup=keyboard
            )

    def handle_create_event(self, user_id, chat_id, text):
        """Обработка создания события"""
        state = self.user_state.get(user_id)

        if state == 'waiting_event_title':
            self.user_data[user_id] = {'event_title': text}
            self.user_state[user_id] = 'waiting_event_desc'
            self.bot.send_message(
                chat_id, "Опиши событие (куда и с кем хочешь пойти):")

        elif state == 'waiting_event_desc':
            self.user_data[user_id]['event_desc'] = text
            self.user_state[user_id] = 'waiting_event_category'
            self.bot.send_message(
                chat_id, "Выберите категорию события:", reply_markup=get_category_keyboard())

        elif state == 'waiting_event_category':
            if text == '⬅️ Назад':
                self.user_state[user_id] = 'waiting_event_title'
                self.bot.send_message(chat_id, "Введите название события:")
            elif text in config.EVENT_CATEGORIES.keys() or text == '🎯 Без категории':
                category = text if text != '🎯 Без категории' else '🎯 Разное'
                self.user_data[user_id]['category'] = category
                self.user_state[user_id] = 'waiting_event_target_gender'
                self.bot.send_message(
                    chat_id, "Кому будет показываться событие?", reply_markup=get_target_gender_keyboard()
                )
            else:
                self.bot.send_message(
                    chat_id, "Выберите категорию из списка:", reply_markup=get_category_keyboard()
                )

        elif state == 'waiting_event_target_gender':
            if text in ['Все', 'Мужчины', 'Женщины']:
                self.user_data[user_id]['target_gender'] = text
                self.user_state[user_id] = 'waiting_event_date'
                self.bot.send_message(
                    chat_id, "Введите дату события (например: 25.12.2024 19:00):"
                )
            else:
                self.bot.send_message(
                    chat_id, "Выберите вариант из клавиатуры:", reply_markup=get_target_gender_keyboard()
                )

        elif state == 'waiting_event_date':
            try:
                event_date = datetime.strptime(text, "%d.%m.%Y %H:%M")
                title = self.user_data[user_id]['event_title']
                desc = self.user_data[user_id]['event_desc']
                target_gender = self.user_data[user_id]['target_gender']
                category = self.user_data[user_id].get('category', '🎯 Разное')

                user = execute_query(
                    "SELECT city FROM users WHERE user_id=?", (user_id,), fetchone=True
                )
                city = user['city'] if user else "Не указан"

                event_id = execute_query(
                    '''INSERT INTO events (user_id, title, description, event_date, target_gender, city, category, created) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id''',
                    (user_id, title, desc, event_date.strftime("%Y-%m-%d %H:%M:%S"),
                     target_gender, city, category, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    commit=True
                )

                execute_query(
                    "UPDATE users SET purpose=? WHERE user_id=?",
                    (f"🎯 {title}", user_id), commit=True
                )

                # Начисляем очки
                AchievementService.update_user_points(
                    user_id, 10, "за создание события")

                # Проверяем достижения
                events_count = execute_query(
                    "SELECT COUNT(*) as count FROM events WHERE user_id=? AND is_hidden = FALSE",
                    (user_id,), fetchone=True
                )['count']

                if events_count == 1:
                    AchievementService.unlock_achievement(
                        user_id, "first_event")

                if event_date.hour < 12:
                    AchievementService.unlock_achievement(
                        user_id, "early_bird")

                del self.user_state[user_id]
                if user_id in self.user_data:
                    del self.user_data[user_id]

                self.bot.send_message(
                    chat_id, "✅ Событие успешно создано! Откройте приложение:", reply_markup=get_start_webapp_keyboard()
                )

            except ValueError:
                self.bot.send_message(
                    chat_id,
                    "Неверный формат даты! Введи: ДД.ММ.ГГГГ ЧЧ:ММ\nПример: 25.12.2024 19:00"
                )
