# handlers/admin_handlers.py
import telebot
from datetime import datetime
import json

from config import config
from database import execute_query
from keyboards.admin_keyboards import *
from services.admin import AdminService
from services.reports import ReportService
from utils.helpers import escape_markdown


class AdminHandlers:
    def __init__(self, bot):
        self.bot = bot
        self.user_state = {}
        self.admin_broadcast_data = {}

    def handle_admin(self, message):
        """Главная команда админ-панели"""
        user_id = message.from_user.id

        if not AdminService.is_admin(user_id):
            self.bot.send_message(
                message.chat.id, "⛔ У вас нет прав доступа к админ-панели."
            )
            return

        AdminService.log_admin_action(user_id, "admin_panel_open")

        markup = get_admin_main_keyboard()
        self.bot.send_message(
            message.chat.id,
            "⚡ *АДМИН-ПАНЕЛЬ*\n\nВыберите действие:",
            parse_mode='Markdown',
            reply_markup=markup
        )

    def handle_stats(self, message):
        """Быстрая команда статистики"""
        user_id = message.from_user.id

        if not AdminService.is_admin(user_id):
            self.bot.send_message(message.chat.id, "⛔ У вас нет прав доступа.")
            return

        AdminService.log_admin_action(user_id, "stats_command")

        try:
            stats = AdminService.get_admin_stats()
            stats_message = AdminService.format_stats_message(stats)

            self.bot.send_message(
                message.chat.id,
                stats_message,
                parse_mode='Markdown',
                reply_markup=get_admin_back_keyboard()
            )
        except Exception as e:
            self.bot.send_message(
                message.chat.id,
                f"❌ Ошибка получения статистики: {str(e)}",
                reply_markup=get_admin_back_keyboard()
            )
            print(f"Ошибка в stats_cmd: {e}")
            import traceback
            traceback.print_exc()

    def handle_text(self, message):
        """Обработка текстовых сообщений для админов"""
        user_id = message.from_user.id
        chat_id = message.chat.id
        text = message.text

        if not AdminService.is_admin(user_id):
            return False

        state = self.user_state.get(user_id)

        # Обработка рассылок
        if state and state.startswith('admin_broadcast'):
            if state == 'admin_broadcast_text':
                if user_id not in self.admin_broadcast_data:
                    self.admin_broadcast_data[user_id] = {
                        'content_type': 'text',
                        'filters': {'gender': 'all', 'cities': ['all']}
                    }

                self.admin_broadcast_data[user_id]['content'] = text
                self.admin_broadcast_data[user_id]['caption'] = ''

                markup = get_gender_filter_keyboard()
                self.bot.send_message(
                    chat_id,
                    f"✅ *Текст сохранен!*\n\n"
                    f"📝 *Предпросмотр:*\n{text[:200]}...\n\n"
                    f"👥 *ФИЛЬТР ПО ПОЛУ*\n\nВыберите пол получателей:",
                    parse_mode='Markdown',
                    reply_markup=markup
                )
                del self.user_state[user_id]
                return True

            elif state == 'admin_broadcast_link':
                if text.startswith(('http://', 'https://')):
                    self.admin_broadcast_data[user_id]['content'] = text
                    self.admin_broadcast_data[user_id]['caption'] = ''

                    markup = get_gender_filter_keyboard()
                    self.bot.send_message(
                        chat_id,
                        f"✅ *Ссылка сохранена!*\n\n"
                        f"🔗 *Предпросмотр:* {text}\n\n"
                        f"👥 *ФИЛЬТР ПО ПОЛУ*\n\nВыберите пол получателей:",
                        parse_mode='Markdown',
                        reply_markup=markup
                    )
                    del self.user_state[user_id]
                    return True
                else:
                    self.bot.send_message(
                        chat_id,
                        "❌ *Неверный формат ссылки!*\n\n"
                        "Ссылка должна начинаться с http:// или https://\n"
                        "Попробуйте еще раз:",
                        parse_mode='Markdown',
                        reply_markup=get_admin_back_keyboard()
                    )
                    return True

            elif state == 'admin_broadcast_age':
                if text == '0':
                    self.admin_broadcast_data[user_id]['filters']['min_age'] = None
                    self.admin_broadcast_data[user_id]['filters']['max_age'] = None
                else:
                    try:
                        if '-' in text:
                            min_age, max_age = text.split('-')
                            self.admin_broadcast_data[user_id]['filters']['min_age'] = int(
                                min_age.strip())
                            self.admin_broadcast_data[user_id]['filters']['max_age'] = int(
                                max_age.strip())
                        else:
                            self.bot.send_message(
                                chat_id,
                                "❌ *Неверный формат!*\n\n"
                                "Введите возрастной диапазон в формате: 18-30\n"
                                "Или 0 для отключения фильтра:",
                                parse_mode='Markdown',
                                reply_markup=get_admin_back_keyboard()
                            )
                            return
                    except:
                        self.bot.send_message(
                            chat_id,
                            "❌ *Неверный формат!*\n\n"
                            "Введите возрастной диапазон в формате: 18-30\n"
                            "Или 0 для отключения фильтра:",
                            parse_mode='Markdown',
                            reply_markup=get_admin_back_keyboard()
                        )
                        return

                self._save_and_preview_broadcast(user_id, chat_id)
                del self.user_state[user_id]
                return True

        # Поиск пользователя
        if state == 'admin_find_user':
            user_info = AdminService.get_user_full_info(text.strip())

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
🏆 Достижений: {user_info['achievements_count']}

