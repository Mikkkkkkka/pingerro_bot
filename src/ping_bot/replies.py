from __future__ import annotations

from collections.abc import Iterable
from html import escape

from aiogram import Bot
from aiogram.enums import ChatMemberStatus

from .messages import MENTION_HEADER
from .storage import Member

MAX_MENTIONS_PER_MESSAGE = 50
MAX_TEXT_LENGTH = 3500
MAX_COPY_TEXT_LENGTH = 256


def mention_chunks(members: Iterable[Member]) -> list[str]:
    """Create Telegram HTML messages with no more than 50 mentions each."""
    chunks: list[str] = []
    current: list[str] = []
    visible_length = len(MENTION_HEADER)

    for member in members:
        mention, mention_length = _format_mention(member)
        next_length = visible_length + mention_length + (1 if current else 0)
        if current and (
            len(current) >= MAX_MENTIONS_PER_MESSAGE or next_length > MAX_TEXT_LENGTH
        ):
            chunks.append(MENTION_HEADER + "\n".join(current))
            current = []
            visible_length = len(MENTION_HEADER)
        current.append(mention)
        visible_length += mention_length + (1 if len(current) > 1 else 0)

    if current:
        chunks.append(MENTION_HEADER + "\n".join(current))
    return chunks


def _format_mention(member: Member) -> tuple[str, int]:
    """Prefer @username: Telegram reliably treats it as a notifying mention."""
    if member.username:
        mention = f"@{member.username}"
        return mention, len(mention)

    name = member.full_name or str(member.user_id)
    mention = f'<a href="tg://user?id={member.user_id}">{escape(name)}</a>'
    return mention, len(name)


def username_chunks(members: Iterable[Member]) -> list[str]:
    """Create clipboard-sized chunks of @usernames for CopyTextButton."""
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0

    for member in members:
        if not member.username:
            continue
        username = f"@{member.username}"
        next_length = current_length + len(username) + (1 if current else 0)
        if current and next_length > MAX_COPY_TEXT_LENGTH:
            chunks.append(" ".join(current))
            current = []
            current_length = 0
        current.append(username)
        current_length += len(username) + (1 if len(current) > 1 else 0)

    if current:
        chunks.append(" ".join(current))
    return chunks


async def is_administrator(bot: Bot, chat_id: int, user_id: int) -> bool:
    member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
    return member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}
