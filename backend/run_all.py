#!/usr/bin/env python3
"""
Запуск всего бэкенда одной командой: REST API (uvicorn) + Telegram-бот.
Использование: из папки backend выполнить
    python run_all.py
"""
import logging
import os
import sys
import threading

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)

# Порт API: на Render используется PORT, локально — API_PORT или 8000
API_HOST = os.getenv("API_HOST", "0.0.0.0")
_port = os.getenv("PORT") or os.getenv("API_PORT") or "8000"
API_PORT = int(str(_port).strip())


def run_api():
    """Запуск FastAPI через uvicorn в текущем потоке."""
    import uvicorn
    uvicorn.run(
        "api:app",
        host=API_HOST,
        port=API_PORT,
        log_level="info",
    )


def run_bot():
    """Запуск Telegram-бота в текущем потоке."""
    try:
        from bot import DatingBot
        bot = DatingBot()
        bot.run()
    except Exception as e:
        logging.getLogger(__name__).exception("Бот завершился с ошибкой: %s", e)
        raise


def main():
    print("=" * 60)
    print("BACKEND: API + BOT (single command)")
    print("=" * 60)
    print(f"API:  http://{API_HOST}:{API_PORT}")
    print("BOT:  polling...")
    print("=" * 60)
    print("Press Ctrl+C to stop both")
    print("=" * 60)

    api_thread = threading.Thread(target=run_api, daemon=True)
    bot_thread = threading.Thread(target=run_bot, daemon=True)

    api_thread.start()
    bot_thread.start()

    try:
        api_thread.join()
        bot_thread.join()
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)


if __name__ == "__main__":
    main()
