# services/achievements.py
from datetime import datetime
import json
from database import execute_query
from config import config


class AchievementService:
    @staticmethod
    def update_user_points(user_id: int, points_to_add: int, reason: str = "") -> None:
        """Обновление очков пользователя"""
        from services.notifications import NotificationService

        # Проверяем бан
        user = execute_query(
            "SELECT is_banned FROM users WHERE user_id = ?",
            (user_id,), fetchone=True
        )

        if user and user['is_banned'] == 1:
            return

        execute_query(
            "UPDATE users SET points = points + ? WHERE user_id = ?",
            (points_to_add, user_id), commit=True
        )

        user = execute_query(
            "SELECT points FROM users WHERE user_id = ?",
            (user_id,), fetchone=True
        )

        if user:
            AchievementService.check_achievements(user_id, user['points'])

        if reason:
            NotificationService.send_points_notification(
                user_id, points_to_add, reason)

    @staticmethod
    def check_achievements(user_id: int, current_points: int = None) -> None:
        """Проверка и разблокировка достижений"""
        if current_points is None:
            user = execute_query(
                "SELECT points FROM users WHERE user_id = ?",
                (user_id,), fetchone=True
            )
            current_points = user['points'] if user else 0

        # Получаем статистику пользователя
        events_count = execute_query(
            "SELECT COUNT(*) as count FROM events WHERE user_id = ? AND is_hidden = FALSE",
            (user_id,), fetchone=True
        )['count']

        likes_received = execute_query(
            "SELECT COUNT(*) as count FROM likes WHERE to_user = ?",
            (user_id,), fetchone=True
        )['count']

        mutual_count = execute_query(
            "SELECT COUNT(*) as count FROM likes WHERE to_user = ? AND mutual = TRUE",
            (user_id,), fetchone=True
        )['count']

        # Проверяем достижения
        achievements_to_check = [
            ("first_event", events_count >= 1),
            ("five_likes", likes_received >= 5),
            ("mutual_match", mutual_count >= 1),
            ("organizer", events_count >= 10),
            ("socializer", likes_received >= 50)
        ]

        for achievement_id, condition in achievements_to_check:
            if condition:
                AchievementService.unlock_achievement(user_id, achievement_id)

    @staticmethod
    def unlock_achievement(user_id: int, achievement_id: str) -> None:
        """Разблокировка достижения"""
        from services.notifications import NotificationService

        # Проверяем бан
        user = execute_query(
            "SELECT is_banned FROM users WHERE user_id = ?",
            (user_id,), fetchone=True
        )

        if user and user['is_banned'] == 1:
            return

        # Проверяем, не получено ли уже достижение
        existing = execute_query(
            "SELECT id FROM achievements WHERE user_id = ? AND achievement_id = ?",
            (user_id, achievement_id), fetchone=True
        )

        if not existing and achievement_id in config.ACHIEVEMENTS:
            # Сохраняем достижение
            execute_query(
                "INSERT INTO achievements (user_id, achievement_id, unlocked_date) VALUES (?, ?, ?)",
                (user_id, achievement_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                commit=True
            )

            achievement = config.ACHIEVEMENTS[achievement_id]
            points_to_add = achievement.get('points', 0)

            # Начисляем очки
            if points_to_add > 0:
                AchievementService.update_user_points(
                    user_id, points_to_add, f"Достижение: {achievement['name']}"
                )

            # Отправляем уведомление
            NotificationService.send_achievement_notification(
                user_id, achievement)

    @staticmethod
    def get_user_achievements(user_id: int) -> list:
        """Получить достижения пользователя"""
        achievements = execute_query(
            "SELECT a.achievement_id, a.unlocked_date FROM achievements a WHERE a.user_id = ?",
            (user_id,), fetchall=True
        )

        result = []
        for ach in achievements:
            if ach['achievement_id'] in config.ACHIEVEMENTS:
                achievement_data = config.ACHIEVEMENTS[ach['achievement_id']]
                result.append({
                    'id': ach['achievement_id'],
                    'name': achievement_data['name'],
                    'description': achievement_data['description'],
                    'emoji': achievement_data['emoji'],
                    'unlocked_date': ach['unlocked_date'],
                    'points': achievement_data.get('points', 0)
                })

        return result