👥 *Реферальная система:*
📊 Приглашено друзей: {user_info['referrals_count']}
🔗 Приглашен: {'Да' if user_info['referred_by'] else 'Нет'}

📅 *Даты:*
📅 Регистрация: {user_info['reg_date'][:10] if user_info['reg_date'] else 'Неизвестно'}
⏰ Последняя активность: {user_info['last_active'] if user_info['last_active'] else 'Неизвестно'}"""

                if user_info['is_banned'] == 1:
                    profile_text += f"\n\n⛔ *Причина блокировки:* {user_info['ban_reason'] or 'Не указана'}"
                    profile_text += f"\n📅 *Дата блокировки:* {user_info['banned_date'][:10] if user_info['banned_date'] else 'Неизвестно'}"

                markup = telebot.types.InlineKeyboardMarkup(row_width=2)

                if user_info['is_banned'] == 1:
                    markup.add(
                        telebot.types.InlineKeyboardButton(
                            "✅ Разблокировать", callback_data=f"admin_unban_{user_info['user_id']}"),
                        telebot.types.InlineKeyboardButton(
                            "📅 События пользователя", callback_data=f"admin_user_events_{user_info['user_id']}")
                    )
                else:
                    markup.add(
                        telebot.types.InlineKeyboardButton(
                            "📊 Полная статистика", callback_data=f"admin_user_stats_{user_info['user_id']}"),
                        telebot.types.InlineKeyboardButton(
                            "📅 События пользователя", callback_data=f"admin_user_events_{user_info['user_id']}")
                    )
                    markup.add(
                        telebot.types.InlineKeyboardButton(
                            "⛔ Заблокировать", callback_data=f"admin_ban_{user_info['user_id']}"),
                        telebot.types.InlineKeyboardButton(
                            "🔍 Новый поиск", callback_data="admin_find_user")
                    )

                markup.add(
                    telebot.types.InlineKeyboardButton(
                        "⬅️ Назад", callback_data="admin_users")
                )

                if user_info.get('photo'):
                    try:
                        self.bot.send_photo(
                            chat_id,
                            user_info['photo'],
                            caption=profile_text,
                            parse_mode='Markdown',
                            reply_markup=markup
                        )
                    except:
                        self.bot.send_message(
                            chat_id, profile_text,
                            parse_mode='Markdown', reply_markup=markup
                        )
                else:
                    self.bot.send_message(
                        chat_id, profile_text + "\n\n📸 *Фото не загружено*",
                        parse_mode='Markdown', reply_markup=markup
                    )
            else:
                markup = telebot.types.InlineKeyboardMarkup()
                markup.add(
                    telebot.types.InlineKeyboardButton(
                        "🔄 Попробовать снова", callback_data="admin_find_user"),
                    telebot.types.InlineKeyboardButton(
                        "⬅️ Назад", callback_data="admin_users")
                )

                self.bot.send_message(
                    chat_id,
                    f"❌ *Пользователь не найден!*\n\n"
                    f"По запросу `{escape_markdown(text)}` ничего не найдено.\n\n"
                    f"*Советы:*\n"
                    f"• Проверьте правильность ID или username\n"
                    f"• Username нужно вводить без @\n"
                    f"• ID должен состоять только из цифр",
                    parse_mode='Markdown',
                    reply_markup=markup
                )

            del self.user_state[user_id]
            return True

        # Блокировка пользователя
        if state and state.startswith('admin_ban_reason_'):
            target_user_id = int(state.replace('admin_ban_reason_', ''))

            if ReportService.ban_user(target_user_id, text, user_id):
                AdminService.log_admin_action(
                    user_id, "ban_user", f"banned: {target_user_id}, reason: {text}"
                )

                markup = telebot.types.InlineKeyboardMarkup()
                markup.add(
                    telebot.types.InlineKeyboardButton(
                        "⬅️ Назад", callback_data="admin_users")
                )

                self.bot.send_message(
                    chat_id,
                    f"✅ *Пользователь ID:{target_user_id} заблокирован!*\n\n"
                    f"Причина: {text}\n\n"
                    f"Его события скрыты от других пользователей.",
                    parse_mode='Markdown',
                    reply_markup=markup
                )

                try:
                    from keyboards.user_keyboards import get_ban_notification_keyboard
                    user_markup = get_ban_notification_keyboard(target_user_id)
                    self.bot.send_message(
                        target_user_id,
                        f"⛔ *Ваш аккаунт заблокирован!*\n\n"
                        f"📝 *Причина:* {text}\n"
                        f"📅 *Дата блокировки:* {datetime.now().strftime('%Y-%m-%d')}\n\n"
                        f"Если вы считаете, что это ошибка, вы можете оспорить блокировку:",
                        parse_mode='Markdown',
                        reply_markup=user_markup
                    )
                except Exception as e:
                    print(
                        f"Ошибка отправки уведомления заблокированному пользователю: {e}")

            else:
                self.bot.send_message(
                    chat_id,
                    f"❌ *Ошибка при блокировке пользователя!*",
                    parse_mode='Markdown',
                    reply_markup=get_admin_back_keyboard()
                )

            del self.user_state[user_id]
            return True

        return False

    def handle_photo(self, message):
        """Обработка фото-сообщений для админов (рассылки)"""
        user_id = message.from_user.id
        chat_id = message.chat.id

        if not AdminService.is_admin(user_id):
            return False

        state = self.user_state.get(user_id)
        if state == 'admin_broadcast_photo':
            photo_id = message.photo[-1].file_id
            caption = getattr(message, "caption", None) or ""

            if user_id not in self.admin_broadcast_data:
                self.admin_broadcast_data[user_id] = {
                    'content_type': 'photo',
                    'filters': {'gender': 'all', 'cities': ['all']}
                }

            self.admin_broadcast_data[user_id]['content_type'] = 'photo'
            self.admin_broadcast_data[user_id]['content'] = photo_id
            self.admin_broadcast_data[user_id]['caption'] = caption

            markup = get_gender_filter_keyboard()
            self.bot.send_message(
                chat_id,
                "✅ *Фото сохранено!*\n\n"
                "👥 *ФИЛЬТР ПО ПОЛУ*\n\nВыберите пол получателей:",
                parse_mode='Markdown',
                reply_markup=markup
            )
            del self.user_state[user_id]
            return True

        return False

    def _save_and_preview_broadcast(self, admin_id, chat_id):
        """Сохраняет рассылку и показывает предпросмотр"""
        if admin_id not in self.admin_broadcast_data:
            self.bot.send_message(chat_id, "❌ Данные рассылки не найдены")
            return

        data = self.admin_broadcast_data[admin_id]

        # Сохраняем в БД
        broadcast_id = execute_query(
            '''INSERT INTO admin_broadcasts 
               (admin_id, content_type, content, caption, filters, created, status) 
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
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

        # Получаем количество пользователей
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
                'with': 'С рефералом',
                'without': 'Без реферала',
                'all': 'Все'
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

        AdminService.log_admin_action(
            admin_id, "broadcast_created", f"ID: {broadcast_id}, Users: {user_count}"
        )
