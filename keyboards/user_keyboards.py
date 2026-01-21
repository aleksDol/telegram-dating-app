# keyboards/user_keyboards.py
import telebot
from config import config


def get_main_menu():
    """Главное меню пользователя"""
    markup = telebot.types.ReplyKeyboardMarkup(
        resize_keyboard=True, row_width=2)
    markup.add(
        '👤 Мой профиль', '🔍 Найти события',
        '📅 Мои события', '🎉 Создать событие',
        '⭐ Рекомендации', '🏆 Достижения',
        'ℹ️ О боте'
    )
    return markup


def get_category_keyboard():
    """Клавиатура для выбора категории события"""
    markup = telebot.types.ReplyKeyboardMarkup(
        resize_keyboard=True, row_width=2)
    categories = list(config.EVENT_CATEGORIES.keys())

    for i in range(0, len(categories), 2):
        row = categories[i:i+2]
        markup.add(*row)

    markup.add('🎯 Без категории', '⬅️ Назад')
    return markup


def get_gender_keyboard():
    """Клавиатура для выбора пола"""
    markup = telebot.types.ReplyKeyboardMarkup(
        resize_keyboard=True, row_width=2)
    markup.add('Мужской', 'Женский', 'Другой')
    return markup


def get_target_gender_keyboard():
    """Клавиатура для выбора целевой аудитории события"""
    markup = telebot.types.ReplyKeyboardMarkup(
        resize_keyboard=True, row_width=2)
    markup.add('Все', 'Мужчины', 'Женщины')
    return markup


def get_relationship_keyboard():
    """Клавиатура для выбора статуса отношений"""
    markup = telebot.types.ReplyKeyboardMarkup(
        resize_keyboard=True, row_width=2)
    markup.add('Не в отношениях', 'В отношениях', 'В браке', 'Всё сложно')
    return markup


def get_profile_menu():
    """Меню редактирования профиля"""
    markup = telebot.types.ReplyKeyboardMarkup(
        resize_keyboard=True, row_width=2)
    markup.add(
        '✏️ Изменить имя', '✏️ Изменить возраст',
        '✏️ Изменить пол', '✏️ Изменить город',
        '✏️ Изменить статус', '✏️ Изменить фото',
        '✏️ Изменить цель', '⬅️ Назад'
    )
    return markup


def get_filter_keyboard():
    """Клавиатура фильтров поиска"""
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton(
            "🎯 По интересам", callback_data="filter_interest"),
        telebot.types.InlineKeyboardButton(
            "🔥 Популярные", callback_data="filter_popular")
    )
    markup.add(
        telebot.types.InlineKeyboardButton(
            "📍 Ближайшие", callback_data="filter_nearby"),
        telebot.types.InlineKeyboardButton(
            "🆕 Новые", callback_data="filter_new")
    )
    markup.add(
        telebot.types.InlineKeyboardButton(
            "📅 Сегодня", callback_data="filter_today"),
        telebot.types.InlineKeyboardButton(
            "📅 Завтра", callback_data="filter_tomorrow")
    )
    markup.add(
        telebot.types.InlineKeyboardButton(
            "👥 Для меня", callback_data="filter_for_me"),
        telebot.types.InlineKeyboardButton(
            "🔀 Случайные", callback_data="filter_random")
    )
    return markup


def get_yes_no_keyboard():
    """Клавиатура Да/Нет"""
    markup = telebot.types.ReplyKeyboardMarkup(
        resize_keyboard=True, row_width=2)
    markup.add('✅ Да', '❌ Нет')
    return markup


def get_event_action_keyboard(event_id, can_edit=True):
    """Клавиатура для действий с событием"""
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)

    if can_edit:
        markup.add(
            telebot.types.InlineKeyboardButton(
                "✏️ Редактировать", callback_data=f"edit_event_{event_id}"),
            telebot.types.InlineKeyboardButton(
                "🗑️ Удалить", callback_data=f"delete_event_{event_id}")
        )

    markup.add(
        telebot.types.InlineKeyboardButton(
            "📋 Мои события", callback_data="my_events_list"),
        telebot.types.InlineKeyboardButton(
            "⬅️ Назад", callback_data="back_to_profile")
    )

    return markup


