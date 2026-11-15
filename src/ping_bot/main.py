from __future__ import annotations

import asyncio
import argparse
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from .commands import router as commands_router
from .config import Settings
from .storage import Storage
from .tracking import router as tracking_router


async def run(require_admin: bool = True) -> None:
    settings = Settings.from_environment()
    storage = Storage(settings.database_url)
    bot = Bot(settings.token)
    dispatcher = Dispatcher(
        member_storage=storage,
        cooldown_seconds=settings.cooldown_seconds,
        require_admin=require_admin,
    )
    dispatcher.include_router(commands_router)
    dispatcher.include_router(tracking_router)
    await bot.set_my_commands(
        [
            BotCommand(command="help", description="Справка по командам"),
            BotCommand(command="add", description="Добавить себя в список"),
            BotCommand(command="addmany", description="Добавить участников по ID"),
            BotCommand(
                command="non_pinging_all",
                description="Перечислить участников, которых можно упомянуть",
            ),
            BotCommand(command="all_copy", description="Скопировать упоминания"),
            BotCommand(command="group", description="Показать участников группы"),
            BotCommand(command="add_group", description="Вступить в группу"),
            BotCommand(command="addmany_group", description="Добавить IDs в свою группу"),
            BotCommand(command="groups", description="Список групп"),
            BotCommand(command="remove_group", description="Выйти из группы"),
            BotCommand(command="delete_group", description="Удалить свою группу"),
            BotCommand(command="group_copy", description="Скопировать группу"),
        ]
    )
    try:
        await dispatcher.start_polling(bot)
    finally:
        storage.close()
        await bot.session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the group mention bot.")
    parser.add_argument(
        "--dont-require-admin",
        action="store_true",
        help="Allow every group member to use commands normally limited to administrators.",
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    asyncio.run(run(require_admin=not args.dont_require_admin))
