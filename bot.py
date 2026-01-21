# bot.py
import telebot
from config import config
from handlers.user_handlers import UserHandlers
from handlers.event_handlers import EventHandlers
from handlers.admin_handlers import AdminHandlers
from handlers.callback_handlers import CallbackHandler
from database import db
from services.admin import AdminService


class DatingBot:
    def __init__(self):
        self.bot = telebot.TeleBot(config.BOT_TOKEN)
        # Общие состояния между callback и текстовыми сообщениями
        shared_user_state = {}
        shared_user_data = {}

        self.user_handlers = UserHandlers(self.bot, shared_user_state, shared_user_data)
        self.event_handlers = EventHandlers(self.bot)
        self.admin_handlers = AdminHandlers(self.bot)
        self.callback_handler = CallbackHandler(
            self.bot,
            admin_handlers=self.admin_handlers,
            user_handlers=self.user_handlers,
            shared_user_state=shared_user_state,
            shared_user_data=shared_user_data
        )

        self._register_handlers()

    def _register_handlers(self):
        """Регистрация обработчиков"""

        # Команды
        @self.bot.message_handler(commands=['start'])
        def handle_start(message):
            self.user_handlers.handle_start(message)

        @self.bot.message_handler(commands=['admin'])
        def handle_admin(message):
            self.admin_handlers.handle_admin(message)

        @self.bot.message_handler(commands=['stats'])
        def handle_stats(message):
            self.admin_handlers.handle_stats(message)

        @self.bot.message_handler(commands=['ref'])
        def handle_ref(message):
            self.user_handlers._show_referral_info(message)

        @self.bot.message_handler(commands=['help'])
        def handle_help(message):
            self.user_handlers.show_about_bot(message)

        # Текстовые сообщения
        @self.bot.message_handler(func=lambda m: True, content_types=['text'])
        def handle_text(message):
            # Админские сценарии должны обрабатываться первым делом,
            # иначе теряются состояния админ-панели (поиск, бан, рассылки).
            if AdminService.is_admin(message.from_user.id):
                handled = self.admin_handlers.handle_text(message)
                if handled:
                    return
            self.user_handlers.handle_text(message)

        # Фото
        @self.bot.message_handler(content_types=['photo'])
        def handle_photo(message):
            if AdminService.is_admin(message.from_user.id):
                handled = self.admin_handlers.handle_photo(message)
                if handled:
                    return
            self.user_handlers.handle_photo(message)

        # Callback запросы
        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_callback(call):
            self.callback_handler.handle(call)

    def run(self):
        """Запуск бота"""
        # На Windows консоль часто в cp1251/cp866 и не поддерживает emoji → избегаем их в логах.
        print("=" * 60)
        print("BOT STARTED")
        print("=" * 60)
        print("ADMIN PANEL: ENABLED")
        print("REPORTS/BANS: ENABLED")
        print("=" * 60)
        print("ADMIN COMMANDS:")
        print("- /admin - Admin panel menu")
        print("- /stats - Detailed stats")
        print("- Broadcasts with filters")
        print("- User search by ID/username")
        print("- Reports and bans system")
        print("=" * 60)
        print("ADMINS:", config.ADMINS)
        print("=" * 60)
        print("Press Ctrl+C to stop")
        print("=" * 60)

        try:
            self.bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            print(f"Ошибка в работе бота: {e}")
            import traceback
            traceback.print_exc()
            import time
            time.sleep(5)


if __name__ == "__main__":
    bot = DatingBot()
    bot.run()
