from __future__ import annotations

import asyncio
import re
from html import escape

from aiogram import Bot, F, Router
from aiogram.enums import ChatType, ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import (
    CopyTextButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    Message,
)

from .messages import (
    ADDED_REPLY_MESSAGE,
    ADD_MANY_GROUP_ADDED_MESSAGE,
    ADD_MANY_GROUP_USAGE_MESSAGE,
    ADDED_MANY_MESSAGE,
    ADDED_SELF_MESSAGE,
    ADD_MANY_INVALID_IDS_MESSAGE,
    ADD_MANY_LIMIT_MESSAGE,
    ADD_MANY_USAGE_MESSAGE,
    ADMIN_ONLY_MESSAGE,
    COPY_BUTTON_TEXT,
    COPY_USERNAMES_MESSAGE,
    EMPTY_GROUP_DELETED_MESSAGE,
    GROUP_ADDED_MESSAGE,
    GROUP_ALREADY_MEMBER_MESSAGE,
    GROUP_CREATED_MESSAGE,
    GROUP_DELETED_MESSAGE,
    GROUP_DELETE_BUTTON,
    GROUP_DELETE_CANCEL_BUTTON,
    GROUP_DELETE_CANCELLED_MESSAGE,
    GROUP_DELETE_CONFIRMATION_MESSAGE,
    GROUP_DELETE_EXPIRED_MESSAGE,
    GROUP_DELETE_FORBIDDEN_MESSAGE,
    GROUP_JOIN_ACCEPTED_MESSAGE,
    GROUP_JOIN_BUTTON,
    GROUP_JOIN_EXPIRED_MESSAGE,
    GROUP_JOIN_FORBIDDEN_MESSAGE,
    GROUP_JOIN_REQUEST_MESSAGE,
    GROUP_MEMBERS_HEADER,
    GROUP_NOT_FOUND_MESSAGE,
    GROUP_NOT_MEMBER_MESSAGE,
    GROUP_REMOVED_MESSAGE,
    GROUP_OWNERSHIP_TRANSFERRED_MESSAGE,
    GROUP_OWNER_ONLY_MESSAGE,
    GROUP_USAGE_MESSAGE,
    GROUPS_HEADER,
    HELP_MESSAGE,
    NO_MEMBERS_MESSAGE,
    NO_GROUP_MEMBERS_MESSAGE,
    NO_GROUPS_MESSAGE,
    NO_USERNAMES_MESSAGE,
    START_MESSAGE,
    cooldown_message,
)
from .replies import is_administrator, mention_chunks, username_chunks
from .storage import Member, Storage
from .tracking import remember_user

GROUP_TYPES = {ChatType.GROUP, ChatType.SUPERGROUP}
MAX_IDS_PER_ADD_MANY = 100
router = Router()


@router.message(Command("start"))
async def start(message: Message) -> None:
    await message.answer(START_MESSAGE)


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(HELP_MESSAGE)


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


@router.message(Command("addmany_group"), F.chat.type.in_(GROUP_TYPES))
async def add_many_group(message: Message, bot: Bot, member_storage: Storage) -> None:
    parsed = _parse_group_and_user_ids(message.text)
    if parsed is None:
        await message.reply(ADD_MANY_GROUP_USAGE_MESSAGE)
        return
    name, user_ids = parsed
    if len(user_ids) > MAX_IDS_PER_ADD_MANY:
        await message.reply(ADD_MANY_LIMIT_MESSAGE.format(limit=MAX_IDS_PER_ADD_MANY))
        return
    if message.from_user is None:
        return

    group = member_storage.get_group(message.chat.id, name)
    if group is None:
        await message.reply(GROUP_NOT_FOUND_MESSAGE.format(name=name))
        return
    if group.owner_user_id != message.from_user.id:
        await message.reply(GROUP_OWNER_ONLY_MESSAGE)
        return

    unresolved_ids: list[int] = []
    known_user_ids: list[int] = []
    for user_id in user_ids:
        try:
            chat_member = await bot.get_chat_member(
                chat_id=message.chat.id, user_id=user_id
            )
        except TelegramBadRequest:
            unresolved_ids.append(user_id)
        else:
            if remember_user(member_storage, message.chat.id, chat_member.user):
                known_user_ids.append(user_id)
        await asyncio.sleep(0.05)

    member_storage.add_members_by_ids(message.chat.id, unresolved_ids)
    member_storage.add_users_to_group(
        message.chat.id, name, known_user_ids + unresolved_ids
    )
    await message.reply(ADD_MANY_GROUP_ADDED_MESSAGE.format(name=group.name, count=len(user_ids)))


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
    await _refresh_members_without_usernames(
        bot, member_storage, message.chat.id, members
    )
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

    members = member_storage.get_members(message.chat.id)
    await _refresh_members_without_usernames(
        bot, member_storage, message.chat.id, members
    )
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


