from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from html import escape

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatMemberStatus, ChatType, ParseMode
from aiogram.filters import Command
from aiogram.types import BotCommand, ChatMemberUpdated, Message

from .config import Settings
from .storage import Member, Storage

GROUP_TYPES = {ChatType.GROUP, ChatType.SUPERGROUP}
MAX_MENTIONS_PER_MESSAGE = 50
MAX_TEXT_LENGTH = 3500

commands_router = Router()
tracking_router = Router()


def create_dispatcher(storage: Storage, cooldown_seconds: int) -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher["storage"] = storage
    dispatcher["cooldown_seconds"] = cooldown_seconds
    dispatcher.include_router(commands_router)
    dispatcher.include_router(tracking_router)
    return dispatcher


@commands_router.message(Command("start"))
async def start(message: Message) -> None:
    await message.answer(
        "Добавьте меня администратором группы. Я буду запоминать пользователей, "
        "которые пишут сообщения, а администраторы смогут вызвать /all."
    )


@commands_router.message(Command("all"), F.chat.type.in_(GROUP_TYPES))
async def mention_all(message: Message, bot: Bot, storage: Storage, cooldown_seconds: int) -> None:
    if message.from_user is not None and not message.from_user.is_bot:
        storage.upsert_member(
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            full_name=message.from_user.full_name,
            username=message.from_user.username,
        )

    if message.from_user is None or not await _is_administrator(bot, message.chat.id, message.from_user.id):
        await message.reply("Команду /all могут использовать только администраторы группы.")
        return

    wait_seconds = storage.claim_cooldown(message.chat.id, cooldown_seconds)
    if wait_seconds:
        await message.reply(f"Повторить /all можно через {wait_seconds} с.")
        return

    members = storage.get_members(message.chat.id)
    if not members:
        await message.reply("Я ещё не видел сообщений от участников этой группы.")
        return

    for part in _mention_chunks(members):
        await message.answer(part, parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.05)


@tracking_router.message(F.chat.type.in_(GROUP_TYPES))
async def remember_message_author(message: Message, storage: Storage) -> None:
    if message.from_user is None or message.from_user.is_bot:
        return
    storage.upsert_member(
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username,
    )


@tracking_router.chat_member(F.chat.type.in_(GROUP_TYPES))
async def forget_departed_member(event: ChatMemberUpdated, storage: Storage) -> None:
    if event.new_chat_member.status in {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}:
        storage.remove_member(event.chat.id, event.new_chat_member.user.id)


def _mention_chunks(members: Iterable[Member]) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    visible_length = len("Внимание:\n")

    for member in members:
        name = member.full_name or str(member.user_id)
        mention = f'<a href="tg://user?id={member.user_id}">{escape(name)}</a>'
        next_length = visible_length + len(name) + (1 if current else 0)
        if current and (len(current) >= MAX_MENTIONS_PER_MESSAGE or next_length > MAX_TEXT_LENGTH):
            chunks.append("Внимание:\n" + " ".join(current))
            current = []
            visible_length = len("Внимание:\n")
        current.append(mention)
        visible_length += len(name) + (1 if len(current) > 1 else 0)

    if current:
        chunks.append("Внимание:\n" + " ".join(current))
    return chunks


async def _is_administrator(bot: Bot, chat_id: int, user_id: int) -> bool:
    member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
    return member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}


async def run() -> None:
    settings = Settings.from_environment()
    storage = Storage(settings.database_path)
    bot = Bot(settings.token)
    dispatcher = create_dispatcher(storage, settings.cooldown_seconds)
    await bot.set_my_commands([BotCommand(command="all", description="Упомянуть участников")])
    try:
        await dispatcher.start_polling(bot)
    finally:
        storage.close()
        await bot.session.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    asyncio.run(run())
