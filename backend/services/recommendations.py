# services/recommendations.py
import json
from database import execute_query
from config import config


class RecommendationService:
    @staticmethod
    def get_recommendations(user_id, limit=5):
        """Получить рекомендации для пользователя"""
        # Получаем предпочтения пользователя
        prefs = execute_query(
            "SELECT liked_categories FROM user_preferences WHERE user_id = ?",
            (user_id,), fetchone=True
        )

        if prefs and prefs['liked_categories']:
            try:
                liked_categories = json.loads(prefs['liked_categories'])
            except:
                liked_categories = []
        else:
            liked_categories = []

        # Получаем категории созданных пользователем событий
        user_events = execute_query(
            '''SELECT category FROM events 
               WHERE user_id = ? AND category IS NOT NULL AND is_hidden = FALSE''',
            (user_id,), fetchall=True
        )

        user_categories = [event['category']
                           for event in user_events if event['category']]

        # Объединяем предпочтения
        preferred_categories = list(set(liked_categories + user_categories))

        if not preferred_categories:
            # Если нет предпочтений, показываем случайные события
            recommendations = execute_query(
                '''SELECT e.id, e.user_id, e.title, e.description, e.event_date, e.target_gender, e.city, e.category, e.photo AS event_photo, e.created, e.is_hidden,
                          u.name, u.age, u.gender, u.photo AS user_photo
                    FROM events e 
                    JOIN users u ON e.user_id = u.user_id 
                    WHERE (e.event_date::timestamp) > NOW()
                    AND e.user_id != ?
                    AND e.is_hidden = FALSE
                    AND u.is_banned = FALSE
                    ORDER BY RANDOM() 
                    LIMIT ?''',
                (user_id, limit), fetchall=True
            )
        else:
            # Показываем события из предпочитаемых категорий
            placeholders = ','.join(['?'] * len(preferred_categories))
            query = f'''SELECT e.id, e.user_id, e.title, e.description, e.event_date, e.target_gender, e.city, e.category, e.photo AS event_photo, e.created, e.is_hidden,
                          u.name, u.age, u.gender, u.photo AS user_photo
                    FROM events e 
                    JOIN users u ON e.user_id = u.user_id 
                    WHERE (e.event_date::timestamp) > NOW()
                    AND e.user_id != ?
                    AND e.category IN ({placeholders})
                    AND e.is_hidden = FALSE
                    AND u.is_banned = FALSE
                    ORDER BY e.created DESC 
                    LIMIT ?'''

            params = [user_id] + preferred_categories + [limit]
            recommendations = execute_query(query, params, fetchall=True)

        return recommendations

    @staticmethod
    def get_events_by_filter(user_id, filter_type, limit=10):
        """Получить события по фильтру"""
        current_user = execute_query(
            "SELECT gender, city FROM users WHERE user_id=?", (user_id,), fetchone=True
        )

        if not current_user:
            return []

        current_gender = current_user['gender']
        current_city = current_user['city']

        base_query = '''
            SELECT e.id, e.user_id, e.title, e.description, e.event_date, e.target_gender, e.city, e.category, e.photo AS event_photo, e.created, e.is_hidden,
                   u.name, u.age, u.gender, u.relationship_status, u.photo AS user_photo, u.purpose
            FROM events e 
            JOIN users u ON e.user_id = u.user_id 
            WHERE (e.event_date::timestamp) > NOW()
            AND e.user_id != ?
            AND e.id NOT IN (SELECT event_id FROM likes WHERE from_user = ?)
            AND e.is_hidden = FALSE
            AND u.is_banned = FALSE
        '''

        params = [user_id, user_id]

        if filter_type == 'today':
            query = base_query + " AND (e.event_date::date) = CURRENT_DATE "
        elif filter_type == 'tomorrow':
            query = base_query + \
                " AND (e.event_date::date) = CURRENT_DATE + INTERVAL '1 day' "
        elif filter_type == 'for_me':
            query = base_query + '''
                AND (e.target_gender = 'Все' OR 
                     (e.target_gender = 'Мужчины' AND ? = 'Мужской') OR
                     (e.target_gender = 'Женщины' AND ? = 'Женский'))
                AND e.city = ?
            '''
            params.extend([current_gender, current_gender, current_city])
        elif filter_type == 'popular':
            query = '''
                SELECT e.id, e.user_id, e.title, e.description, e.event_date, e.target_gender, e.city, e.category, e.photo AS event_photo, e.created, e.is_hidden,
                       u.name, u.age, u.gender, u.relationship_status, u.photo AS user_photo, u.purpose,
                       COUNT(l.id) as likes_count
                FROM events e 
                JOIN users u ON e.user_id = u.user_id 
                LEFT JOIN likes l ON e.id = l.event_id
                WHERE (e.event_date::timestamp) > NOW()
                AND e.user_id != ?
                AND e.id NOT IN (SELECT event_id FROM likes WHERE from_user = ?)
                AND e.is_hidden = FALSE
                AND u.is_banned = FALSE
                GROUP BY e.id, e.user_id, e.title, e.description, e.event_date, e.target_gender, e.city, e.category, e.photo, e.created, e.is_hidden, u.name, u.age, u.gender, u.relationship_status, u.photo, u.purpose
                ORDER BY likes_count DESC
            '''
        elif filter_type == 'nearby':
            query = base_query + " AND e.city = ? "
            params.append(current_city)
        elif filter_type == 'new':
            query = base_query
        elif filter_type == 'random':
            query = base_query
        else:
            query = base_query

        if filter_type != 'popular':
            if filter_type == 'random':
                query += " ORDER BY RANDOM() "
            elif filter_type == 'new':
                query += " ORDER BY e.created DESC "
            else:
                query += " ORDER BY e.event_date ASC "

        query += " LIMIT ?"
        params.append(limit)

        return execute_query(query, params, fetchall=True)