@router.message(Command("add_group"), F.chat.type.in_(GROUP_TYPES))
async def add_group(message: Message, member_storage: Storage) -> None:
    name = _group_name_argument(message.text)
    if name is None:
        await message.reply(GROUP_USAGE_MESSAGE.format(command="add_group"))
        return
    if message.from_user is None:
        return

    remember_user(member_storage, message.chat.id, message.from_user)
    group = member_storage.get_group(message.chat.id, name)
    if group is None:
        group_created, _ = member_storage.add_user_to_group(
            message.chat.id, name, message.from_user.id
        )
        if group_created:
            await message.reply(GROUP_CREATED_MESSAGE.format(name=name))
            return

    if member_storage.is_user_in_group(message.chat.id, name, message.from_user.id):
        await message.reply(GROUP_ALREADY_MEMBER_MESSAGE.format(name=name))
        return

    token = member_storage.create_group_join_confirmation(
        message.chat.id, name, message.from_user.id
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=GROUP_JOIN_BUTTON, callback_data=f"join_group:{token}"
                )
            ]
        ]
    )
    await message.answer(
        GROUP_JOIN_REQUEST_MESSAGE.format(
            name=escape(name),
            user=_user_html(
                message.from_user.id,
                message.from_user.full_name,
                message.from_user.username,
            ),
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )


@router.message(Command("group"), F.chat.type.in_(GROUP_TYPES))
async def show_group(message: Message, bot: Bot, member_storage: Storage) -> None:
    name = _group_name_argument(message.text)
    if name is None:
        await message.reply(GROUP_USAGE_MESSAGE.format(command="group"))
        return
    if member_storage.get_group(message.chat.id, name) is None:
        await message.reply(GROUP_NOT_FOUND_MESSAGE.format(name=name))
        return

    members = member_storage.get_group_members(message.chat.id, name)
    await _refresh_members_without_usernames(
        bot, member_storage, message.chat.id, members
    )
    members = member_storage.get_group_members(message.chat.id, name)
    if not members:
        await message.reply(NO_GROUP_MEMBERS_MESSAGE.format(name=name))
        return

    await message.answer(GROUP_MEMBERS_HEADER.format(name=name))
    for part in mention_chunks(members):
        await message.answer(part, parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.05)


@router.message(Command("groups"), F.chat.type.in_(GROUP_TYPES))
async def show_groups(message: Message, member_storage: Storage) -> None:
    groups = member_storage.list_groups(message.chat.id)
    if not groups:
        await message.reply(NO_GROUPS_MESSAGE)
        return

    for part in _text_chunks(GROUPS_HEADER, [group.name for group in groups]):
        await message.answer(part)


@router.message(Command("remove_group"), F.chat.type.in_(GROUP_TYPES))
async def remove_group(message: Message, member_storage: Storage) -> None:
    name = _group_name_argument(message.text)
    if name is None:
        await message.reply(GROUP_USAGE_MESSAGE.format(command="remove_group"))
        return
    if message.from_user is None:
        return

    removal = member_storage.remove_user_from_group(
        message.chat.id, name, message.from_user.id
    )
    if removal.removed:
        reply = GROUP_REMOVED_MESSAGE.format(name=name)
        if removal.ownership_transferred:
            reply += "\n" + GROUP_OWNERSHIP_TRANSFERRED_MESSAGE
        elif removal.group_deleted:
            reply += "\n" + EMPTY_GROUP_DELETED_MESSAGE
        await message.reply(reply)
    elif member_storage.get_group(message.chat.id, name) is None:
        await message.reply(GROUP_NOT_FOUND_MESSAGE.format(name=name))
    else:
        await message.reply(GROUP_NOT_MEMBER_MESSAGE.format(name=name))


@router.message(Command("delete_group"), F.chat.type.in_(GROUP_TYPES))
async def delete_group(message: Message, member_storage: Storage) -> None:
    name = _group_name_argument(message.text)
    if name is None:
        await message.reply(GROUP_USAGE_MESSAGE.format(command="delete_group"))
        return
    if message.from_user is None:
        return

    group = member_storage.get_group(message.chat.id, name)
    if group is None:
        await message.reply(GROUP_NOT_FOUND_MESSAGE.format(name=name))
        return
    if group.owner_user_id != message.from_user.id:
        await message.reply(GROUP_DELETE_FORBIDDEN_MESSAGE)
        return
    token = member_storage.create_group_delete_confirmation(
        message.chat.id, name, message.from_user.id
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=GROUP_DELETE_BUTTON, callback_data=f"delete_group:{token}"
                ),
                InlineKeyboardButton(
                    text=GROUP_DELETE_CANCEL_BUTTON, callback_data=f"cancel_delete_group:{token}"
                ),
            ]
        ]
    )
    await message.reply(
        GROUP_DELETE_CONFIRMATION_MESSAGE.format(name=group.name), reply_markup=keyboard
    )


