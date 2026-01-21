# keyboards/admin_keyboards.py
import telebot


def get_admin_main_keyboard():
    """Главное меню админ-панели"""
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton(
            "📊 Статистика", callback_data="admin_stats"),
        telebot.types.InlineKeyboardButton(
            "📨 Рассылка", callback_data="admin_broadcast")
    )
    markup.add(
        telebot.types.InlineKeyboardButton(
            "👥 Пользователи", callback_data="admin_users"),
        telebot.types.InlineKeyboardButton(
            "🚨 Жалобы", callback_data="admin_reports")
    )
    return markup


def get_broadcast_type_keyboard():
    """Выбор типа рассылки"""
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton(
            "📝 Текст", callback_data="broadcast_type_text"),
        telebot.types.InlineKeyboardButton(
            "🖼️ Фото", callback_data="broadcast_type_photo")
    )
    markup.add(
        telebot.types.InlineKeyboardButton(
            "🎥 Видео", callback_data="broadcast_type_video"),
        telebot.types.InlineKeyboardButton(
            "📎 Документ", callback_data="broadcast_type_document")
    )
    markup.add(
        telebot.types.InlineKeyboardButton(
            "🎵 Аудио", callback_data="broadcast_type_audio"),
        telebot.types.InlineKeyboardButton(
            "🔗 Ссылка", callback_data="broadcast_type_link")
    )
    markup.add(
        telebot.types.InlineKeyboardButton(
            "⬅️ Назад", callback_data="admin_back")
    )
    return markup


def get_gender_filter_keyboard(action_prefix="broadcast_filter"):
    """Выбор фильтра по полу"""
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton(
            "👨 Мужчины", callback_data=f"{action_prefix}_gender_Мужской"),
        telebot.types.InlineKeyboardButton(
            "👩 Женщины", callback_data=f"{action_prefix}_gender_Женский")
    )
    markup.add(
        telebot.types.InlineKeyboardButton(
            "⚧️ Другие", callback_data=f"{action_prefix}_gender_Другой"),
        telebot.types.InlineKeyboardButton(
            "👥 Все", callback_data=f"{action_prefix}_gender_all")
    )
    markup.add(
        telebot.types.InlineKeyboardButton(
            "✅ Готово", callback_data=f"{action_prefix}_gender_done"),
        telebot.types.InlineKeyboardButton(
            "⬅️ Назад", callback_data=f"{action_prefix}_back")
    )
    return markup


def get_city_filter_keyboard(action_prefix="broadcast_filter"):
    """Выбор фильтра по городам"""
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)

    popular_cities = ["Москва", "Санкт-Петербург",
                      "Новосибирск", "Екатеринбург", "Казань"]
    for city in popular_cities:
        markup.add(telebot.types.InlineKeyboardButton(
            city, callback_data=f"{action_prefix}_city_{city}"))

    markup.add(
        telebot.types.InlineKeyboardButton(
            "🌍 Все города", callback_data=f"{action_prefix}_city_all"),
        telebot.types.InlineKeyboardButton(
            "✅ Готово", callback_data=f"{action_prefix}_city_done")
    )
    markup.add(
        telebot.types.InlineKeyboardButton(
            "⬅️ Назад", callback_data=f"{action_prefix}_back")
    )
    return markup


def get_referral_filter_keyboard(action_prefix="broadcast_filter"):
    """Выбор фильтра по рефералам"""
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton(
            "🔗 С рефералом", callback_data=f"{action_prefix}_referral_with"),
        telebot.types.InlineKeyboardButton(
            "🚫 Без реферала", callback_data=f"{action_prefix}_referral_without")
    )
    markup.add(
        telebot.types.InlineKeyboardButton(
            "👥 Все", callback_data=f"{action_prefix}_referral_all"),
        telebot.types.InlineKeyboardButton(
            "✅ Готово", callback_data=f"{action_prefix}_referral_done")
    )
    markup.add(
        telebot.types.InlineKeyboardButton(
            "⬅️ Назад", callback_data=f"{action_prefix}_back")
    )
    return markup


def get_broadcast_confirm_keyboard(broadcast_id):
    """Подтверждение рассылки"""
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton(
            "✅ Отправить", callback_data=f"broadcast_confirm_{broadcast_id}"),
        telebot.types.InlineKeyboardButton(
            "✏️ Редактировать", callback_data=f"broadcast_edit_{broadcast_id}")
    )
    markup.add(
        telebot.types.InlineKeyboardButton(
            "🗑️ Удалить", callback_data=f"broadcast_delete_{broadcast_id}"),
        telebot.types.InlineKeyboardButton(
            "⬅️ Назад", callback_data="admin_broadcast")
    )
    return markup


def get_admin_back_keyboard():
    """Кнопка назад в админ-панель"""
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(
        "⬅️ Назад", callback_data="admin_back"))
    return markup
