import asyncio
import logging

import handlers.admin     # noqa: F401
import handlers.ai_chat   # noqa: F401
import handlers.contact   # noqa: F401
import handlers.start     # noqa: F401
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault
from config import ADMIN_CHAT_IDS
from loader import bot, db, dp
from router import router

_USER_COMMANDS = [
    BotCommand(command="start", description="Начать / Boshlash"),
    BotCommand(command="help",  description="Помощь / Yordam"),
]

_ADMIN_COMMANDS = _USER_COMMANDS + [
    BotCommand(command="admin",  description="Панель администратора"),
    BotCommand(command="users",  description="Список пользователей"),
    BotCommand(command="user",   description="Профиль: /user <id>"),
    BotCommand(command="stats",  description="Статистика"),
    BotCommand(command="topics", description="Темы запросов"),
]


async def on_startup() -> None:
    try:
        db.create_tables()
        db.seed_subcategories()
        db.update_subcategory_labels()
    except Exception as exc:
        logging.error("DB startup error: %s", exc)

    await bot.set_my_commands(_USER_COMMANDS, scope=BotCommandScopeDefault())
    for admin_id in ADMIN_CHAT_IDS:
        try:
            await bot.set_my_commands(_ADMIN_COMMANDS, scope=BotCommandScopeChat(chat_id=admin_id))
            await bot.send_message(
                admin_id,
                "🤖 Бот запущен. Вы получаете это сообщение, потому что являетесь администратором.",
            )
        except Exception as exc:
            logging.warning("Could not reach admin %s: %s", admin_id, exc)

    logging.info("DB ready, commands set, admins notified")


async def main() -> None:
    dp.startup.register(on_startup)
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
