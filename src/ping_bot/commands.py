from __future__ import annotations

import asyncio
import re

from aiogram import Bot, F, Router
from aiogram.enums import ChatType, ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import (
    CopyTextButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from .messages import (
    ADDED_REPLY_MESSAGE,
    ADDED_MANY_MESSAGE,
    ADDED_SELF_MESSAGE,
    ADD_MANY_INVALID_IDS_MESSAGE,
    ADD_MANY_LIMIT_MESSAGE,
    ADD_MANY_USAGE_MESSAGE,
    ADMIN_ONLY_MESSAGE,
    COPY_BUTTON_TEXT,
    COPY_USERNAMES_MESSAGE,
    NO_MEMBERS_MESSAGE,
    NO_USERNAMES_MESSAGE,
    START_MESSAGE,
    cooldown_message,
)
from .replies import is_administrator, mention_chunks, username_chunks
from .storage import Storage
from .tracking import remember_user

GROUP_TYPES = {ChatType.GROUP, ChatType.SUPERGROUP}
MAX_IDS_PER_ADD_MANY = 100
router = Router()


@router.message(Command("start"))
async def start(message: Message) -> None:
    await message.answer(START_MESSAGE)


@router.message(Command("add"), F.chat.type.in_(GROUP_TYPES))
async def add_member(message: Message, member_storage: Storage) -> None:
    """Allow users to opt in when the bot cannot read ordinary group messages."""
    added_author = remember_user(member_storage, message.chat.id, message.from_user)
    reply_author = getattr(message.reply_to_message, "from_user", None)
    added_reply_author = remember_user(member_storage, message.chat.id, reply_author)

    if added_reply_author:
        await message.reply(ADDED_REPLY_MESSAGE)
    elif added_author:
        await message.reply(ADDED_SELF_MESSAGE)


@router.message(Command("addmany"), F.chat.type.in_(GROUP_TYPES))
async def add_many(
    message: Message, bot: Bot, member_storage: Storage, require_admin: bool
) -> None:
    if message.from_user is None:
        await message.reply(ADMIN_ONLY_MESSAGE)
        return
    if require_admin and not await is_administrator(
        bot, message.chat.id, message.from_user.id
    ):
        await message.reply(ADMIN_ONLY_MESSAGE)
        return

    user_ids = _parse_user_ids(message.text)
    if user_ids is None:
        await message.reply(ADD_MANY_INVALID_IDS_MESSAGE)
        return
    if not user_ids:
        await message.reply(ADD_MANY_USAGE_MESSAGE)
        return
    if len(user_ids) > MAX_IDS_PER_ADD_MANY:
        await message.reply(ADD_MANY_LIMIT_MESSAGE.format(limit=MAX_IDS_PER_ADD_MANY))
        return

    unresolved_ids: list[int] = []
    for user_id in user_ids:
        try:
            chat_member = await bot.get_chat_member(
                chat_id=message.chat.id, user_id=user_id
            )
        except TelegramBadRequest:
            unresolved_ids.append(user_id)
        else:
            remember_user(member_storage, message.chat.id, chat_member.user)
        await asyncio.sleep(0.05)

    member_storage.add_members_by_ids(message.chat.id, unresolved_ids)
    await message.reply(ADDED_MANY_MESSAGE.format(count=len(user_ids)))


@router.message(Command("non_pinging_all"), F.chat.type.in_(GROUP_TYPES))
async def mention_all(
    message: Message,
    bot: Bot,
    member_storage: Storage,
    cooldown_seconds: int,
    require_admin: bool,
) -> None:
    remember_user(member_storage, message.chat.id, message.from_user)

    if message.from_user is None:
        await message.reply(ADMIN_ONLY_MESSAGE)
        return
    if require_admin and not await is_administrator(
        bot, message.chat.id, message.from_user.id
    ):
        await message.reply(ADMIN_ONLY_MESSAGE)
        return

    wait_seconds = member_storage.claim_cooldown(message.chat.id, cooldown_seconds)
    if wait_seconds:
        await message.reply(cooldown_message(wait_seconds))
        return

    members = member_storage.get_members(message.chat.id)
    if not members:
        await message.reply(NO_MEMBERS_MESSAGE)
        return

    for part in mention_chunks(members):
        await message.answer(part, parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.05)


@router.message(Command("all_copy", "allc"), F.chat.type.in_(GROUP_TYPES))
async def text_all(
    message: Message,
    bot: Bot,
    member_storage: Storage,
    require_admin: bool,
) -> None:
    remember_user(member_storage, message.chat.id, message.from_user)

    if message.from_user is None:
        await message.reply(ADMIN_ONLY_MESSAGE)
        return
    if require_admin and not await is_administrator(
        bot, message.chat.id, message.from_user.id
    ):
        await message.reply(ADMIN_ONLY_MESSAGE)
        return

    chunks = username_chunks(member_storage.get_members(message.chat.id))
    if not chunks:
        await message.reply(NO_USERNAMES_MESSAGE)
        return

    for index, chunk in enumerate(chunks, start=1):
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=COPY_BUTTON_TEXT.format(number=index, total=len(chunks)),
                        copy_text=CopyTextButton(text=chunk),
                    )
                ]
            ]
        )
        await message.answer(COPY_USERNAMES_MESSAGE, reply_markup=keyboard)


def _parse_user_ids(text: str | None) -> list[int] | None:
    """Return unique positive signed-64-bit IDs, or None for invalid arguments."""
    if text is None:
        return []
    arguments = text.split(maxsplit=1)
    if len(arguments) == 1:
        return []

    user_ids: list[int] = []
    for token in arguments[1].split():
        if re.fullmatch(r"[1-9]\d{0,18}", token) is None:
            return None
        user_id = int(token)
        if user_id > 9_223_372_036_854_775_807:
            return None
        if user_id not in user_ids:
            user_ids.append(user_id)
    return user_ids
