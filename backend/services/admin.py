# services/admin.py
from datetime import datetime, timedelta
from database import execute_query
from config import config
from utils.helpers import escape_markdown


class AdminService:
    @staticmethod
    def is_admin(user_id):
        """Проверяет, является ли пользователь админом"""
        return user_id in config.ADMINS

    @staticmethod
    def log_admin_action(admin_id, action, details=""):
        """Логирует действия админов"""
        execute_query(
            "INSERT INTO admin_logs (admin_id, action, details, created) VALUES (?, ?, ?, ?)",
            (admin_id, action, details, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            commit=True
        )

    @staticmethod
    def _count(query, params=None):
        """Безопасно возвращает count из fetchone (0 если нет строки)."""
        row = execute_query(query, params or (), fetchone=True)
        return (row.get("count") or 0) if row else 0

    @staticmethod
    def _total(query, params=None):
        """Безопасно возвращает total/sum из fetchone (0 если нет строки или NULL)."""
        row = execute_query(query, params or (), fetchone=True)
        return (row.get("total") or 0) if row else 0

    @staticmethod
    def get_admin_stats():
        """Получает полную статистику для админ-панели"""
        stats = {}

        stats['total_users'] = AdminService._count(
            "SELECT COUNT(*) as count FROM users WHERE is_banned = FALSE"
        )
        stats['banned_users'] = AdminService._count(
            "SELECT COUNT(*) as count FROM users WHERE is_banned = TRUE"
        )
        stats['gender_stats'] = execute_query(
            "SELECT gender, COUNT(*) as count FROM users WHERE is_banned = FALSE GROUP BY gender",
            fetchall=True
        ) or []

        today = datetime.now().strftime("%Y-%m-%d")
        stats['new_users_today'] = AdminService._count(
            "SELECT COUNT(*) as count FROM users WHERE DATE(reg_date::timestamp) = ? AND is_banned = FALSE",
            (today,)
        )

        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        stats['active_users_week'] = AdminService._count(
            "SELECT COUNT(*) as count FROM users WHERE last_active >= ? AND is_banned = FALSE",
            (week_ago,)
        )

        stats['total_events'] = AdminService._count(
            "SELECT COUNT(*) as count FROM events WHERE is_hidden = FALSE"
        )
        stats['active_events'] = AdminService._count(
            "SELECT COUNT(*) as count FROM events WHERE event_date > NOW() AND is_hidden = FALSE"
        )
        stats['hidden_events'] = AdminService._count(
            "SELECT COUNT(*) as count FROM events WHERE is_hidden = TRUE"
        )

        stats['referral_users'] = AdminService._count(
            "SELECT COUNT(*) as count FROM users WHERE referred_by IS NOT NULL AND is_banned = FALSE"
        )
        stats['total_referrals'] = AdminService._total(
            "SELECT SUM(referrals_count) as total FROM users WHERE is_banned = FALSE"
        )

        stats['top_referrers'] = execute_query(
            "SELECT name, referrals_count FROM users WHERE referrals_count > 0 AND is_banned = FALSE ORDER BY referrals_count DESC LIMIT 5",
            fetchall=True
        ) or []
        stats['top_cities'] = execute_query(
            "SELECT city, COUNT(*) as count FROM users WHERE city IS NOT NULL AND city != '' AND is_banned = FALSE GROUP BY city ORDER BY count DESC LIMIT 5",
            fetchall=True
        ) or []

        stats['total_likes'] = AdminService._count("SELECT COUNT(*) as count FROM likes")
        stats['mutual_likes'] = AdminService._count(
            "SELECT COUNT(*) as count FROM likes WHERE mutual = TRUE"
        )
        stats['total_points'] = AdminService._total(
            "SELECT SUM(points) as total FROM users WHERE is_banned = FALSE"
        )

        hour_ago = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        stats['online_now'] = AdminService._count(
            "SELECT COUNT(*) as count FROM users WHERE last_active >= ? AND is_banned = FALSE",
            (hour_ago,)
        )

        stats['total_reports'] = AdminService._count("SELECT COUNT(*) as count FROM reports")
        stats['pending_reports'] = AdminService._count(
            "SELECT COUNT(*) as count FROM reports WHERE status = 'pending'"
        )
        stats['pending_appeals'] = AdminService._count(
            "SELECT COUNT(*) as count FROM reports WHERE appeal_status = 'pending'"
        )

        return stats

    @staticmethod
    def format_stats_message(stats):
        """Форматирует статистику в читаемое сообщение"""
        gender_dict = {}
        for row in stats['gender_stats']:
            gender_dict[row['gender']] = row['count']

        message = "📊 *АДМИН СТАТИСТИКА*\n\n"

        message += "👥 *ПОЛЬЗОВАТЕЛИ:*\n"
        message += f"• Всего: {stats['total_users']:,}\n"
        message += f"• Заблокировано: {stats['banned_users']}\n"
        message += f"• Новые (сегодня): {stats['new_users_today']}\n"
        message += f"• Активные (за 7 дней): {stats['active_users_week']}\n"
        message += f"• Онлайн сейчас: ~{stats['online_now']}\n\n"

        message += "👨‍👩‍👧‍👦 *ПОЛ:*\n"
        message += f"• Мужчины: {gender_dict.get('Мужской', 0)} ({gender_dict.get('Мужской', 0)/stats['total_users']*100:.1f}%)\n"
        message += f"• Женщины: {gender_dict.get('Женский', 0)} ({gender_dict.get('Женский', 0)/stats['total_users']*100:.1f}%)\n"
        message += f"• Другие: {gender_dict.get('Другой', 0)} ({gender_dict.get('Другой', 0)/stats['total_users']*100:.1f}%)\n\n"

        message += "🎉 *СОБЫТИЯ:*\n"
        message += f"• Всего создано: {stats['total_events']}\n"
        message += f"• Активных: {stats['active_events']}\n"
        message += f"• Скрыто (забанено): {stats['hidden_events']}\n"
        if stats['total_users'] > 0:
            message += f"• Среднее на пользователя: {stats['total_events']/stats['total_users']:.2f}\n\n"
        else:
            message += "• Среднее на пользователя: 0\n\n"

        message += "❤️ *ЛАЙКИ:*\n"
        message += f"• Всего лайков: {stats['total_likes']}\n"
        message += f"• Взаимных симпатий: {stats['mutual_likes']}\n\n"

        message += "👥 *РЕФЕРАЛЫ:*\n"
        if stats['total_users'] > 0:
            message += f"• Пришли по ссылкам: {stats['referral_users']} ({stats['referral_users']/stats['total_users']*100:.1f}%)\n"
        else:
            message += "• Пришли по ссылкам: 0 (0%)\n"
        message += f"• Всего приглашено: {stats['total_referrals']}\n\n"

        message += "📍 *ТОП-5 ГОРОДОВ:*\n"
        for i, city in enumerate(stats['top_cities'], 1):
            message += f"{i}. {city['city']}: {city['count']}\n"
        message += "\n"

        message += "🏆 *ТОП-5 РЕФЕРЕРОВ:*\n"
        if stats['top_referrers']:
            for i, ref in enumerate(stats['top_referrers'], 1):
                message += f"{i}. {ref['name']}: {ref['referrals_count']}\n"
        else:
            message += "Пока нет активных рефереров\n"
        message += "\n"

        message += "💰 *БАЛЛЫ:*\n"
        message += f"• Всего в системе: {stats['total_points']:,}\n"
        if stats['total_users'] > 0:
            message += f"• Среднее на пользователя: {stats['total_points']/stats['total_users']:.1f}\n\n"
        else:
            message += "• Среднее на пользователя: 0\n\n"

        message += "🚨 *ЖАЛОБЫ И АПЕЛЛЯЦИИ:*\n"
        message += f"• Всего жалоб: {stats['total_reports']}\n"
        message += f"• Ожидают рассмотрения: {stats['pending_reports']}\n"
        message += f"• Ожидают апелляции: {stats['pending_appeals']}"

        return message

    @staticmethod
    def get_user_full_info(user_identifier):
        """Получает полную информацию о пользователе по ID или username"""
        try:
            if user_identifier.isdigit():
                query = """SELECT u.user_id, u.username, u.name, u.age, u.gender, u.city, 
                                  u.relationship_status, u.photo, u.purpose, u.points, 
                                  u.reg_date, u.last_active, u.referrals_count, u.referred_by,
                                  u.is_banned, u.ban_reason, u.banned_date,
                                  COUNT(DISTINCT e.id) as events_count,
                                  COUNT(DISTINCT l1.id) as likes_received,
                                  COUNT(DISTINCT l2.id) as likes_given,
                                  COUNT(DISTINCT l3.id) as mutual_likes,
                                  COUNT(DISTINCT a.id) as achievements_count
                           FROM users u
                           LEFT JOIN events e ON u.user_id = e.user_id AND e.is_hidden = FALSE
                           LEFT JOIN likes l1 ON u.user_id = l1.to_user
                           LEFT JOIN likes l2 ON u.user_id = l2.from_user
                           LEFT JOIN likes l3 ON u.user_id = l3.to_user AND l3.mutual = TRUE
                           LEFT JOIN achievements a ON u.user_id = a.user_id
                           WHERE u.user_id = ?
                           GROUP BY u.user_id"""
                user = execute_query(
                    query, (int(user_identifier),), fetchone=True)
            else:
                username = user_identifier.lstrip('@')
                query = """SELECT u.user_id, u.username, u.name, u.age, u.gender, u.city, 
                                  u.relationship_status, u.photo, u.purpose, u.points, 
                                  u.reg_date, u.last_active, u.referrals_count, u.referred_by,
                                  u.is_banned, u.ban_reason, u.banned_date,
                                  COUNT(DISTINCT e.id) as events_count,
                                  COUNT(DISTINCT l1.id) as likes_received,
                                  COUNT(DISTINCT l2.id) as likes_given,
                                  COUNT(DISTINCT l3.id) as mutual_likes,
                                  COUNT(DISTINCT a.id) as achievements_count
                           FROM users u
                           LEFT JOIN events e ON u.user_id = e.user_id AND e.is_hidden = FALSE
                           LEFT JOIN likes l1 ON u.user_id = l1.to_user
                           LEFT JOIN likes l2 ON u.user_id = l2.from_user
                           LEFT JOIN likes l3 ON u.user_id = l3.to_user AND l3.mutual = TRUE
                           LEFT JOIN achievements a ON u.user_id = a.user_id
                           WHERE u.username = ?
                           GROUP BY u.user_id"""
                user = execute_query(query, (username,), fetchone=True)

            return user
        except Exception as e:
            print(f"Ошибка в get_user_full_info: {e}")
            return None
