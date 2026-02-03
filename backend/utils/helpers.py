# utils/helpers.py
import random
import string


def escape_markdown(text):
    """Экранирование символов Markdown"""
    if not text:
        return ""
    chars_to_escape = ['_', '*', '[', ']',
                       '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in chars_to_escape:
        text = text.replace(char, f'\\{char}')
    return text


def find_similar_city(input_city, cities_list):
    """Найти наиболее похожий город из списка"""
    input_city = input_city.lower().strip()

    for city in cities_list:
        if city.lower() == input_city:
            return city

    for city in cities_list:
        if input_city in city.lower() or city.lower() in input_city:
            return city

    for city in cities_list:
        if city.lower().startswith(input_city[:3]):
            return city

    return None


def generate_referral_code():
    """Генерирует уникальный реферальный код"""
    characters = string.ascii_uppercase + string.digits
    code = 'REF_' + ''.join(random.choices(characters, k=8))

    from database import execute_query
    existing = execute_query(
        "SELECT user_id FROM users WHERE referral_code = ?",
        (code,), fetchone=True
    )

    while existing:
        code = 'REF_' + ''.join(random.choices(characters, k=8))
        existing = execute_query(
            "SELECT user_id FROM users WHERE referral_code = ?",
            (code,), fetchone=True
        )

    return code
