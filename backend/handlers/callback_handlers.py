# handlers/callback_handlers.py
import json
from datetime import datetime
import telebot

from config import config
from database import execute_query
from keyboards.user_keyboards import *
from keyboards.admin_keyboards import *
from services.achievements import AchievementService
from services.notifications import NotificationService
from services.reports import ReportService
from services.broadcast import BroadcastService
from services.admin import AdminService
from utils.helpers import escape_markdown, find_similar_city


class CallbackHandler:
    def __init__(self, bot, admin_handlers=None, user_handlers=None, shared_user_state=None, shared_user_data=None):
        self.bot = bot
        # Если передан экземпляр `AdminHandlers`, используем его состояния/данные
        # для админ-панели (чтобы они не терялись между сообщениями).
        self.admin_handlers = admin_handlers
        self.user_handlers = user_handlers
        self.user_state = shared_user_state if shared_user_state is not None else {}
        self.user_data = shared_user_data if shared_user_data is not None else {}
        self.admin_broadcast_data = {}

    def _admin_state(self):
        return self.admin_handlers.user_state if self.admin_handlers else self.user_state

    def _admin_broadcast_data(self):
        return self.admin_handlers.admin_broadcast_data if self.admin_handlers else self.admin_broadcast_data

    def handle(self, call):
        """Главный обработчик callback запросов"""
        user_id = call.from_user.id
        data = call.data

        print(f"DEBUG: callback_data = {data}, user_id = {user_id}")

        # Если пользователь заблокирован — при нажатии любой кнопки показываем сообщение о блокировке
        # (кроме кнопки апелляции и админов).
        if user_id not in config.ADMINS and not data.startswith("appeal_ban_"):
            user = execute_query(
                "SELECT is_banned FROM users WHERE user_id = ?",
                (user_id,), fetchone=True
            )
            if user and user.get('is_banned') == 1:
                try:
                    from keyboards.user_keyboards import get_ban_notification_keyboard
                    self.bot.send_message(
                        call.message.chat.id,
                        "⛔ *Ваш аккаунт заблокирован!*\n\n"
                        "Вы можете оспорить блокировку через кнопку ниже:",
                        parse_mode='Markdown',
                        reply_markup=get_ban_notification_keyboard(user_id)
                    )
                except:
                    pass
                self.bot.answer_callback_query(call.id, "⛔ Аккаунт заблокирован")
                return

        # Обработка лайков (ИСПРАВЛЕННАЯ ВЕРСИЯ)
        if data.startswith("like_"):
            self._handle_like(call)

        # Админ панель
        elif data.startswith("admin_") or data.startswith("broadcast_"):
            self._handle_admin_callback(call)

        # Фильтры поиска
        elif data.startswith("filter_"):
            self._handle_filter(call)

        # Жалобы
        elif data.startswith("report_"):
            self._handle_report(call)

        # Взаимные симпатии
        elif data.startswith("mutual_"):
            self._handle_mutual(call)

        # Пропуск
        elif data.startswith("skip_"):
            self._handle_skip(call)

        # Навигация
        elif data.startswith("next_"):
            self._handle_next(call)

        # Игнорирование
        elif data.startswith("ignore_"):
            self._handle_ignore(call)

        # Оспаривание блокировки
        elif data.startswith("appeal_ban_"):
            self._handle_appeal_ban(call)

        # Другие callback
        else:
            self._handle_other_callbacks(call)

    def _handle_like(self, call):
        """Обработка лайков (ИСПРАВЛЕННАЯ)"""
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        data = call.data

        try:
            # Извлекаем event_id из callback данных
            parts = data.split("_")
            if len(parts) < 2:
                self.bot.answer_callback_query(call.id, "❌ Ошибка обработки")
                return

            try:
                event_id = int(parts[1])
            except (ValueError, IndexError):
                self.bot.answer_callback_query(call.id, "❌ Неверный ID события")
                return

            # Получаем информацию о событии (включая id)
            event = execute_query(
                "SELECT id, user_id, title, description, event_date, category FROM events WHERE id=? AND is_hidden = FALSE",
                (event_id,), fetchone=True
            )

            if not event:
                self.bot.answer_callback_query(call.id, "❌ Событие не найдено")
                return

            creator_id = event['user_id']

            # Проверяем, не лайкает ли пользователь свое событие
            if creator_id == user_id:
                self.bot.answer_callback_query(
                    call.id, "❌ Нельзя лайкать своё событие!")
                return

            # Проверяем, не лайкал ли уже
            existing_like = execute_query(
                "SELECT id FROM likes WHERE from_user=? AND event_id=?",
                (user_id, event_id), fetchone=True
            )

            if existing_like:
                self.bot.answer_callback_query(
                    call.id, "❤️ Вы уже лайкали это событие")
                return

            # Сохраняем лайк
            like_id = execute_query(
                '''INSERT INTO likes (from_user, to_user, event_id, created) 
                   VALUES (?, ?, ?, ?) RETURNING id''',
                (user_id, creator_id, event_id,
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                commit=True
            )

            # Обновляем предпочтения пользователя
            if event.get('category'):
                prefs = execute_query(
                    "SELECT liked_categories FROM user_preferences WHERE user_id = ?",
                    (user_id,), fetchone=True
                )

                if not prefs:
                    execute_query(
                        "INSERT INTO user_preferences (user_id, liked_categories) VALUES (?, ?)",
                        (user_id, json.dumps([event['category']])), commit=True
                    )
                else:
                    try:
                        liked = json.loads(prefs['liked_categories'])
                    except:
                        liked = []

                    if event['category'] not in liked:
                        liked.append(event['category'])
                        execute_query(
                            "UPDATE user_preferences SET liked_categories = ? WHERE user_id = ?",
                            (json.dumps(liked), user_id), commit=True
                        )

            # Начисляем очки
            AchievementService.update_user_points(
                user_id, 5, "за лайк события")

            # Проверяем достижения
            likes_given = execute_query(
                "SELECT COUNT(*) as count FROM likes WHERE from_user=?",
                (user_id,), fetchone=True
            )['count']

            if likes_given == 5:
                AchievementService.unlock_achievement(user_id, "five_likes")

            # Отправляем уведомление создателю события
            NotificationService.send_like_notification(
                creator_id, user_id, event, like_id, self.bot)

            self.bot.answer_callback_query(
                call.id, "❤️ Вы лайкали это событие!")

            # Удаляем сообщение с событием
            try:
                self.bot.delete_message(chat_id, call.message.message_id)
            except:
                pass

            # Показываем следующее событие
            if user_id in self.user_data:
                user_data_info = self.user_data[user_id]
                filter_type = user_data_info.get('filter_type')
                current_index = user_data_info.get('current_index', 0)
                self.show_next_event(call.message, user_id,
                                     current_index + 1, filter_type)

        except Exception as e:
            print(f"Ошибка при обработке лайка: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка обработки")

    def _handle_mutual(self, call):
        """Обработка взаимных симпатий"""
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        data = call.data

        try:
            like_id = data.split("_")[1]

            like = execute_query(
                "SELECT from_user, to_user, event_id FROM likes WHERE id = ?",
                (like_id,), fetchone=True
            )

            if not like:
                self.bot.answer_callback_query(call.id, "❌ Лайк не найден")
                return

            if like['to_user'] != user_id:
                self.bot.answer_callback_query(call.id, "❌ Это не ваш лайк")
                return

            # Получаем информацию о событии
            event = execute_query(
                "SELECT title, description, event_date FROM events WHERE id = ?",
                (like['event_id'],), fetchone=True
            )

            if not event:
                self.bot.answer_callback_query(call.id, "❌ Событие не найдено")
                return

            # Получаем информацию о пользователях
            liker_user = execute_query(
                "SELECT name, username FROM users WHERE user_id = ?",
                (like['from_user'],), fetchone=True
            )

            creator_user = execute_query(
                "SELECT name, username FROM users WHERE user_id = ?",
                (like['to_user'],), fetchone=True
            )

            # Обновляем лайк как взаимный
            execute_query(
                "UPDATE likes SET mutual = TRUE WHERE id = ?",
                (like_id,), commit=True
            )

            # Проверяем, есть ли обратный лайк
            mutual_check = execute_query(
                "SELECT id FROM likes WHERE from_user = ? AND to_user = ? AND mutual = TRUE",
                (user_id, like['from_user']), fetchone=True
            )

            if not mutual_check:
                # Создаем обратный лайк
                execute_query(
                    '''INSERT INTO likes (from_user, to_user, event_id, mutual, created) 
                       VALUES (?, ?, ?, 1, ?)''',
                    (user_id, like['from_user'], like['event_id'],
                     datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    commit=True
                )

            # Начисляем очки обоим пользователям
            AchievementService.update_user_points(
                user_id, 20, "за взаимную симпатию")
            AchievementService.update_user_points(
                like['from_user'], 20, "за взаимную симпатию")

            # Проверяем достижения
            AchievementService.check_achievements(user_id)
            AchievementService.check_achievements(like['from_user'])

            # Отправляем уведомление о матчинге
            NotificationService.send_match_notification(
                like['from_user'], user_id, like['event_id'], self.bot)

            # Без дублирующих сообщений — только "Матч! ..."
            self.bot.answer_callback_query(call.id)

            # Удаляем сообщение с уведомлением
            try:
                self.bot.delete_message(chat_id, call.message.message_id)
            except:
                pass

        except Exception as e:
            print(f"Ошибка при обработке взаимной симпатии: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка обработки")

    def _handle_admin_callback(self, call):
        """Обработка админ callback"""
        user_id = call.from_user.id

        if user_id not in config.ADMINS:
            self.bot.answer_callback_query(call.id, "⛔ Нет прав доступа")
            return

        # Обработка различных админ действий
        data = call.data

        if data == "admin_back":
            self._show_admin_main_menu(call)
        elif data == "admin_stats":
            self._show_admin_stats(call)
        elif data == "admin_broadcast":
            self._show_broadcast_menu(call)
        elif data == "admin_users":
            self._show_users_menu(call)
        elif data == "admin_reports":
            self._show_reports_menu(call)
        elif data.startswith("admin_ban_"):
            self._handle_admin_ban(call)
        elif data.startswith("admin_unban_"):
            self._handle_admin_unban(call)
        elif data.startswith("admin_view_user_"):
            self._handle_admin_view_user(call)
        elif data.startswith("admin_dismiss_report_"):
            self._handle_admin_dismiss_report(call)
        elif data.startswith("broadcast_type_"):
            self._handle_broadcast_type(call)
        elif data.startswith("broadcast_filter_"):
            self._handle_broadcast_filter(call)
        elif data.startswith("broadcast_confirm_"):
            self._handle_broadcast_confirm(call)
        elif data.startswith("broadcast_delete_"):
            self._handle_broadcast_delete(call)
        elif data.startswith("broadcast_edit_"):
            self._handle_broadcast_edit(call)
        elif data == "admin_find_user":
            self._handle_admin_find_user(call)
        elif data.startswith("admin_user_stats_"):
            self._handle_admin_user_stats(call)
        elif data.startswith("admin_user_events_"):
            self._handle_admin_user_events(call)
        elif data.startswith("admin_reject_appeal_"):
            self._handle_admin_reject_appeal(call)
        elif data == "admin_all_reports":
            self._handle_admin_all_reports(call)

    def _handle_filter(self, call):
        """Обработка фильтров поиска"""
        user_id = call.from_user.id
        filter_type = call.data.replace("filter_", "")

        # Проверяем регистрацию
        user = execute_query(
            "SELECT * FROM users WHERE user_id=?", (user_id,), fetchone=True
        )

        if not user:
            self.bot.answer_callback_query(
                call.id, "❌ Сначала завершите регистрацию!")
            return

        # Проверяем бан
        if user['is_banned'] == 1:
            self.bot.answer_callback_query(
                call.id, "⛔ Ваш аккаунт заблокирован!")
            return

        # Показываем первое событие по выбранному фильтру
        self.show_next_event(call.message, user_id, filter_type=filter_type)
        self.bot.answer_callback_query(call.id)

    def _handle_report(self, call):
        """Обработка жалоб"""
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        data = call.data

        try:
            if "organizer" in data:
                event_id = data.split("_")[2]

                event = execute_query(
                    "SELECT user_id, title FROM events WHERE id = ?",
                    (event_id,), fetchone=True
                )

                if event:
                    reported_user_id = event['user_id']

                    if reported_user_id == user_id:
                        self.bot.answer_callback_query(
                            call.id, "❌ Нельзя жаловаться на себя!")
                        return

                    self.bot.send_message(
                        chat_id,
                        f"🚨 *ПОЖАЛОВАТЬСЯ НА ОРГАНИЗАТОРА*\n\n"
                        f"Вы хотите пожаловаться на организатора события:\n"
                        f"«*{escape_markdown(event['title'])}*»\n\n"
                        f"Пожалуйста, укажите причину жалобы:",
                        parse_mode='Markdown'
                    )

                    self.user_state[user_id] = f'report_organizer_{event_id}'
                    self.bot.answer_callback_query(call.id)
                else:
                    self.bot.answer_callback_query(
                        call.id, "❌ Событие не найдено")

            elif "user" in data:
                reported_user_id = int(data.split("_")[2])

                if reported_user_id == user_id:
                    self.bot.answer_callback_query(
                        call.id, "❌ Нельзя жаловаться на себя!")
                    return

                reported_user = execute_query(
                    "SELECT name FROM users WHERE user_id = ?",
                    (reported_user_id,), fetchone=True
                )

                if reported_user:
                    self.bot.send_message(
                        chat_id,
                        f"🚨 *ПОЖАЛОВАТЬСЯ НА ПОЛЬЗОВАТЕЛЯ*\n\n"
                        f"Вы хотите пожаловаться на пользователя:\n"
                        f"*{escape_markdown(reported_user['name'])}*\n\n"
                        f"Пожалуйста, укажите причину жалобы:",
                        parse_mode='Markdown'
                    )

                    self.user_state[user_id] = f'report_user_{reported_user_id}'
                    self.bot.answer_callback_query(call.id)
                else:
                    self.bot.answer_callback_query(
                        call.id, "❌ Пользователь не найден")

        except Exception as e:
            print(f"Ошибка при создании жалобы: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка обработки")

    def _handle_skip(self, call):
        """Обработка пропуска события"""
        try:
            event_id = call.data.split("_")[1]
            chat_id = call.message.chat.id

            self.bot.answer_callback_query(call.id, "➡️ Событие пропущено")

            # Удаляем сообщение
            try:
                self.bot.delete_message(chat_id, call.message.message_id)
            except:
                pass

            # Показываем следующее событие
            user_id = call.from_user.id
            if user_id in self.user_data:
                user_data_info = self.user_data[user_id]
                filter_type = user_data_info.get('filter_type')
                self.show_next_event(call.message, user_id,
                                     filter_type=filter_type)

        except Exception as e:
            print(f"Ошибка при пропуске: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка обработки")

    def _handle_next(self, call):
        """Обработка перехода к следующему событию"""
        try:
            event_index = int(call.data.split("_")[1])
            chat_id = call.message.chat.id

            self.bot.answer_callback_query(call.id)

            # Удаляем сообщение
            try:
                self.bot.delete_message(chat_id, call.message.message_id)
            except:
                pass

            # Показываем следующее событие
            user_id = call.from_user.id
            if user_id in self.user_data:
                user_data_info = self.user_data[user_id]
                filter_type = user_data_info.get('filter_type')
                self.show_next_event(call.message, user_id,
                                     event_index, filter_type)

        except Exception as e:
            print(f"Ошибка при переходе к следующему: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка обработки")

    def _handle_ignore(self, call):
        """Обработка игнорирования лайка"""
        try:
            like_id = call.data.split("_")[1]
            chat_id = call.message.chat.id

            like = execute_query(
                "SELECT from_user, to_user FROM likes WHERE id = ?",
                (like_id,), fetchone=True
            )

            if not like:
                self.bot.answer_callback_query(call.id, "❌ Лайк не найден")
                return

            if like['to_user'] != call.from_user.id:
                self.bot.answer_callback_query(call.id, "❌ Это не ваш лайк")
                return

            self.bot.answer_callback_query(call.id, "➡️ Лайк пропущен")

            # Удаляем сообщение
            try:
                self.bot.delete_message(chat_id, call.message.message_id)
            except:
                pass

        except Exception as e:
            print(f"Ошибка при игнорировании лайка: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка обработки")

    def _handle_appeal_ban(self, call):
        """Обработка оспаривания блокировки"""
        try:
            target_user_id = int(call.data.split("_")[2])
            user_id = call.from_user.id

            if target_user_id != user_id:
                self.bot.answer_callback_query(
                    call.id, "❌ Нельзя оспаривать чужую блокировку")
                return

            self.bot.send_message(
                call.message.chat.id,
                "📝 *ОСПАРИВАНИЕ БЛОКИРОВКИ*\n\n"
                "Пожалуйста, напишите текст вашей апелляции.\n"
                "Объясните, почему вы считаете блокировку несправедливой:",
                parse_mode='Markdown'
            )

            # состояние хранится в общем словаре (см. `bot.py`)
            self.user_state[user_id] = f'appeal_ban_{target_user_id}'
            self.bot.answer_callback_query(call.id)

        except Exception as e:
            print(f"Ошибка при оспаривании блокировки: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка обработки")

    def _handle_other_callbacks(self, call):
        """Обработка других callback"""
        data = call.data

        if data == "new_search":
            self._handle_new_search(call)
        elif data == "create_event":
            self._handle_create_event(call)
        elif data == "back_to_profile":
            self._handle_back_to_profile(call)
        elif data == "edit_profile":
            self._handle_edit_profile(call)
        elif data == "my_events_list":
            self._handle_my_events_list(call)
        elif data.startswith("my_events_"):
            self._handle_my_events_pagination(call)
        elif data.startswith("edit_event_"):
            self._handle_edit_event(call)
        elif data.startswith("delete_event_"):
            self._handle_delete_event(call)
        elif data.startswith("edit_title_"):
            self._handle_edit_event_field(call, "title")
        elif data.startswith("edit_desc_"):
            self._handle_edit_event_field(call, "description")
        elif data.startswith("edit_date_"):
            self._handle_edit_event_field(call, "date")
        elif data.startswith("edit_target_"):
            self._handle_edit_event_field(call, "target")
        elif data.startswith("edit_event_city_"):
            self._handle_edit_event_field(call, "city")
        elif data.startswith("edit_category_"):
            self._handle_edit_event_field(call, "category")
        elif data.startswith("cancel_edit_"):
            self._handle_cancel_edit(call)
        elif data.startswith("like_cat_"):
            self._handle_like_category(call)
        elif data.startswith("dislike_cat_"):
            self._handle_dislike_category(call)
        elif data.startswith("like_user_"):
            self._handle_like_user(call)
        else:
            self.bot.answer_callback_query(call.id, "⚠️ Команда не распознана")

    def _handle_new_search(self, call):
        """Обработка нового поиска"""
        user_id = call.from_user.id

        user = execute_query(
            "SELECT * FROM users WHERE user_id=?", (user_id,), fetchone=True
        )

        if not user:
            self.bot.answer_callback_query(
                call.id, "❌ Сначала завершите регистрацию!")
            return

        keyboard = get_filter_keyboard()
        self.bot.send_message(
            call.message.chat.id,
            "🔍 *Выберите тип поиска:*",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        self.bot.answer_callback_query(call.id)

    def _handle_create_event(self, call):
        """Обработка создания события из callback"""
        user_id = call.from_user.id

        user = execute_query(
            "SELECT * FROM users WHERE user_id=?", (user_id,), fetchone=True
        )

        if not user:
            self.bot.answer_callback_query(
                call.id, "❌ Сначала завершите регистрацию!")
            return

        self.user_state[user_id] = 'waiting_event_title'
        self.bot.send_message(call.message.chat.id,
                              "Введите название события:")
        self.bot.answer_callback_query(call.id)

    def _handle_back_to_profile(self, call):
        """Обработка возврата к профилю"""
        if self.user_handlers:
            self.user_handlers.show_profile(call.message)
        else:
            # fallback: просто показываем главное меню
            self.bot.send_message(call.message.chat.id, "Главное меню:", reply_markup=get_main_menu())
        self.bot.answer_callback_query(call.id)

    def _handle_edit_profile(self, call):
        """Обработка редактирования профиля"""
        self.bot.send_message(
            call.message.chat.id,
            "Выберите что изменить:",
            reply_markup=get_profile_menu()
        )
        self.bot.answer_callback_query(call.id)

    def _handle_my_events_list(self, call):
        """Обработка показа событий пользователя"""
        from handlers.event_handlers import EventHandlers
        event_handler = EventHandlers(self.bot)
        event_handler.show_my_events(call.message)
        self.bot.answer_callback_query(call.id)

    def _handle_my_events_pagination(self, call):
        """Обработка пагинации событий"""
        try:
            page = int(call.data.split("_")[2])
            from handlers.event_handlers import EventHandlers
            event_handler = EventHandlers(self.bot)
            event_handler.show_my_events(call.message, page=page)
            self.bot.answer_callback_query(call.id)
        except:
            self.bot.answer_callback_query(call.id, "❌ Ошибка обработки")

    def _handle_edit_event(self, call):
        """Обработка редактирования события"""
        try:
            event_id = int(call.data.split("_")[2])
            keyboard = get_event_edit_keyboard(event_id)

            try:
                self.bot.edit_message_reply_markup(
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboard
                )
            except:
                self.bot.send_message(
                    call.message.chat.id,
                    "Выберите что редактировать:",
                    reply_markup=keyboard
                )

            self.bot.answer_callback_query(call.id)
        except:
            self.bot.answer_callback_query(call.id, "❌ Ошибка обработки")

    def _handle_delete_event(self, call):
        """Обработка удаления события"""
        try:
            event_id = int(call.data.split("_")[2])
            user_id = call.from_user.id

            # Проверяем, принадлежит ли событие пользователю
            event = execute_query(
                "SELECT user_id FROM events WHERE id = ?",
                (event_id,), fetchone=True
            )

            if not event or event['user_id'] != user_id:
                self.bot.answer_callback_query(
                    call.id, "❌ Вы не можете удалить это событие")
                return

            # Сначала удаляем связанные лайки, затем событие (из-за FK)
            execute_query(
                "DELETE FROM likes WHERE event_id = ?",
                (event_id,), commit=True
            )
            execute_query(
                "DELETE FROM events WHERE id = ?",
                (event_id,), commit=True
            )

            self.bot.answer_callback_query(call.id, "✅ Событие удалено")

            # Удаляем сообщение
            try:
                self.bot.delete_message(
                    call.message.chat.id, call.message.message_id)
            except:
                pass

        except Exception as e:
            print(f"Ошибка при удалении события: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка удаления")

    def _handle_edit_event_field(self, call, field_type):
        """Обработка редактирования поля события"""
        try:
            event_id = int(call.data.split("_")[2])
            user_id = call.from_user.id

            # Проверяем права на редактирование
            event = execute_query(
                "SELECT user_id FROM events WHERE id = ?",
                (event_id,), fetchone=True
            )

            if not event or event['user_id'] != user_id:
                self.bot.answer_callback_query(
                    call.id, "❌ Вы не можете редактировать это событие")
                return

            messages = {
                "title": "Введите новое название события:",
                "description": "Введите новое описание события:",
                "date": "Введите новую дату события (например: 25.12.2024 19:00):",
                "target": "Выберите для кого событие:",  # Покажем клавиатуру
                "city": "Введите новый город для события:",
                "category": "Выберите новую категорию:"  # Покажем клавиатуру
            }

            if field_type in ["target", "category"]:
                if field_type == "target":
                    self.bot.send_message(
                        call.message.chat.id,
                        messages[field_type],
                        reply_markup=get_target_gender_keyboard()
                    )
                elif field_type == "category":
                    self.bot.send_message(
                        call.message.chat.id,
                        messages[field_type],
                        reply_markup=get_category_keyboard()
                    )
                self.user_state[user_id] = f'edit_event_{field_type}_{event_id}'
            else:
                self.bot.send_message(
                    call.message.chat.id, messages[field_type])
                self.user_state[user_id] = f'edit_event_{field_type}_{event_id}'

            self.bot.answer_callback_query(call.id)

        except Exception as e:
            print(f"Ошибка при редактировании события: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка обработки")

    def _handle_cancel_edit(self, call):
        """Обработка отмены редактирования"""
        try:
            event_id = int(call.data.split("_")[2])

            # Возвращаемся к просмотру события
            event = execute_query(
                "SELECT * FROM events WHERE id = ?",
                (event_id,), fetchone=True
            )

            if event:
                event_text = f"""*{escape_markdown(event['title'])}*
🏷️ Категория: {event.get('category', '🎯 Разное')}

📝 {escape_markdown(event['description'])}
📅 {escape_markdown(event['event_date'])}
🏙️ Город: {escape_markdown(event['city'])}
👥 Для: {escape_markdown(event['target_gender'])}"""

                keyboard = get_event_action_keyboard(event_id)

                try:
                    self.bot.edit_message_text(
                        event_text,
                        call.message.chat.id,
                        call.message.message_id,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                except:
                    self.bot.send_message(
                        call.message.chat.id,
                        event_text,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )

            self.bot.answer_callback_query(call.id)

        except Exception as e:
            print(f"Ошибка при отмене редактирования: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка обработки")

    def _handle_like_category(self, call):
        """Обработка лайка категории"""
        try:
            category = call.data.split("_")[2]
            user_id = call.from_user.id

            # Обновляем предпочтения пользователя
            prefs = execute_query(
                "SELECT liked_categories FROM user_preferences WHERE user_id = ?",
                (user_id,), fetchone=True
            )

            if not prefs:
                execute_query(
                    "INSERT INTO user_preferences (user_id, liked_categories) VALUES (?, ?)",
                    (user_id, json.dumps([category])), commit=True
                )
            else:
                try:
                    liked = json.loads(prefs['liked_categories'])
                except:
                    liked = []

                if category not in liked:
                    liked.append(category)
                    execute_query(
                        "UPDATE user_preferences SET liked_categories = ? WHERE user_id = ?",
                        (json.dumps(liked), user_id), commit=True
                    )

            self.bot.answer_callback_query(call.id, f"✅ Нравится {category}")

        except Exception as e:
            print(f"Ошибка при лайке категории: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка обработки")

    def _handle_dislike_category(self, call):
        """Обработка дизлайка категории"""
        try:
            category = call.data.split("_")[2]
            user_id = call.from_user.id

            # Обновляем предпочтения пользователя
            prefs = execute_query(
                "SELECT disliked_categories FROM user_preferences WHERE user_id = ?",
                (user_id,), fetchone=True
            )

            if not prefs:
                execute_query(
                    "INSERT INTO user_preferences (user_id, disliked_categories) VALUES (?, ?)",
                    (user_id, json.dumps([category])), commit=True
                )
            else:
                try:
                    disliked = json.loads(prefs['disliked_categories'])
                except:
                    disliked = []

                if category not in disliked:
                    disliked.append(category)
                    execute_query(
                        "UPDATE user_preferences SET disliked_categories = ? WHERE user_id = ?",
                        (json.dumps(disliked), user_id), commit=True
                    )

            self.bot.answer_callback_query(
                call.id, f"❌ Не нравится {category}")

        except Exception as e:
            print(f"Ошибка при дизлайке категории: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка обработки")

    def _handle_like_user(self, call):
        """Обработка лайка пользователя (прямого)"""
        try:
            liked_user_id = int(call.data.split("_")[2])
            user_id = call.from_user.id

            if liked_user_id == user_id:
                self.bot.answer_callback_query(
                    call.id, "❌ Нельзя лайкнуть себя!")
                return

            # Проверяем, не лайкал ли уже
            existing_like = execute_query(
                "SELECT id FROM likes WHERE from_user=? AND to_user=? AND event_id IS NULL",
                (user_id, liked_user_id), fetchone=True
            )

            if existing_like:
                self.bot.answer_callback_query(
                    call.id, "❤️ Вы уже лайкали этого пользователя")
                return

            # Создаем лайк
            like_id = execute_query(
                '''INSERT INTO likes (from_user, to_user, created) 
                   VALUES (?, ?, ?) RETURNING id''',
                (user_id, liked_user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                commit=True
            )

            # Начисляем очки
            AchievementService.update_user_points(
                user_id, 3, "за лайк пользователя")

            # Проверяем взаимность
            mutual_check = execute_query(
                "SELECT id FROM likes WHERE from_user=? AND to_user=? AND event_id IS NULL",
                (liked_user_id, user_id), fetchone=True
            )

            if mutual_check:
                # Делаем оба лайка взаимными
                execute_query(
                    "UPDATE likes SET mutual = TRUE WHERE id IN (?, ?)",
                    (like_id, mutual_check['id']), commit=True
                )

                # Начисляем очки за взаимность
                AchievementService.update_user_points(
                    user_id, 20, "за взаимную симпатию")
                AchievementService.update_user_points(
                    liked_user_id, 20, "за взаимную симпатию")

                # Отправляем уведомления
                NotificationService.send_match_notification(
                    user_id, liked_user_id, None, self.bot)

            self.bot.answer_callback_query(
                call.id, "❤️ Вы лайкали пользователя!")

        except Exception as e:
            print(f"Ошибка при лайке пользователя: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка обработки")

    def show_next_event(self, message, user_id, event_index=0, filter_type=None):
        """Показать следующее событие для просмотра"""
        from handlers.event_handlers import EventHandlers
        event_handler = EventHandlers(self.bot)
        event_handler.show_next_event(
            message, user_id, event_index, filter_type)

    def _show_admin_main_menu(self, call):
        """Показать главное меню админ-панели"""
        keyboard = get_admin_main_keyboard()

        try:
            self.bot.edit_message_text(
                "⚡ *АДМИН-ПАНЕЛЬ*\n\nВыберите действие:",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        except:
            self.bot.send_message(
                call.message.chat.id,
                "⚡ *АДМИН-ПАНЕЛЬ*\n\nВыберите действие:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )

        self.bot.answer_callback_query(call.id)

    def _show_admin_stats(self, call):
        """Показать статистику админ-панели"""
        stats = AdminService.get_admin_stats()
        stats_message = AdminService.format_stats_message(stats)

        keyboard = get_admin_back_keyboard()

        try:
            self.bot.edit_message_text(
                stats_message,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        except:
            self.bot.send_message(
                call.message.chat.id,
                stats_message,
                parse_mode='Markdown',
                reply_markup=keyboard
            )

        self.bot.answer_callback_query(call.id)

    def _show_broadcast_menu(self, call):
        """Показать меню рассылки"""
        keyboard = get_broadcast_type_keyboard()

        try:
            self.bot.edit_message_text(
                "📨 *СОЗДАНИЕ РАССЫЛКИ*\n\nВыберите тип контента:",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        except:
            self.bot.send_message(
                call.message.chat.id,
                "📨 *СОЗДАНИЕ РАССЫЛКИ*\n\nВыберите тип контента:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )

        self.bot.answer_callback_query(call.id)

    def _show_users_menu(self, call):
        """Показать меню пользователей"""
        stats = AdminService.get_admin_stats()

        users_message = "👥 *СПИСОК ПОЛЬЗОВАТЕЛЕЙ*\n\n"

        recent_users = execute_query(
            "SELECT user_id, name, age, gender, city, reg_date, is_banned FROM users ORDER BY reg_date DESC LIMIT 10",
            fetchall=True
        )

        if recent_users:
            users_message += "📋 *Последние 10 пользователей:*\n\n"
            for i, user in enumerate(recent_users, 1):
                status = "⛔" if user['is_banned'] == 1 else "✅"
                users_message += f"{i}. {status} {user['name']} ({user['age']} лет, {user['gender']})\n"
                users_message += f"   🏙️ {user['city']} | 📅 {user['reg_date'][:10]}\n"
                users_message += f"   👤 ID: {user['user_id']}\n\n"
        else:
            users_message += "❌ Пользователей не найдено\n"

        users_message += f"\n📊 *Всего пользователей:* {stats['total_users']:,}\n"
        users_message += f"⛔ *Заблокировано:* {stats['banned_users']}"

        keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            telebot.types.InlineKeyboardButton(
                "🔍 Найти пользователя", callback_data="admin_find_user"),
            telebot.types.InlineKeyboardButton(
                "⬅️ Назад", callback_data="admin_back")
        )

        try:
            self.bot.edit_message_text(
                users_message,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        except:
            self.bot.send_message(
                call.message.chat.id,
                users_message,
                parse_mode='Markdown',
                reply_markup=keyboard
            )

        self.bot.answer_callback_query(call.id)

    def _show_reports_menu(self, call):
        """Показать меню жалоб"""
        reports = ReportService.get_reports_by_status('pending')

        if not reports:
            message_text = "🚨 *ЖАЛОБЫ НА ПОЛЬЗОВАТЕЛЕЙ*\n\nНа данный момент нет жалоб, ожидающих рассмотрения."
        else:
            message_text = f"🚨 *ЖАЛОБЫ НА ПОЛЬЗОВАТЕЛЕЙ*\n\nОжидают рассмотрения: {len(reports)}\n\n"

            for i, report in enumerate(reports[:5], 1):
                reporter = execute_query(
                    "SELECT name FROM users WHERE user_id = ?",
                    (report['reporter_id'],), fetchone=True
                )
                reported = execute_query(
                    "SELECT name FROM users WHERE user_id = ?",
                    (report['reported_user_id'],), fetchone=True
                )

                reporter_name = reporter['name'] if reporter else f"ID: {report['reporter_id']}"
                reported_name = reported['name'] if reported else f"ID: {report['reported_user_id']}"

                message_text += f"{i}. *Жалоба #{report['id']}*\n"
                message_text += f"   👤 От: {escape_markdown(reporter_name)}\n"
                message_text += f"   ⚠️ На: {escape_markdown(reported_name)}\n"
                message_text += f"   📝 Причина: {escape_markdown(report['reason'][:50])}...\n"
                message_text += f"   📅 Дата: {report['created'][:10]}\n\n"

        keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            telebot.types.InlineKeyboardButton(
                "📋 Все жалобы", callback_data="admin_all_reports"),
            telebot.types.InlineKeyboardButton(
                "⬅️ Назад", callback_data="admin_back")
        )

        try:
            self.bot.edit_message_text(
                message_text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        except:
            self.bot.send_message(
                call.message.chat.id,
                message_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )

        self.bot.answer_callback_query(call.id)

    def _handle_admin_ban(self, call):
        """Обработка блокировки пользователя админом"""
        try:
            target_user_id = int(call.data.replace(
                "admin_ban_", "").replace("_from_report", ""))

            self.bot.edit_message_text(
                f"⛔ *БЛОКИРОВКА ПОЛЬЗОВАТЕЛЯ*\n\n"
                f"Вы собираетесь заблокировать пользователя ID: `{target_user_id}`\n\n"
                f"Введите причину блокировки:",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=get_admin_back_keyboard()
            )

            self._admin_state()[call.from_user.id] = f'admin_ban_reason_{target_user_id}'
            self.bot.answer_callback_query(call.id)

        except Exception as e:
            print(f"Ошибка при блокировке пользователя: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка обработки")

    def _handle_admin_unban(self, call):
        """Обработка разблокировки пользователя админом"""
        try:
            target_user_id = int(call.data.replace(
                "admin_unban_", "").replace("_from_report", ""))

            if ReportService.unban_user(target_user_id):
                # Если это было подтверждение апелляции — отмечаем её принятой
                try:
                    execute_query(
                        """UPDATE reports
                           SET appeal_status = 'accepted', admin_notes = COALESCE(admin_notes,'') || ' | Апелляция принята'
                           WHERE id = (
                               SELECT id FROM reports
                               WHERE reported_user_id = ? AND appeal_status = 'pending'
                               ORDER BY created DESC LIMIT 1
                           )""",
                        (target_user_id,), commit=True
                    )
                except Exception as e:
                    print(f"Ошибка обновления статуса апелляции: {e}")

                keyboard = telebot.types.InlineKeyboardMarkup()
                keyboard.add(
                    telebot.types.InlineKeyboardButton(
                        "⬅️ Назад", callback_data="admin_reports")
                )

                self.bot.send_message(
                    call.message.chat.id,
                    f"✅ *Пользователь ID:{target_user_id} разблокирован!*\n\n"
                    f"Его события теперь видны другим пользователям.",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )

                try:
                    self.bot.send_message(
                        target_user_id,
                        "✅ *Ваш аккаунт разблокирован!*\n\n"
                        "Теперь вы можете снова использовать бота.",
                        parse_mode='Markdown'
                    )
                except:
                    pass
            else:
                self.bot.send_message(
                    call.message.chat.id,
                    f"❌ *Ошибка при разблокировке пользователя!*",
                    parse_mode='Markdown',
                    reply_markup=get_admin_back_keyboard()
                )

            self.bot.answer_callback_query(call.id)

        except Exception as e:
            print(f"Ошибка при разблокировке пользователя: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка обработки")

    def _handle_admin_view_user(self, call):
        """Обработка просмотра профиля пользователя админом"""
        try:
            target_user_id = int(call.data.replace("admin_view_user_", ""))

            user_info = AdminService.get_user_full_info(str(target_user_id))

            if user_info:
                profile_text = f"""🔍 *ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ*

👤 *Основная информация:*
📛 Имя: {escape_markdown(user_info['name'])}
🆔 ID: `{user_info['user_id']}`
👤 Username: @{escape_markdown(user_info['username']) if user_info['username'] else 'нет'}
🎂 Возраст: {escape_markdown(str(user_info['age']))}
⚧️ Пол: {escape_markdown(user_info['gender'])}
🏙️ Город: {escape_markdown(user_info['city']) if user_info['city'] else 'Не указан'}
💖 Статус: {escape_markdown(user_info['relationship_status']) if user_info['relationship_status'] else 'Не указан'}
{'⛔ ЗАБЛОКИРОВАН' if user_info['is_banned'] == 1 else '✅ Активен'}

🎯 *Цель:*
{escape_markdown(user_info['purpose']) if user_info['purpose'] else 'куда-то сходить'}

📊 *Статистика:*
⭐ Очки: {user_info['points']}
🎉 Событий создано: {user_info['events_count']}
❤️ Лайков получено: {user_info['likes_received']}
👍 Лайков поставлено: {user_info['likes_given']}
💞 Взаимных симпатий: {user_info['mutual_likes']}
🏆 Достижений: {user_info['achievements_count']}"""

                markup = telebot.types.InlineKeyboardMarkup(row_width=2)

                if user_info['is_banned'] == 1:
                    markup.add(
                        telebot.types.InlineKeyboardButton(
                            "✅ Разблокировать", callback_data=f"admin_unban_{user_info['user_id']}_from_report"),
                        telebot.types.InlineKeyboardButton(
                            "⬅️ Назад", callback_data="admin_reports")
                    )
                else:
                    markup.add(
                        telebot.types.InlineKeyboardButton(
                            "⛔ Заблокировать", callback_data=f"admin_ban_{user_info['user_id']}_from_report"),
                        telebot.types.InlineKeyboardButton(
                            "⬅️ Назад", callback_data="admin_reports")
                    )

                try:
                    if user_info.get('photo'):
                        self.bot.send_photo(
                            call.message.chat.id,
                            user_info['photo'],
                            caption=profile_text,
                            parse_mode='Markdown',
                            reply_markup=markup
                        )
                    else:
                        self.bot.send_message(
                            call.message.chat.id,
                            profile_text + "\n\n📸 *Фото не загружено*",
                            parse_mode='Markdown',
                            reply_markup=markup
                        )
                except:
                    self.bot.send_message(
                        call.message.chat.id,
                        profile_text + "\n\n📸 *Фото не загружено*",
                        parse_mode='Markdown',
                        reply_markup=markup
                    )

            self.bot.answer_callback_query(call.id)

        except Exception as e:
            print(f"Ошибка при просмотре профиля пользователя: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка обработки")

    def _handle_admin_dismiss_report(self, call):
        """Обработка отклонения жалобы админом"""
        try:
            report_id = int(call.data.replace("admin_dismiss_report_", ""))

            ReportService.update_report_status(
                report_id, "dismissed", "Жалоба отклонена админом")

            self.bot.answer_callback_query(call.id, "✅ Жалоба отклонена")

            try:
                self.bot.edit_message_text(
                    f"✅ Жалоба #{report_id} была отклонена.",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=get_admin_back_keyboard()
                )
            except:
                self.bot.send_message(
                    call.message.chat.id,
                    f"✅ Жалоба #{report_id} была отклонена.",
                    reply_markup=get_admin_back_keyboard()
                )

        except Exception as e:
            print(f"Ошибка при отклонении жалобы: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка обработки")

    def _handle_broadcast_type(self, call):
        """Обработка выбора типа рассылки"""
        content_type = call.data.replace("broadcast_type_", "")

        admin_id = call.from_user.id

        admin_broadcast_data = self._admin_broadcast_data()
        admin_state = self._admin_state()

        admin_broadcast_data[admin_id] = {
            'content_type': content_type,
            'filters': {'gender': 'all', 'cities': ['all']}
        }

        if content_type == "text":
            self.bot.edit_message_text(
                f"📝 *ТЕКСТОВАЯ РАССЫЛКА*\n\nВведите текст сообщения (поддерживается Markdown):",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=get_admin_back_keyboard()
            )
            admin_state[admin_id] = 'admin_broadcast_text'

        elif content_type == "photo":
            self.bot.edit_message_text(
                f"🖼️ *ФОТО-РАССЫЛКА*\n\n"
                f"Отправьте фото (можно с подписью — поддерживается Markdown):",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=get_admin_back_keyboard()
            )
            admin_state[admin_id] = 'admin_broadcast_photo'

        elif content_type == "link":
            self.bot.edit_message_text(
                f"🔗 *ССЫЛОЧНАЯ РАССЫЛКА*\n\nВведите ссылку (начните с http:// или https://):",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=get_admin_back_keyboard()
            )
            admin_state[admin_id] = 'admin_broadcast_link'

        self.bot.answer_callback_query(call.id)

    def _handle_broadcast_filter(self, call):
        """Обработка фильтров рассылки"""
        admin_id = call.from_user.id
        data = call.data

        admin_broadcast_data = self._admin_broadcast_data()
        admin_state = self._admin_state()

        if admin_id not in admin_broadcast_data:
            self.bot.answer_callback_query(
                call.id, "❌ Данные рассылки не найдены")
            return

        # Обработка фильтров по полу
        if data.startswith("broadcast_filter_gender_"):
            gender = data.replace("broadcast_filter_gender_", "")

            if gender == "all":
                admin_broadcast_data[admin_id]['filters']['gender'] = 'all'
                self.bot.answer_callback_query(call.id, "✅ Все пользователи")
            elif gender == "done":
                # Переход к следующему шагу
                self.bot.edit_message_text(
                    f"👥 *ФИЛЬТР ПО ВОЗРАСТУ*\n\n"
                    f"Введите возрастной диапазон (например: 18-30)\n"
                    f"Или введите 0 для отключения фильтра:",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown',
                    reply_markup=get_admin_back_keyboard()
                )
                admin_state[admin_id] = 'admin_broadcast_age'
            else:
                admin_broadcast_data[admin_id]['filters']['gender'] = gender
                self.bot.answer_callback_query(
                    call.id, f"✅ Выбран пол: {gender}")

        # Обработка фильтров по городам
        elif data.startswith("broadcast_filter_city_"):
            city_data = data.replace("broadcast_filter_city_", "")

            if city_data == "all":
                admin_broadcast_data[admin_id]['filters']['cities'] = ['all']
                self.bot.answer_callback_query(call.id, "✅ Выбраны все города")
            elif city_data == "done":
                # Сохраняем и показываем предпросмотр
                self._save_and_preview_broadcast(
                    admin_id, call.message.chat.id)
            else:
                if 'cities' not in admin_broadcast_data[admin_id]['filters']:
                    admin_broadcast_data[admin_id]['filters']['cities'] = []

                if city_data in admin_broadcast_data[admin_id]['filters']['cities']:
                    admin_broadcast_data[admin_id]['filters']['cities'].remove(
                        city_data)
                    self.bot.answer_callback_query(
                        call.id, f"❌ Город {city_data} удален")
                else:
                    admin_broadcast_data[admin_id]['filters']['cities'].append(
                        city_data)
                    self.bot.answer_callback_query(
                        call.id, f"✅ Город {city_data} добавлен")

        # Обработка фильтров по рефералам
        elif data.startswith("broadcast_filter_referral_"):
            referral_status = data.replace("broadcast_filter_referral_", "")

            if referral_status == "all":
                admin_broadcast_data[admin_id]['filters']['referral_status'] = None
                self.bot.answer_callback_query(call.id, "✅ Все пользователи")
            elif referral_status == "done":
                # Сохраняем и показываем предпросмотр
                self._save_and_preview_broadcast(
                    admin_id, call.message.chat.id)
            else:
                # Нормализуем значения под `BroadcastService.get_users_by_filters`
                mapped = {
                    'with': 'with_referral',
                    'without': 'without_referral',
                }.get(referral_status, referral_status)
                admin_broadcast_data[admin_id]['filters']['referral_status'] = mapped
                self.bot.answer_callback_query(
                    call.id, "✅ Фильтр сохранен")

    def _save_and_preview_broadcast(self, admin_id, chat_id):
        """Сохраняет рассылку и показывает предпросмотр"""
        if admin_id not in self.admin_broadcast_data:
            self.bot.send_message(chat_id, "❌ Данные рассылки не найдены")
            return

        data = self.admin_broadcast_data[admin_id]

        # Сохраняем рассылку в БД
        broadcast_id = execute_query(
            '''INSERT INTO admin_broadcasts 
               (admin_id, content_type, content, caption, filters, created, status) 
               VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id''',
            (
                admin_id,
                data['content_type'],
                data['content'],
                data.get('caption', ''),
                json.dumps(data['filters']),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'pending'
            ),
            commit=True
        )

        # Получаем количество пользователей по фильтрам
        from services.broadcast import BroadcastService
        user_ids = BroadcastService.get_users_by_filters(data['filters'])
        user_count = len(user_ids)

        # Формируем текст предпросмотра
        filters_text = ""
        if data['filters'].get('gender') and data['filters']['gender'] != 'all':
            filters_text += f"• Пол: {data['filters']['gender']}\n"

        if data['filters'].get('min_age') and data['filters'].get('max_age'):
            filters_text += f"• Возраст: {data['filters']['min_age']}-{data['filters']['max_age']} лет\n"

        if data['filters'].get('cities') and data['filters']['cities'] != ['all']:
            cities = ', '.join(data['filters']['cities'][:3])
            if len(data['filters']['cities']) > 3:
                cities += f" и еще {len(data['filters']['cities']) - 3}"
            filters_text += f"• Города: {cities}\n"

        if data['filters'].get('referral_status'):
            status_text = {
                'with_referral': 'С рефералом',
                'without_referral': 'Без реферала',
            }.get(data['filters']['referral_status'], data['filters']['referral_status'])
            filters_text += f"• Рефералы: {status_text}\n"

        if not filters_text:
            filters_text = "• Все пользователи\n"

        content_preview = ""
        if data['content_type'] == 'text':
            content_preview = f"📝 *Текст:*\n{data['content'][:200]}..."
        elif data['content_type'] == 'photo':
            content_preview = "🖼️ *Фото:* (будет отправлено как фото)\n" + (
                f"✍️ *Подпись:*\n{data.get('caption','')[:200]}..." if data.get('caption') else ""
            )
        elif data['content_type'] == 'link':
            content_preview = f"🔗 *Ссылка:* {data['content']}"

        preview_text = f"""📨 *ПРЕДПРОСМОТР РАССЫЛКИ #{broadcast_id}*

{content_preview}

📊 *ФИЛЬТРЫ:*
{filters_text}
👥 *Получателей:* {user_count:,}

⚠️ *Внимание:* Рассылку нельзя отменить после запуска!"""

        markup = get_broadcast_confirm_keyboard(broadcast_id)
        self.bot.send_message(
            chat_id,
            preview_text,
            parse_mode='Markdown',
            reply_markup=markup
        )

    def _handle_broadcast_confirm(self, call):
        """Обработка подтверждения рассылки"""
        broadcast_id = int(call.data.replace("broadcast_confirm_", ""))

        # Запускаем рассылку в отдельном потоке
        import threading

        self.bot.answer_callback_query(call.id, "🚀 Рассылка запущена!")

        try:
            self.bot.edit_message_text(
                "🚀 *Рассылка запущена!*\n\n"
                "Обработка началась. Вы получите уведомление о завершении.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )
        except:
            self.bot.send_message(
                call.message.chat.id,
                "🚀 *Рассылка запущена!*\n\n"
                "Обработка началась. Вы получите уведомление о завершении.",
                parse_mode='Markdown'
            )

        threading.Thread(
            target=BroadcastService.process_broadcast,
            args=(broadcast_id, call.from_user.id,
                  call.message.chat.id, self.bot)
        ).start()

    def _handle_broadcast_delete(self, call):
        """Удаление черновика/рассылки из предпросмотра"""
        try:
            broadcast_id = int(call.data.replace("broadcast_delete_", ""))
            execute_query(
                "DELETE FROM admin_broadcasts WHERE id = ?",
                (broadcast_id,), commit=True
            )
            self.bot.answer_callback_query(call.id, "🗑️ Удалено")
            self.bot.edit_message_text(
                f"🗑️ *Рассылка #{broadcast_id} удалена.*",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=get_admin_back_keyboard()
            )
        except Exception as e:
            print(f"Ошибка удаления рассылки: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка удаления")

    def _handle_broadcast_edit(self, call):
        """Редактирование рассылки (пока упрощено)"""
        try:
            broadcast_id = int(call.data.replace("broadcast_edit_", ""))
            self.bot.answer_callback_query(call.id)
            self.bot.edit_message_text(
                f"✏️ *Редактирование рассылки #{broadcast_id}*\n\n"
                f"Пока не поддерживается. Создайте новую рассылку.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=get_admin_back_keyboard()
            )
        except Exception as e:
            print(f"Ошибка редактирования рассылки: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка")

    def _handle_admin_find_user(self, call):
        """Обработка поиска пользователя админом"""
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(
            telebot.types.InlineKeyboardButton(
                "⬅️ Назад", callback_data="admin_users")
        )

        try:
            self.bot.edit_message_text(
                "🔍 *ПОИСК ПОЛЬЗОВАТЕЛЯ*\n\n"
                "Введите ID пользователя или его username (без @):\n\n"
                "Примеры:\n"
                "• ID: `123456789`\n"
                "• Username: `ivanov`",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        except:
            self.bot.send_message(
                call.message.chat.id,
                "🔍 *ПОИСК ПОЛЬЗОВАТЕЛЯ*\n\n"
                "Введите ID пользователя или его username (без @):\n\n"
                "Примеры:\n"
                "• ID: `123456789`\n"
                "• Username: `ivanov`",
                parse_mode='Markdown',
                reply_markup=keyboard
            )

        self._admin_state()[call.from_user.id] = 'admin_find_user'
        self.bot.answer_callback_query(call.id)

    def _handle_admin_user_stats(self, call):
        """Обработка просмотра статистики пользователя"""
        try:
            user_id = int(call.data.replace("admin_user_stats_", ""))

            # Получаем расширенную статистику пользователя
            user_info = AdminService.get_user_full_info(str(user_id))

            if user_info:
                stats_text = f"""📊 *ПОЛНАЯ СТАТИСТИКА ПОЛЬЗОВАТЕЛЯ*

👤 *Основная информация:*
📛 Имя: {escape_markdown(user_info['name'])}
🆔 ID: `{user_info['user_id']}`
👤 Username: @{escape_markdown(user_info['username']) if user_info['username'] else 'нет'}

📅 *Даты:*
📅 Регистрация: {user_info['reg_date'][:10] if user_info['reg_date'] else 'Неизвестно'}
⏰ Последняя активность: {user_info['last_active'] if user_info['last_active'] else 'Неизвестно'}

📊 *Статистика активности:*
⭐ Очки: {user_info['points']}
🎉 Событий создано: {user_info['events_count']}
❤️ Лайков получено: {user_info['likes_received']}
👍 Лайков поставлено: {user_info['likes_given']}
💞 Взаимных симпатий: {user_info['mutual_likes']}
🏆 Достижений: {user_info['achievements_count']}

👥 *Реферальная система:*
📊 Приглашено друзей: {user_info['referrals_count']}
🔗 Приглашен: {'Да' if user_info['referred_by'] else 'Нет'}"""

                if user_info['is_banned'] == 1:
                    stats_text += f"\n\n⛔ *Причина блокировки:* {user_info['ban_reason'] or 'Не указана'}"
                    stats_text += f"\n📅 *Дата блокировки:* {user_info['banned_date'][:10] if user_info['banned_date'] else 'Неизвестно'}"

                keyboard = get_admin_back_keyboard()

                self.bot.send_message(
                    call.message.chat.id,
                    stats_text,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )

            self.bot.answer_callback_query(call.id)

        except Exception as e:
            print(f"Ошибка при просмотре статистики пользователя: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка обработки")

    def _handle_admin_user_events(self, call):
        """Обработка просмотра событий пользователя"""
        try:
            user_id = int(call.data.replace("admin_user_events_", ""))

            # Получаем события пользователя
            events = execute_query(
                "SELECT id, title, description, event_date, target_gender, city, category, is_hidden FROM events WHERE user_id = ? ORDER BY event_date",
                (user_id,), fetchall=True
            )

            if not events:
                self.bot.send_message(
                    call.message.chat.id,
                    f"📅 *События пользователя ID:{user_id}*\n\nПользователь еще не создал событий.",
                    parse_mode='Markdown',
                    reply_markup=get_admin_back_keyboard()
                )
            else:
                events_text = f"📅 *События пользователя ID:{user_id}* ({len(events)} всего):\n\n"

                for i, event in enumerate(events[:10], 1):
                    status = "⛔ Скрыто" if event['is_hidden'] == 1 else "✅ Активно"
                    events_text += f"{i}. {status} *{escape_markdown(event['title'])}*\n"
                    events_text += f"   📅 {event['event_date']} | 🏙️ {event['city']}\n"
                    events_text += f"   👥 Для: {event['target_gender']} | 🏷️ {event.get('category', '🎯 Разное')}\n\n"

                if len(events) > 10:
                    events_text += f"... и еще {len(events) - 10} событий"

                keyboard = get_admin_back_keyboard()
                self.bot.send_message(
                    call.message.chat.id,
                    events_text,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )

            self.bot.answer_callback_query(call.id)

        except Exception as e:
            print(f"Ошибка при просмотре событий пользователя: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка обработки")

    def _handle_admin_reject_appeal(self, call):
        """Обработка отклонения апелляции"""
        try:
            user_id = int(call.data.replace("admin_reject_appeal_", ""))

            # Находим апелляцию
            report = execute_query(
                '''SELECT id FROM reports 
                   WHERE reported_user_id = ? AND appeal_status = 'pending' 
                   ORDER BY created DESC LIMIT 1''',
                (user_id,), fetchone=True
            )

            if report:
                execute_query(
                    "UPDATE reports SET appeal_status = 'rejected', admin_notes = ? WHERE id = ?",
                    ("Апелляция отклонена админом", report['id']), commit=True
                )

                try:
                    self.bot.send_message(
                        user_id,
                        "📢 *Ваша апелляция отклонена*\n\n"
                        "Администратор рассмотрел вашу апелляцию и оставил блокировку в силе.",
                        parse_mode='Markdown'
                    )
                except:
                    pass

                self.bot.answer_callback_query(
                    call.id, "✅ Апелляция отклонена")

                try:
                    self.bot.edit_message_text(
                        f"✅ Апелляция пользователя ID:{user_id} отклонена.",
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=get_admin_back_keyboard()
                    )
                except:
                    self.bot.send_message(
                        call.message.chat.id,
                        f"✅ Апелляция пользователя ID:{user_id} отклонена.",
                        reply_markup=get_admin_back_keyboard()
                    )
            else:
                self.bot.answer_callback_query(
                    call.id, "❌ Апелляция не найдена")

        except Exception as e:
            print(f"Ошибка при отклонении апелляции: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка обработки")

    def _handle_admin_all_reports(self, call):
        """Обработка показа всех жалоб"""
        reports = execute_query(
            "SELECT * FROM reports ORDER BY created DESC LIMIT 20",
            fetchall=True
        )

        if not reports:
            message_text = "🚨 *ВСЕ ЖАЛОБЫ*\n\nНет жалоб в системе."
        else:
            message_text = f"🚨 *ВСЕ ЖАЛОБЫ*\n\nВсего жалоб: {len(reports)}\n\n"

            for i, report in enumerate(reports[:10], 1):
                reporter = execute_query(
                    "SELECT name FROM users WHERE user_id = ?",
                    (report['reporter_id'],), fetchone=True
                )
                reported = execute_query(
                    "SELECT name FROM users WHERE user_id = ?",
                    (report['reported_user_id'],), fetchone=True
                )

                reporter_name = reporter['name'] if reporter else f"ID: {report['reporter_id']}"
                reported_name = reported['name'] if reported else f"ID: {report['reported_user_id']}"

                status_emoji = {
                    'pending': '⏳',
                    'resolved': '✅',
                    'dismissed': '❌'
                }.get(report['status'], '❓')

                message_text += f"{i}. {status_emoji} *Жалоба #{report['id']}*\n"
                message_text += f"   👤 От: {escape_markdown(reporter_name)}\n"
                message_text += f"   ⚠️ На: {escape_markdown(reported_name)}\n"
                message_text += f"   📝 Причина: {escape_markdown(report['reason'][:30])}...\n"
                message_text += f"   📅 Дата: {report['created'][:10]}\n"
                message_text += f"   📊 Статус: {report['status']}\n\n"

        keyboard = get_admin_back_keyboard()

        try:
            self.bot.edit_message_text(
                message_text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        except:
            self.bot.send_message(
                call.message.chat.id,
                message_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )

        self.bot.answer_callback_query(call.id)
