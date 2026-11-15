from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.types import ChatMemberUpdated, Message, User

from .storage import Storage

GROUP_TYPES = {ChatType.GROUP, ChatType.SUPERGROUP}
router = Router()


@router.message(F.chat.type.in_(GROUP_TYPES))
async def remember_message_author(message: Message, member_storage: Storage) -> None:
    remember_user(member_storage, message.chat.id, message.from_user)


@router.chat_member(F.chat.type.in_(GROUP_TYPES))
async def forget_departed_member(event: ChatMemberUpdated, member_storage: Storage) -> None:
    if event.new_chat_member.status in {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}:
        member_storage.remove_member(event.chat.id, event.new_chat_member.user.id)


def remember_user(member_storage: Storage, chat_id: int, user: User | None) -> bool:
    """Save a non-bot user and report whether a record was saved."""
    if user is None or user.is_bot:
        return False
    member_storage.upsert_member(
        chat_id=chat_id,
        user_id=user.id,
        full_name=user.full_name,
        username=user.username,
    )
    return True