@router.message(Command("group_copy", "groupc"), F.chat.type.in_(GROUP_TYPES))
async def copy_group(message: Message, bot: Bot, member_storage: Storage) -> None:
    name = _group_name_argument(message.text)
    if name is None:
        await message.reply(GROUP_USAGE_MESSAGE.format(command="group_copy"))
        return
    if member_storage.get_group(message.chat.id, name) is None:
        await message.reply(GROUP_NOT_FOUND_MESSAGE.format(name=name))
        return

    members = member_storage.get_group_members(message.chat.id, name)
    await _refresh_members_without_usernames(
        bot, member_storage, message.chat.id, members
    )
    chunks = username_chunks(member_storage.get_group_members(message.chat.id, name))
    if not chunks:
        await message.reply(NO_GROUP_MEMBERS_MESSAGE.format(name=name))
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
        await message.answer(
            f"Группа «{name}». {COPY_USERNAMES_MESSAGE}", reply_markup=keyboard
        )


@router.callback_query(F.data.startswith("delete_group:"))
async def confirm_delete_group(
    callback: CallbackQuery, member_storage: Storage
) -> None:
    if callback.from_user is None or callback.data is None:
        return
    token = callback.data.removeprefix("delete_group:")
    result = member_storage.confirm_group_deletion(token, callback.from_user.id)
    if result.status == "deleted":
        text = GROUP_DELETED_MESSAGE.format(name=result.name)
    elif result.status == "forbidden":
        text = GROUP_DELETE_FORBIDDEN_MESSAGE
    else:
        text = GROUP_DELETE_EXPIRED_MESSAGE
    await callback.answer(text)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text)


@router.callback_query(F.data.startswith("cancel_delete_group:"))
async def cancel_delete_group(
    callback: CallbackQuery, member_storage: Storage
) -> None:
    if callback.from_user is None or callback.data is None:
        return
    token = callback.data.removeprefix("cancel_delete_group:")
    if member_storage.cancel_group_deletion(token, callback.from_user.id):
        text = GROUP_DELETE_CANCELLED_MESSAGE
    else:
        text = GROUP_DELETE_EXPIRED_MESSAGE
    await callback.answer(text)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text)


@router.callback_query(F.data.startswith("join_group:"))
async def confirm_join_group(callback: CallbackQuery, member_storage: Storage) -> None:
    if callback.from_user is None or callback.data is None:
        return
    token = callback.data.removeprefix("join_group:")
    result = member_storage.confirm_group_join(token, callback.from_user.id)
    if result.status == "accepted":
        text = GROUP_JOIN_ACCEPTED_MESSAGE.format(name=result.name)
    elif result.status == "forbidden":
        text = GROUP_JOIN_FORBIDDEN_MESSAGE
    else:
        text = GROUP_JOIN_EXPIRED_MESSAGE
    await callback.answer(text)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text)


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


def _group_name_argument(text: str | None) -> str | None:
    if text is None:
        return None
    parts = text.split(maxsplit=1)
    if len(parts) == 1:
        return None
    name = " ".join(parts[1].split())
    return name if 0 < len(name) <= 64 else None


def _parse_group_and_user_ids(text: str | None) -> tuple[str, list[int]] | None:
    if text is None:
        return None
    parts = text.split(maxsplit=1)
    if len(parts) == 1:
        return None
    arguments = parts[1].split()
    first_id_index = len(arguments)
    while first_id_index > 0 and re.fullmatch(r"[1-9]\d{0,18}", arguments[first_id_index - 1]):
        first_id_index -= 1
    if first_id_index == 0 or first_id_index == len(arguments):
        return None

    name = " ".join(arguments[:first_id_index])
    if not 0 < len(name) <= 64:
        return None
    user_ids: list[int] = []
    for token in arguments[first_id_index:]:
        user_id = int(token)
        if user_id > 9_223_372_036_854_775_807:
            return None
        if user_id not in user_ids:
            user_ids.append(user_id)
    return name, user_ids


def _text_chunks(header: str, items: list[str], max_length: int = 3500) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_length = len(header)
    for item in items:
        next_length = current_length + len(item) + (1 if current else 0)
        if current and next_length > max_length:
            chunks.append(header + "\n".join(current))
            current = []
            current_length = len(header)
        current.append(item)
        current_length += len(item) + (1 if len(current) > 1 else 0)
    if current:
        chunks.append(header + "\n".join(current))
    return chunks


def _user_html(user_id: int, full_name: str, username: str | None) -> str:
    if username:
        return f"@{username}"
    return f'<a href="tg://user?id={user_id}">{escape(full_name)}</a>'


async def _refresh_members_without_usernames(
    bot: Bot, member_storage: Storage, chat_id: int, members: list[Member]
) -> None:
    for member in members:
        if member.username:
            continue
        try:
            chat_member = await bot.get_chat_member(chat_id=chat_id, user_id=member.user_id)
        except TelegramBadRequest:
            continue
        remember_user(member_storage, chat_id, chat_member.user)
        await asyncio.sleep(0.05)
