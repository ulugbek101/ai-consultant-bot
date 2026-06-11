import asyncio
import logging

import handlers.admin     # noqa: F401
import handlers.ai_chat   # noqa: F401
import handlers.contact   # noqa: F401
import handlers.start     # noqa: F401
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault
from config import ADMIN_CHAT_ID
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
    db.create_tables()
    db.seed_subcategories()
    await bot.set_my_commands(_USER_COMMANDS, scope=BotCommandScopeDefault())
    await bot.set_my_commands(_ADMIN_COMMANDS, scope=BotCommandScopeChat(chat_id=ADMIN_CHAT_ID))
    logging.info("DB tables ready, commands set")


async def main() -> None:
    dp.startup.register(on_startup)
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
