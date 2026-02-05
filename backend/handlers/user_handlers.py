# handlers/user_handlers.py
import telebot
from datetime import datetime
import json
from database import execute_query
from config import config
from keyboards.user_keyboards import (
    get_start_webapp_keyboard,
    get_main_menu,
    get_gender_keyboard,
    get_relationship_keyboard,
    get_user_profile_keyboard,
    get_filter_keyboard,
    get_event_action_keyboard,
    get_yes_no_keyboard,
    get_ban_notification_keyboard,
)
from utils.helpers import escape_markdown, find_similar_city
from services.achievements import AchievementService
from services.recommendations import RecommendationService


class UserHandlers:
    def __init__(self, bot, shared_user_state=None, shared_user_data=None):
        self.bot = bot
        # Общие состояния/данные нужны, чтобы сценарии из callback (жалобы/апелляции)
        # корректно завершались после ввода текста пользователем.
        self.user_state = shared_user_state if shared_user_state is not None else {}
        self.user_data = shared_user_data if shared_user_data is not None else {}
        # Инициализируем event_handlers для обработки создания событий
        from handlers.event_handlers import EventHandlers
        self.event_handlers = EventHandlers(self.bot)
    
    def _remove_keyboard(self):
        """Вспомогательная функция для скрытия клавиатуры"""
        return telebot.types.ReplyKeyboardRemove(selective=False)

    def handle_start(self, message):
        """Обработка команды /start"""
        user_id = message.from_user.id
        chat_id = message.chat.id

        # Проверяем блокировку
        user = execute_query(
            "SELECT is_banned, ban_reason, banned_date FROM users WHERE user_id = ?",
            (user_id,), fetchone=True
        )

        if user and user['is_banned'] == 1:
            reason = user['ban_reason'] or "Нарушение правил"
            date = user['banned_date'][:10] if user['banned_date'] else "неизвестно"

            markup = get_ban_notification_keyboard(user_id)
            self.bot.send_message(
                chat_id,
                f"⛔ *Ваш аккаунт заблокирован!*\n\n"
                f"📝 *Причина:* {reason}\n"
                f"📅 *Дата блокировки:* {date}\n\n"
                f"Если вы считаете, что это ошибка, вы можете оспорить блокировку:",
                parse_mode='Markdown',
                reply_markup=markup
            )
            return

        # Проверяем существующего пользователя
        existing_user = execute_query(
            "SELECT * FROM users WHERE user_id = ?", (user_id,), fetchone=True
        )

        if existing_user:
            execute_query(
                "UPDATE users SET last_active = ? WHERE user_id = ?",
                (datetime.now().strftime("%Y-%m-%d"), user_id), commit=True
            )
            self.bot.send_message(
                chat_id, "С возвращением! 👋", reply_markup=get_main_menu())
            self.bot.send_message(
                chat_id,
                "📱 Открыть приложение в браузере:",
                reply_markup=get_start_webapp_keyboard(),
            )
            AchievementService.check_achievements(user_id)
            return

        # Обработка реферальной ссылки
        referral_code_param = None
        if len(message.text.split()) > 1:
            referral_code_param = message.text.split()[1]

        if referral_code_param and referral_code_param.startswith('REF_'):
            referrer = execute_query(
                "SELECT user_id, name, referral_code FROM users WHERE referral_code = ? AND is_banned = 0",
                (referral_code_param,), fetchone=True
            )

            if referrer and referrer['user_id'] != user_id:
                self.user_data[user_id] = {'referred_by': referrer['user_id']}

                self.bot.send_message(
                    chat_id,
                    f"👋 Вы зашли по приглашению *{referrer['name']}*\n\n"
                    f"🎁 После регистрации вы получите *50 бонусных очков!*\n\n"
                    f"Для регистрации введи своё имя:",
                    parse_mode='Markdown'
                )
                self.user_state[user_id] = 'waiting_name'
                return

        # Скрываем клавиатуру для незарегистрированных пользователей
        remove_keyboard = self._remove_keyboard()
        
        # Приветственное сообщение с фото
        welcome_text = (
            "Хочешь куда-то сходить но не знаешь с кем — создай встречу. Бот покажет её людям рядом.\n\n"
            "Откликнутся — идите. Никакой лишней болтовни.\n\n"
            "👉 *Как тебя зовут?*"
        )
        
        # Кнопка открытия Mini App
        webapp_markup = get_start_webapp_keyboard()
        # Отправляем фото из папки images, если оно есть
        import os
        image_path = os.path.join('images', 'Spon.png')
        if os.path.exists(image_path):
            try:
                with open(image_path, 'rb') as photo:
                    self.bot.send_photo(
                        chat_id,
                        photo,
                        caption=welcome_text,
                        parse_mode='Markdown',
                        reply_markup=remove_keyboard,
                    )
            except Exception as e:
                print(f"Ошибка отправки фото: {e}")
                self.bot.send_message(
                    chat_id, welcome_text, parse_mode='Markdown', reply_markup=remove_keyboard)
        else:
            self.bot.send_message(
                chat_id, welcome_text, parse_mode='Markdown', reply_markup=remove_keyboard)
        self.bot.send_message(
            chat_id,
            "📱 Или откройте приложение:",
            reply_markup=webapp_markup,
        )
        self.user_state[user_id] = 'waiting_name'

    def handle_text(self, message):
        """Обработка текстовых сообщений"""
        user_id = message.from_user.id
        chat_id = message.chat.id
        text = message.text

        # Проверяем регистрацию в начале (кроме состояний регистрации)
        state = self.user_state.get(user_id)
        if state and not state.startswith('waiting_') and not state.startswith('edit_') and not state.startswith('appeal_ban_'):
            user = execute_query(
                "SELECT * FROM users WHERE user_id = ?", (user_id,), fetchone=True
            )
            if not user:
                # Скрываем клавиатуру для незарегистрированных пользователей
                self.bot.send_message(
                    chat_id, "Вы не зарегистрированы. Напишите /start", reply_markup=self._remove_keyboard())
                return

        # Проверяем блокировку (кроме апелляции)
        if not (state and state.startswith('appeal_ban_')):
            user = execute_query(
                "SELECT is_banned FROM users WHERE user_id = ?", (user_id,), fetchone=True
            )
            if user and user['is_banned'] == 1:
                self._show_ban_message(user_id, chat_id)
                return

        # Жалобы: после нажатия кнопки "Пожаловаться" просим причину, а затем создаем жалобу.
        if state and (state.startswith('report_user_') or state.startswith('report_organizer_')):
            try:
                if state.startswith('report_user_'):
                    reported_user_id = int(state.split("_")[2])
                else:
                    event_id = int(state.split("_")[2])
                    event = execute_query(
                        "SELECT user_id FROM events WHERE id = ?",
                        (event_id,), fetchone=True
                    )
                    reported_user_id = int(event['user_id']) if event else None

                reason = text.strip()
                if not reason:
                    self.bot.send_message(chat_id, "Введите причину жалобы текстом:")
                    return

                if not reported_user_id:
                    self.bot.send_message(chat_id, "❌ Не удалось найти пользователя для жалобы.")
                else:
                    from services.reports import ReportService
                    report_id = ReportService.create_report(user_id, reported_user_id, reason)
                    if report_id:
                        self.bot.send_message(
                            chat_id,
                            "✅ *Жалоба отправлена администратору.*\n\n"
                            "Спасибо! Мы рассмотрим её в ближайшее время.",
                            parse_mode='Markdown',
                            reply_markup=get_main_menu()
                        )
                    else:
                        self.bot.send_message(chat_id, "❌ Не удалось отправить жалобу. Попробуйте позже.")

                del self.user_state[user_id]
                return
            except Exception as e:
                print(f"Ошибка при отправке жалобы: {e}")
                self.bot.send_message(chat_id, "❌ Ошибка отправки жалобы. Попробуйте позже.")
                if user_id in self.user_state:
                    del self.user_state[user_id]
                return

        # Апелляция: после кнопки "Оспорить блокировку" пользователь пишет текст → уходит админам.
        if state and state.startswith('appeal_ban_'):
            try:
                from services.reports import ReportService
                appeal_text = text.strip()
                if not appeal_text:
                    self.bot.send_message(chat_id, "Введите текст апелляции:")
                    return

                ok = ReportService.appeal_ban(user_id, appeal_text)
                if ok:
                    self.bot.send_message(
                        chat_id,
                        "✅ *Апелляция отправлена администратору.*\n\n"
                        "Ожидайте ответа.",
                        parse_mode='Markdown'
                    )
                else:
                    self.bot.send_message(chat_id, "❌ Не удалось отправить апелляцию. Попробуйте позже.")

                del self.user_state[user_id]
                return
            except Exception as e:
                print(f"Ошибка при отправке апелляции: {e}")
                self.bot.send_message(chat_id, "❌ Ошибка отправки апелляции. Попробуйте позже.")
                if user_id in self.user_state:
                    del self.user_state[user_id]
                return

        # Админские сообщения обрабатываются на уровне `bot.py` отдельным обработчиком
        # (чтобы состояния админ-панели не терялись между сообщениями).

        # Обработка состояний создания события
        if state and state.startswith('waiting_event_'):
            # Синхронизируем состояния между handlers
            self.event_handlers.user_state = self.user_state
            self.event_handlers.user_data = self.user_data
            self.event_handlers.handle_create_event(user_id, chat_id, text)
            return

        # Обработка состояний регистрации
        if state == 'waiting_name':
            self._handle_waiting_name(user_id, chat_id, text)
        elif state == 'waiting_age':
            self._handle_waiting_age(user_id, chat_id, text)
        elif state == 'waiting_gender':
            self._handle_waiting_gender(user_id, chat_id, text)
        elif state == 'waiting_city':
            self._handle_waiting_city(user_id, chat_id, text)
        elif state == 'confirm_city':
            self._handle_confirm_city(user_id, chat_id, text)
        elif state == 'waiting_relationship':
            self._handle_waiting_relationship(user_id, chat_id, text)

        # Обработка редактирования профиля
        elif state == 'edit_purpose':
            self._handle_edit_purpose(user_id, chat_id, text)
        elif state == 'edit_name':
            self._handle_edit_name(user_id, chat_id, text)
        elif state == 'edit_age':
            self._handle_edit_age(user_id, chat_id, text)
        elif state == 'edit_gender':
            self._handle_edit_gender(user_id, chat_id, text)
        elif state == 'edit_city':
            self._handle_edit_city(user_id, chat_id, text)
        elif state == 'edit_confirm_city':
            self._handle_edit_confirm_city(user_id, chat_id, text)
        elif state == 'edit_relationship':
            self._handle_edit_relationship(user_id, chat_id, text)

        # Обработка главного меню
        elif text == '👤 Мой профиль':
            self.show_profile(message)
        elif text == '🔍 Найти события':
            self.show_filter_menu(message)
        elif text == '📅 Мои события':
            self.show_my_events(message)
        elif text == '🎉 Создать событие':
            self._handle_create_event_start(message)
        elif text == '⭐ Рекомендации':
            self.show_recommendations(message)
        elif text == '🏆 Достижения':
            self.show_achievements(message)
        elif text == 'ℹ️ О боте':
            self.show_about_bot(message)
        elif text == '⬅️ Назад':
            self.bot.send_message(chat_id, "Главное меню:",
                                  reply_markup=get_main_menu())

        # Редактирование профиля из меню
        elif text == '✏️ Изменить цель':
            self.user_state[user_id] = 'edit_purpose'
            self.bot.send_message(
                chat_id,
                "Введите новую цель (например: 'сходить в кино', 'посетить выставку'):"
            )
        elif text == '✏️ Изменить имя':
            self.user_state[user_id] = 'edit_name'
            self.bot.send_message(chat_id, "Введите новое имя:")
        elif text == '✏️ Изменить возраст':
            self.user_state[user_id] = 'edit_age'
            self.bot.send_message(chat_id, "Введите новый возраст:")
        elif text == '✏️ Изменить пол':
            self.user_state[user_id] = 'edit_gender'
            self.bot.send_message(chat_id, "Выберите пол:",
                                  reply_markup=get_gender_keyboard())
        elif text == '✏️ Изменить город':
            self.user_state[user_id] = 'edit_city'
            self.bot.send_message(chat_id, "Введите новый город:")
        elif text == '✏️ Изменить статус':
            self.user_state[user_id] = 'edit_relationship'
            self.bot.send_message(
                chat_id, "Выберите статус:", reply_markup=get_relationship_keyboard())
        elif text == '✏️ Изменить фото':
            self.user_state[user_id] = 'edit_photo'
            self.bot.send_message(chat_id, "Отправьте новое фото:")

        # Команды
        elif text == '/cities':
            self._show_cities_list(chat_id)
        elif text == '/ref':
            self._show_referral_info(message)
        elif text == '/help':
            self.show_about_bot(message)
        else:
            # Проверяем регистрацию перед показом меню
            user = execute_query(
                "SELECT * FROM users WHERE user_id = ?", (user_id,), fetchone=True
            )
            if not user:
                self.bot.send_message(
                    chat_id, "Вы не зарегистрированы. Напишите /start", reply_markup=self._remove_keyboard())
            else:
                self.bot.send_message(
                    chat_id, "Используйте меню для навигации:", reply_markup=get_main_menu())

    def show_profile(self, message):
        """Показать профиль пользователя"""
        user_id = message.from_user.id
        chat_id = message.chat.id

        user = execute_query(
            """SELECT username, name, age, gender, city, relationship_status, 
                      photo, purpose, points, referrals_count, referral_code, is_banned 
               FROM users WHERE user_id=?""",
            (user_id,), fetchone=True
        )

        if not user:
            self.bot.send_message(
                chat_id, "Вы не зарегистрированы. Напишите /start", reply_markup=self._remove_keyboard())
            return

        # Получаем статистику
        events_count = execute_query(
            "SELECT COUNT(*) as count FROM events WHERE user_id=? AND is_hidden = 0",
            (user_id,), fetchone=True
        )['count']

        likes_received = execute_query(
            "SELECT COUNT(*) as count FROM likes WHERE to_user=?",
            (user_id,), fetchone=True
        )['count']

        mutual_likes = execute_query(
            "SELECT COUNT(*) as count FROM likes WHERE to_user=? AND mutual=1",
            (user_id,), fetchone=True
        )['count']

        achievements_count = execute_query(
            "SELECT COUNT(*) as count FROM achievements WHERE user_id=?",
            (user_id,), fetchone=True
        )['count']

        # Генерируем реферальный код если нет
        referral_code = user['referral_code']
        if not referral_code:
            from utils.helpers import generate_referral_code
            referral_code = generate_referral_code()
            execute_query(
                "UPDATE users SET referral_code = ? WHERE user_id = ?",
                (referral_code, user_id), commit=True
            )
            user['referral_code'] = referral_code

        profile_text = f"""👤 *Мой профиль*

📛 *Имя:* {escape_markdown(user['name'])}
👤 *Username:* @{escape_markdown(user['username'] if user['username'] else 'нет')}
🎂 *Возраст:* {escape_markdown(str(user['age']))}
⚧️ *Пол:* {escape_markdown(user['gender'])}
🏙️ *Город:* {escape_markdown(user['city']) if user['city'] else 'Не указан'}
💖 *Статус:* {escape_markdown(user['relationship_status']) if user['relationship_status'] else 'Не указан'}

🎯 *Я здесь для того чтобы:*
*{escape_markdown(user['purpose']) if user['purpose'] else 'куда\\-то сходить'}*

📊 *Статистика:*
🎉 Событий создано: {events_count}
❤️ Лайков получено: {likes_received}
💞 Взаимных симпатий: {mutual_likes}
🏆 Достижений: {achievements_count}
⭐ Рейтинг: {user['points']} очков

👥 *Реферальная программа:*
📊 Приглашено друзей: {user.get('referrals_count', 0)}
🔗 Ваш код: `{user.get('referral_code', 'не задан')}`
💎 Ваша ссылка: `t.me/RELOCK_CLUB_BOT?start={user.get('referral_code', '')}`"""

        if user['is_banned'] == 1:
            ban_info = execute_query(
                "SELECT ban_reason, banned_date FROM users WHERE user_id = ?",
                (user_id,), fetchone=True
            )
            if ban_info:
                profile_text += f"\n\n⛔ *Ваш аккаунт заблокирован!*\n"
                profile_text += f"📝 Причина: {ban_info['ban_reason'] or 'Нарушение правил'}\n"
                profile_text += f"📅 Дата блокировки: {ban_info['banned_date'][:10] if ban_info['banned_date'] else 'неизвестно'}"

        keyboard = get_user_profile_keyboard(
            user_id, user_id, can_report=False)

        if user['photo']:
            self.bot.send_photo(
                chat_id, user['photo'], caption=profile_text,
                parse_mode='Markdown', reply_markup=keyboard
            )
        else:
            self.bot.send_message(
                chat_id, profile_text + "\n\n📸 *Фото не загружено*",
                parse_mode='Markdown', reply_markup=keyboard
            )

    def show_filter_menu(self, message):
        """Показать меню фильтров"""
        user_id = message.from_user.id
        chat_id = message.chat.id

        user = execute_query(
            "SELECT * FROM users WHERE user_id=?", (user_id,), fetchone=True
        )

        if not user:
            self.bot.send_message(
                chat_id, "Вы не зарегистрированы. Напишите /start", reply_markup=self._remove_keyboard())
            return

        keyboard = get_filter_keyboard()
        self.bot.send_message(
            chat_id, "🔍 *Выберите тип поиска:*", parse_mode='Markdown', reply_markup=keyboard
        )

    def show_my_events(self, message, page=0, page_size=5):
        """Показать события пользователя"""
        user_id = message.from_user.id
        chat_id = message.chat.id

        user = execute_query(
            "SELECT * FROM users WHERE user_id=?", (user_id,), fetchone=True
        )

        if not user:
            self.bot.send_message(
                chat_id, "Вы не зарегистрированы. Напишите /start", reply_markup=self._remove_keyboard())
            return

        total_count = execute_query(
            "SELECT COUNT(*) as count FROM events WHERE user_id=? AND is_hidden = 0",
            (user_id,), fetchone=True
        )['count']

        if total_count == 0:
            self.bot.send_message(
                chat_id, "У вас пока нет событий. Создайте первое! 🎉")
            return

        events = execute_query(
            """SELECT id, title, description, event_date, target_gender, city, category 
               FROM events WHERE user_id=? AND is_hidden = 0
               ORDER BY event_date 
               LIMIT ? OFFSET ?""",
            (user_id, page_size, page * page_size), fetchall=True
        )

        if not events:
            self.bot.send_message(chat_id, "Нет событий на этой странице.")
            return

        header = f"📅 *Ваши события* ({total_count} всего, стр. {page+1}/{((total_count-1)//page_size)+1}):\n"
        self.bot.send_message(chat_id, header, parse_mode='Markdown')

        for event in events:
            event_text = f"""*{escape_markdown(event['title'])}*
🏷️ Категория: {event.get('category', '🎯 Разное')}

📝 {escape_markdown(event['description'][:100])}{'...' if len(event['description']) > 100 else ''}
📅 {escape_markdown(event['event_date'])}
🏙️ Город: {escape_markdown(event['city'])}
👥 Для: {escape_markdown(event['target_gender'])}"""

            likes_count = execute_query(
                "SELECT COUNT(*) as count FROM likes WHERE event_id=?",
                (event['id'],), fetchone=True
            )

            if likes_count and likes_count['count'] > 0:
                event_text += f"\n\n❤️ *Лайков:* {likes_count['count']}\n"

            keyboard = get_event_action_keyboard(event['id'])
            self.bot.send_message(
                chat_id, event_text, parse_mode='Markdown', reply_markup=keyboard
            )

        if total_count > page_size:
            keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
            buttons = []

            if page > 0:
                buttons.append(telebot.types.InlineKeyboardButton(
                    "◀️ Предыдущая", callback_data=f"my_events_{page-1}"))

            if (page + 1) * page_size < total_count:
                buttons.append(telebot.types.InlineKeyboardButton(
                    "Следующая ▶️", callback_data=f"my_events_{page+1}"))

            if buttons:
                keyboard.add(*buttons)

            self.bot.send_message(
                chat_id, "Навигация по страницам:", reply_markup=keyboard)

    def show_recommendations(self, message):
        """Показать рекомендации"""
        user_id = message.from_user.id
        chat_id = message.chat.id

        user = execute_query(
            "SELECT * FROM users WHERE user_id=?", (user_id,), fetchone=True
        )

        if not user:
            self.bot.send_message(
                chat_id, "Вы не зарегистрированы. Напишите /start", reply_markup=self._remove_keyboard())
            return

        recommendations = RecommendationService.get_recommendations(user_id)

        if not recommendations:
            self.bot.send_message(
                chat_id,
                "🎯 *Пока нет рекомендаций*\n\n"
                "Создайте первое событие или поставьте лайки, чтобы мы узнали ваши предпочтения!",
                parse_mode='Markdown'
            )
            return

        self.bot.send_message(
            chat_id, f"⭐ *Рекомендации для вас* ({len(recommendations)}):", parse_mode='Markdown'
        )

        for event in recommendations[:5]:
            event_text = f"""🎉 *{escape_markdown(event['title'])}*
🏷️ Категория: {event.get('category', '🎯 Разное')}

📝 {escape_markdown(event['description'][:100])}{'...' if len(event['description']) > 100 else ''}
📅 {escape_markdown(event['event_date'])}
👤 Организатор: {escape_markdown(event['name'])} ({event['age']}, {event['gender']})
🏙️ Город: {escape_markdown(event['city'])}
👥 Для: {escape_markdown(event['target_gender'])}"""

            keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                telebot.types.InlineKeyboardButton(
                    "❤️ Лайк", callback_data=f"like_{event['id']}"),
                telebot.types.InlineKeyboardButton(
                    "🚨 Пожаловаться на организатора", callback_data=f"report_organizer_{event['id']}")
            )

            if event.get('photo'):
                self.bot.send_photo(
                    chat_id, event['photo'], caption=event_text,
                    parse_mode='Markdown', reply_markup=keyboard
                )
            else:
                self.bot.send_message(
                    chat_id, event_text, parse_mode='Markdown', reply_markup=keyboard
                )

    def show_achievements(self, message):
        """Показать достижения пользователя"""
        user_id = message.from_user.id
        chat_id = message.chat.id

        user = execute_query(
            "SELECT * FROM users WHERE user_id=?", (user_id,), fetchone=True
        )

        if not user:
            self.bot.send_message(
                chat_id, "Вы не зарегистрированы. Напишите /start", reply_markup=self._remove_keyboard())
            return

        achievements = AchievementService.get_user_achievements(user_id)
        points = user['points'] if user else 0

        if not achievements:
            self.bot.send_message(
                chat_id,
                f"""🏆 *Достижения*

🎯 У вас пока нет достижений.
📊 Очков рейтинга: *{points}*

*Как получить достижения:*
🎉 Создайте первое событие
❤️ Получайте лайки на свои события
💞 Находите взаимные симпатии
🎯 Будьте активны каждый день""",
                parse_mode='Markdown'
            )
            return

        unlocked_text = f"🏆 *Ваши достижения* ({len(achievements)})\n\n"
        for ach in achievements:
            unlocked_text += f"{ach['emoji']} *{ach['name']}*\n"
            unlocked_text += f"📝 {ach['description']}\n"
            unlocked_text += f"🎯 +{ach['points']} очков\n"
            unlocked_text += f"📅 {ach['unlocked_date'][:10]}\n\n"

        locked_text = "\n🔒 *Ещё не разблокировано:*\n"
        locked_count = 0
        for ach_id, ach_data in config.ACHIEVEMENTS.items():
            if not any(a['id'] == ach_id for a in achievements):
                locked_text += f"🔒 {ach_data['emoji']} {ach_data['name']}\n"
                locked_count += 1

        final_text = f"""{unlocked_text}
📊 *Общий рейтинг:* {points} очков
{locked_text if locked_count > 0 else ''}"""

        self.bot.send_message(chat_id, final_text, parse_mode='Markdown')

    def _handle_waiting_name(self, user_id, chat_id, text):
        """Обработка ввода имени при регистрации"""
        if user_id not in self.user_data:
            self.user_data[user_id] = {}
        self.user_data[user_id]['name'] = text
        self.user_state[user_id] = 'waiting_age'
        self.bot.send_message(
            chat_id, f"Приятно познакомиться, {text}! Сколько тебе лет?")

    def _handle_waiting_age(self, user_id, chat_id, text):
        """Обработка ввода возраста"""
        if text.isdigit():
            age = int(text)
            if 18 <= age <= 100:
                self.user_data[user_id]['age'] = age
                self.user_state[user_id] = 'waiting_gender'
                self.bot.send_message(
                    chat_id, "Выбери пол:", reply_markup=get_gender_keyboard())
            else:
                self.bot.send_message(
                    chat_id, "Возраст должен быть от 18 до 100 лет.")
        else:
            self.bot.send_message(chat_id, "Введи возраст цифрами:")

    def _handle_waiting_gender(self, user_id, chat_id, text):
        """Обработка выбора пола"""
        if text in ['Мужской', 'Женский', 'Другой']:
            self.user_data[user_id]['gender'] = text
            self.user_state[user_id] = 'waiting_city'
            cities_sample = "\n".join(config.CITIES[:10])
            self.bot.send_message(
                chat_id,
                f"Введите ваш город (например: Москва, Санкт-Петербург...)\n\n"
                f"Примеры городов:\n{cities_sample}\n\n"
                f"...и ещё {len(config.CITIES)-10} городов"
            )
        else:
            self.bot.send_message(
                chat_id, "Выбери вариант из клавиатуры:", reply_markup=get_gender_keyboard()
            )

    def _handle_waiting_city(self, user_id, chat_id, text):
        """Обработка ввода города"""
        city = text.strip()

        if city in config.CITIES:
            self.user_data[user_id]['city'] = city
            self.user_state[user_id] = 'waiting_relationship'
            self.bot.send_message(
                chat_id, "Выбери статус отношений:", reply_markup=get_relationship_keyboard()
            )
        else:
            similar_city = find_similar_city(city, config.CITIES)

            if similar_city:
                self.user_data[user_id]['suggested_city'] = similar_city
                self.user_data[user_id]['input_city'] = city
                self.user_state[user_id] = 'confirm_city'

                self.bot.send_message(
                    chat_id,
                    f"Возможно, вы имели в виду: *{similar_city}*?\n\n"
                    f"(Если нет, введите правильное название города)",
                    parse_mode='Markdown',
                    reply_markup=get_yes_no_keyboard()
                )
            else:
                # Оставляем состояние waiting_city, чтобы пользователь мог ввести город снова
                self.bot.send_message(
                    chat_id,
                    "❌ Такого города нет в нашем списке.\n\n"
                    "Пожалуйста, введите другой город из доступных. "
                    "Проверьте правильность написания и попробуйте ещё раз:"
                )

    def _handle_confirm_city(self, user_id, chat_id, text):
        """Обработка подтверждения города"""
        if text == '✅ Да':
            self.user_data[user_id]['city'] = self.user_data[user_id]['suggested_city']
            self.user_state[user_id] = 'waiting_relationship'
            self.bot.send_message(
                chat_id, "Выбери статус отношений:", reply_markup=get_relationship_keyboard()
            )
        elif text == '❌ Нет':
            self.user_state[user_id] = 'waiting_city'
            self.bot.send_message(
                chat_id, "Введите название города из списка:")
        else:
            if text in config.CITIES:
                self.user_data[user_id]['city'] = text
                self.user_state[user_id] = 'waiting_relationship'
                self.bot.send_message(
                    chat_id, "Выбери статус отношений:", reply_markup=get_relationship_keyboard()
                )
            else:
                similar_city = find_similar_city(text, config.CITIES)
                if similar_city:
                    self.user_data[user_id]['suggested_city'] = similar_city
                    self.user_data[user_id]['input_city'] = text
                    self.bot.send_message(
                        chat_id,
                        f"Возможно, вы имели в виду: *{similar_city}*?\n\n"
                        f"(Если нет, введите правильное название города)",
                        parse_mode='Markdown',
                        reply_markup=get_yes_no_keyboard()
                    )
                else:
                    self.bot.send_message(
                        chat_id,
                        "Город не найден в списке. Пожалуйста, введите город из списка.\n"
                        "Можно посмотреть все города: /cities"
                    )

    def _handle_waiting_relationship(self, user_id, chat_id, text):
        """Обработка выбора статуса отношений"""
        if text in ['Не в отношениях', 'В отношениях', 'В браке', 'Всё сложно']:
            self.user_data[user_id]['relationship'] = text
            self.user_state[user_id] = 'waiting_photo'
            self.bot.send_message(
                chat_id, "Отправь своё фото (это важно для анкеты!):"
            )
        else:
            self.bot.send_message(
                chat_id, "Выбери вариант из клавиатуры:", reply_markup=get_relationship_keyboard()
            )

    def _handle_create_event_start(self, message):
        """Обработка начала создания события"""
        user_id = message.from_user.id
        chat_id = message.chat.id

        user = execute_query(
            "SELECT * FROM users WHERE user_id=?", (user_id,), fetchone=True
        )

        if not user:
            self.bot.send_message(
                chat_id, "Вы не зарегистрированы. Напишите /start", reply_markup=self._remove_keyboard())
            return

        # Очищаем предыдущие данные
        if user_id in self.user_data:
            del self.user_data[user_id]

        self.user_state[user_id] = 'waiting_event_title'
        self.user_data[user_id] = {}  # Важно: создаем пустой словарь
        self.bot.send_message(chat_id, "Введите название события:")

    def _handle_edit_purpose(self, user_id, chat_id, text):
        """Обработка изменения цели"""
        if len(text) > 100:
            self.bot.send_message(
                chat_id, "Цель слишком длинная (максимум 100 символов). Введите короче:"
            )
            return

        execute_query(
            "UPDATE users SET purpose=? WHERE user_id=?", (text, user_id), commit=True
        )
        del self.user_state[user_id]
        self.bot.send_message(chat_id, "✅ Цель обновлена!",
                              reply_markup=get_profile_menu())

    def _handle_edit_name(self, user_id, chat_id, text):
        """Обработка изменения имени"""
        execute_query(
            "UPDATE users SET name=? WHERE user_id=?", (text, user_id), commit=True
        )
        del self.user_state[user_id]
        self.bot.send_message(chat_id, "✅ Имя обновлено!",
                              reply_markup=get_profile_menu())

    def _handle_edit_age(self, user_id, chat_id, text):
        """Обработка изменения возраста"""
        if text.isdigit() and 18 <= int(text) <= 100:
            execute_query(
                "UPDATE users SET age=? WHERE user_id=?", (int(text), user_id), commit=True
            )
            del self.user_state[user_id]
            self.bot.send_message(
                chat_id, "✅ Возраст обновлён!", reply_markup=get_profile_menu())
        else:
            self.bot.send_message(chat_id, "Введите возраст от 18 до 100:")

    def _handle_edit_gender(self, user_id, chat_id, text):
        """Обработка изменения пола"""
        if text in ['Мужской', 'Женский', 'Другой']:
            execute_query(
                "UPDATE users SET gender=? WHERE user_id=?", (text, user_id), commit=True
            )
            del self.user_state[user_id]
            self.bot.send_message(chat_id, "✅ Пол обновлён!",
                                  reply_markup=get_profile_menu())

    def _handle_edit_city(self, user_id, chat_id, text):
        """Обработка изменения города"""
        city = text.strip()
        if city in config.CITIES:
            execute_query(
                "UPDATE users SET city=? WHERE user_id=?", (city, user_id), commit=True
            )
            del self.user_state[user_id]
            self.bot.send_message(
                chat_id, "✅ Город обновлён!", reply_markup=get_profile_menu())
        else:
            similar_city = find_similar_city(city, config.CITIES)
            if similar_city:
                self.user_data[user_id] = {
                    'suggested_city': similar_city, 'input_city': city}
                self.user_state[user_id] = 'edit_confirm_city'
                self.bot.send_message(
                    chat_id,
                    f"Возможно, вы имели в виду: *{similar_city}*?",
                    parse_mode='Markdown',
                    reply_markup=get_yes_no_keyboard()
                )
            else:
                # Оставляем состояние edit_city, чтобы пользователь мог ввести город снова
                self.bot.send_message(
                    chat_id,
                    "❌ Такого города нет в нашем списке.\n\n"
                    "Пожалуйста, введите другой город из доступных. "
                    "Проверьте правильность написания и попробуйте ещё раз:"
                )

    def _handle_edit_confirm_city(self, user_id, chat_id, text):
        """Обработка подтверждения города при редактировании"""
        if text == '✅ Да':
            execute_query(
                "UPDATE users SET city=? WHERE user_id=?",
                (self.user_data[user_id]
                 ['suggested_city'], user_id), commit=True
            )
            del self.user_state[user_id]
            del self.user_data[user_id]
            self.bot.send_message(
                chat_id, "✅ Город обновлён!", reply_markup=get_profile_menu())
        elif text == '❌ Нет':
            self.user_state[user_id] = 'edit_city'
            self.bot.send_message(
                chat_id, "Введите название города из списка:")

    def _handle_edit_relationship(self, user_id, chat_id, text):
        """Обработка изменения статуса отношений"""
        if text in ['Не в отношениях', 'В отношениях', 'В браке', 'Всё сложно']:
            execute_query(
                "UPDATE users SET relationship_status=? WHERE user_id=?", (text, user_id), commit=True
            )
            del self.user_state[user_id]
            self.bot.send_message(
                chat_id, "✅ Статус обновлён!", reply_markup=get_profile_menu())

    def show_about_bot(self, message):
        """Показать подробную информацию о боте"""
        user_id = message.from_user.id
        chat_id = message.chat.id

        about_text = (
            "🤖 *О боте для знакомств*\n\n"
            "🎯 *Главная идея:*\n"
            "Мы создали бот, где знакомства происходят *естественно* — через совместные мероприятия! "
            "Вместо бесконечных свайпов и скучной переписки, вы сразу находите людей с общими интересами "
            "и планируете реальные встречи.\n\n"
            "✨ *Почему мы лучше других:*\n\n"
            "🎉 *События вместо свайпов*\n"
            "Знакомьтесь через реальные активности: кино, кафе, прогулки, выставки. "
            "У вас уже есть общая тема для разговора!\n\n"
            "🎯 *Общие интересы*\n"
            "Находите людей, которые любят то же, что и вы. Бот анализирует ваши предпочтения "
            "и подбирает идеальные события.\n\n"
            "🏆 *Система достижений*\n"
            "Получайте очки за активность: создание событий, лайки, взаимные симпатии. "
            "Соревнуйтесь с другими пользователями!\n\n"
            "⭐ *Умные рекомендации*\n"
            "Бот изучает ваши предпочтения и предлагает события, которые точно вам понравятся. "
            "Чем больше вы используете бот, тем точнее рекомендации!\n\n"
            "👥 *Реферальная программа*\n"
            "Приглашайте друзей и получайте бонусные очки. Ваши друзья тоже получат подарок!\n\n"
            "🚀 *Основные функции:*\n\n"
            "📅 *Создание событий*\n"
            "Создавайте свои мероприятия: кино, кафе, прогулки, выставки, спорт и многое другое. "
            "Указывайте дату, место, категорию и для кого событие.\n\n"
            "🔍 *Поиск событий*\n"
            "• По интересам — события в ваших любимых категориях\n"
            "• Популярные — самые лайкаемые события\n"
            "• Ближайшие — события в вашем городе\n"
            "• Новые — свежие события\n"
            "• Сегодня/Завтра — события на ближайшие дни\n"
            "• Персональные — специально для вас\n\n"
            "❤️ *Система лайков*\n"
            "Лайкайте понравившиеся события. Если организатор тоже лайкнет вас — это взаимная симпатия! "
            "После взаимного лайка вы можете обменяться контактами.\n\n"
            "🏆 *Достижения и очки*\n"
            "• 🎉 Первый шаг — создал первое событие\n"
            "• ❤️ Привлекательный — получил 5 лайков\n"
            "• 💞 Взаимность — первая взаимная симпатия\n"
            "• 🔥 Непрерывность — активен 7 дней подряд\n"
            "• 🎯 Организатор — создал 10 событий\n"
            "• 👥 Общительный — получил 50 лайков\n"
            "• 🧭 Исследователь — посетил 5 разных категорий\n"
            "• 🐦 Ранняя пташка — создал событие на утро\n\n"
            "💡 *Как начать:*\n"
            "1. Заполните профиль (имя, возраст, город, фото)\n"
            "2. Создайте своё первое событие\n"
            "3. Или начните искать события других пользователей\n"
            "4. Лайкайте понравившиеся события\n"
            "5. Знакомьтесь и встречайтесь!\n\n"
            "📱 *Команды:*\n"
            "• /start — начать работу с ботом\n"
            "• /help — эта справка\n"
            "• /ref — информация о реферальной программе\n\n"
            "❓ *Вопросы?*\n"
            "Используйте меню для навигации. Все функции доступны через кнопки!"
        )

        self.bot.send_message(
            chat_id, about_text, parse_mode='Markdown', reply_markup=get_main_menu()
        )

    def _show_cities_list(self, chat_id):
        """Показать список городов"""
        cities_text = "Список доступных городов:\n\n" + \
            "\n".join(config.CITIES)
        if len(cities_text) > 4096:
            for i in range(0, len(cities_text), 4000):
                self.bot.send_message(chat_id, cities_text[i:i+4000])
        else:
            self.bot.send_message(chat_id, cities_text)

    def _show_referral_info(self, message):
        """Показать информацию о реферальной программе"""
        user_id = message.from_user.id
        chat_id = message.chat.id

        user = execute_query(
            "SELECT * FROM users WHERE user_id=?", (user_id,), fetchone=True
        )

        if not user:
            self.bot.send_message(
                chat_id, "Вы не зарегистрированы. Напишите /start", reply_markup=self._remove_keyboard())
            return

        user = execute_query(
            "SELECT referral_code, referrals_count, name FROM users WHERE user_id=?",
            (user_id,), fetchone=True
        )

        if user:
            if not user['referral_code']:
                from utils.helpers import generate_referral_code
                referral_code = generate_referral_code()
                execute_query(
                    "UPDATE users SET referral_code = ? WHERE user_id = ?",
                    (referral_code, user_id), commit=True
                )
                user['referral_code'] = referral_code

            self.bot.send_message(
                chat_id,
                f"👥 *Реферальная программа*\n\n"
                f"👤 *Ваше имя:* {escape_markdown(user['name'])}\n"
                f"🔗 *Ваш реферальный код:* `{user['referral_code']}`\n\n"
                f"📊 *Ваша статистика:*\n"
                f"👥 Приглашено друзей: {user['referrals_count']}\n"
                f"💰 Всего заработано: {user['referrals_count'] * 100} очков\n\n"
                f"📢 *Как приглашать:*\n"
                f"1. Отправьте другу ссылку:\n"
                f"`t.me/RELOCK_CLUB_BOT?start={user['referral_code']}`\n\n"
                f"2. Друг регистрируется по вашей ссылке\n"
                f"3. Вы получаете *100 очков*\n"
                f"4. Друг получает *50 очков*\n\n"
                f"🎁 *Ваши бонусы:*\n"
                f"• 100 очков за каждого друга\n"
                f"• Друг получает 50 очков\n\n"
                f"💡 *Совет:* Отправьте ссылку друзьям в соцсетях или мессенджерах!",
                parse_mode='Markdown'
            )
        else:
            self.bot.send_message(
                chat_id, "❌ Ошибка: не удалось получить информацию о реферальной программе."
            )

    def _show_ban_message(self, user_id, chat_id):
        """Показать сообщение о блокировке"""
        user = execute_query(
            "SELECT ban_reason, banned_date FROM users WHERE user_id = ?",
            (user_id,), fetchone=True
        )

        if user:
            reason = user['ban_reason'] or "Нарушение правил"
            date = user['banned_date'][:10] if user['banned_date'] else "неизвестно"

            markup = get_ban_notification_keyboard(user_id)
            self.bot.send_message(
                chat_id,
                f"⛔ *Ваш аккаунт заблокирован!*\n\n"
                f"📝 *Причина:* {reason}\n"
                f"📅 *Дата блокировки:* {date}\n\n"
                f"Если вы считаете, что это ошибка, вы можете оспорить блокировку:",
                parse_mode='Markdown',
                reply_markup=markup
            )

    def handle_photo(self, message):
        """Обработка фотографий"""
        user_id = message.from_user.id
        chat_id = message.chat.id
        state = self.user_state.get(user_id)

        if state in ['waiting_photo', 'edit_photo']:
            photo_id = message.photo[-1].file_id

            if state == 'waiting_photo':
                username = message.from_user.username or ""
                self._handle_registration_photo(user_id, chat_id, photo_id, username)
            elif state == 'edit_photo':
                self._handle_edit_photo(user_id, chat_id, photo_id)

    def _handle_registration_photo(self, user_id, chat_id, photo_id, username=""):
        """Обработка фото при регистрации"""
        data = self.user_data.get(user_id, {})

        from utils.helpers import generate_referral_code
        referral_code = generate_referral_code()
        referred_by = data.get('referred_by')

        execute_query(
            '''INSERT INTO users (user_id, username, name, age, gender, city, relationship_status, photo, reg_date, last_active, referral_code, referred_by) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (user_id, username, data.get('name', ''), data.get('age', 0), data.get('gender', ''),
             data.get('city', ''), data.get(
                 'relationship', 'Не указано'), photo_id,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             datetime.now().strftime("%Y-%m-%d"),
             referral_code, referred_by),
            commit=True
        )

        # Начисляем очки за реферала
        if referred_by:
            AchievementService.update_user_points(
                user_id, 50, "за регистрацию по приглашению")
            AchievementService.update_user_points(
                referred_by, 100, f"за приглашение пользователя {data.get('name', 'нового пользователя')}"
            )

            execute_query(
                "UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?",
                (referred_by,), commit=True
            )

            referrer_stats = execute_query(
                "SELECT name, referrals_count FROM users WHERE user_id = ?",
                (referred_by,), fetchone=True
            )

            try:
                self.bot.send_message(
                    referred_by,
                    f"🎉 *Ваш друг {data.get('name', 'новый пользователь')} зарегистрировался по вашей ссылке!*\n\n"
                    f"💰 Вы получили +100 очков\n"
                    f"👥 Всего приглашено: {referrer_stats['referrals_count'] if referrer_stats else 0}\n\n"
                    f"💎 Теперь у вас {referrer_stats['referrals_count'] if referrer_stats else 0} приглашенных друзей!",
                    parse_mode='Markdown'
                )
            except Exception as e:
                print(f"❌ Ошибка отправки уведомления рефереру: {e}")

        del self.user_state[user_id]
        if user_id in self.user_data:
            del self.user_data[user_id]

        self.bot.send_message(
            chat_id, "✅ Регистрация завершена!", reply_markup=get_main_menu())

        # Предлагаем создать событие через 2 минуты
        import threading
        threading.Thread(target=self._suggest_event_delayed,
                         args=(user_id,)).start()

    def _handle_edit_photo(self, user_id, chat_id, photo_id):
        """Обработка изменения фото"""
        execute_query(
            "UPDATE users SET photo=? WHERE user_id=?", (photo_id, user_id), commit=True
        )
        del self.user_state[user_id]
        self.bot.send_message(chat_id, "✅ Фото обновлено!",
                              reply_markup=get_profile_menu())

    def _suggest_event_delayed(self, user_id):
        """Предложить создать событие через 2 минуты"""
        import time

        time.sleep(120)

        # Проверяем бан
        user = execute_query(
            "SELECT is_banned FROM users WHERE user_id = ?", (user_id,), fetchone=True
        )

        if user and user['is_banned'] == 1:
            return

        # Проверяем, есть ли уже события
        events_count = execute_query(
            "SELECT COUNT(*) as count FROM events WHERE user_id=? AND is_hidden = 0",
            (user_id,), fetchone=True
        )

        if events_count and events_count['count'] == 0:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(
                "🎉 Создать событие", callback_data="create_event"))

            try:
                self.bot.send_message(
                    user_id,
                    "💡 *Хочешь создать своё первое событие для знакомств?*\n\n"
                    "Это поможет другим пользователям найти тебя быстрее! ✨",
                    parse_mode='Markdown',
                    reply_markup=markup
                )
            except:
                pass
