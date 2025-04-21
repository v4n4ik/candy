import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from admin_bot import *  # Подключаем Application из admin_bot

LOCK_FILE = '/tmp/bot_run.lock'  # Путь к файлу блокировки

# Функция для создания блокировки
def create_lock():
    if os.path.exists(LOCK_FILE):
        return False
    with open(LOCK_FILE, 'w') as f:
        f.write("Bot is running.")  # Просто записываем что-то в файл
    return True

# Функция для удаления блокировки
def remove_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

# Функция для запуска Telegram-бота
async def run_telegram_bot():
    app.add_handler(CommandHandler("add_product", add_product))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("delete", delete))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("Готово"), handle_done))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    await asyncio.Event().wait()  # Ожидание бесконечно, чтобы бот оставался активным

def start_bot():
    if not create_lock():
        print("Bot is already running.")
        return  # Если бот уже работает, просто выходим

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            print("Event loop is already running. Adding task to the loop.")
            task = loop.create_task(run_telegram_bot())
            loop.run_forever()
        else:
            print("Starting new event loop.")
            loop.run_until_complete(run_telegram_bot())
    finally:
        remove_lock()  # Убираем блокировку после завершения работы бота

if __name__ == "__main__":
    start_bot()