def get_event_edit_keyboard(event_id):
    """Клавиатура для редактирования события"""
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton(
            "📝 Название", callback_data=f"edit_title_{event_id}"),
        telebot.types.InlineKeyboardButton(
            "📄 Описание", callback_data=f"edit_desc_{event_id}")
    )
    markup.add(
        telebot.types.InlineKeyboardButton(
            "📅 Дата", callback_data=f"edit_date_{event_id}"),
        telebot.types.InlineKeyboardButton(
            "👥 Для кого", callback_data=f"edit_target_{event_id}")
    )
    markup.add(
        telebot.types.InlineKeyboardButton(
            "🏙️ Город", callback_data=f"edit_event_city_{event_id}"),
        telebot.types.InlineKeyboardButton(
            "🏷️ Категория", callback_data=f"edit_category_{event_id}")
    )
    markup.add(
        telebot.types.InlineKeyboardButton(
            "❌ Отмена", callback_data=f"cancel_edit_{event_id}")
    )
    return markup


def get_event_navigation_keyboard(event_id, total_events, current_index, category=None,
                                  is_search=False, show_organizer_profile=False, organizer_id=None):
    """Клавиатура для навигации по событиям"""
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)

    markup.add(
        telebot.types.InlineKeyboardButton(
            "❤️ Лайк", callback_data=f"like_{event_id}"),
        telebot.types.InlineKeyboardButton(
            "➡️ Пропустить", callback_data=f"skip_{event_id}")
    )

    if category:
        markup.add(
            telebot.types.InlineKeyboardButton(
                f"👍 Нравится {category}", callback_data=f"like_cat_{category}"),
            telebot.types.InlineKeyboardButton(
                f"👎 Не нравится {category}", callback_data=f"dislike_cat_{category}")
        )

    if show_organizer_profile and organizer_id:
        markup.add(
            telebot.types.InlineKeyboardButton(
                "🚨 Пожаловаться на организатора", callback_data=f"report_organizer_{event_id}")
        )

    if current_index < total_events - 1 and is_search:
        markup.add(
            telebot.types.InlineKeyboardButton(
                "⏭️ Следующее событие", callback_data=f"next_{current_index+1}")
        )

    return markup


def get_user_profile_keyboard(viewed_user_id, current_user_id, can_report=True):
    """Клавиатура для просмотра профиля пользователя"""
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)

    if viewed_user_id != current_user_id:
        markup.add(
            telebot.types.InlineKeyboardButton(
                "❤️ Лайкнуть", callback_data=f"like_user_{viewed_user_id}"),
        )

        if can_report:
            markup.add(
                telebot.types.InlineKeyboardButton(
                    "🚨 Пожаловаться", callback_data=f"report_user_{viewed_user_id}")
            )

    if current_user_id == viewed_user_id:
        markup.add(
            telebot.types.InlineKeyboardButton(
                "✏️ Редактировать", callback_data="edit_profile"),
            telebot.types.InlineKeyboardButton(
                "🔍 Новый поиск", callback_data="new_search")
        )

    return markup


def get_ban_notification_keyboard(user_id):
    """Клавиатура для уведомления о блокировке"""
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton(
            "📝 Оспорить блокировку", callback_data=f"appeal_ban_{user_id}")
    )
    return markup


def get_mutual_notification_keyboard(like_id):
    """Клавиатура для уведомления о лайке"""
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton(
            "❤️ Ответить взаимностью", callback_data=f"mutual_{like_id}"),
        telebot.types.InlineKeyboardButton(
            "➡️ Пропустить", callback_data=f"ignore_{like_id}")
    )
    return markup
