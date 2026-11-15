START_MESSAGE = (
    "Добавьте меня администратором группы. Я буду запоминать пользователей, "
    "которые пишут сообщения, а администраторы смогут вызвать /all."
)
ADMIN_ONLY_MESSAGE = "Команду /all могут использовать только администраторы группы."
NO_MEMBERS_MESSAGE = "Я ещё не видел сообщений от участников этой группы."
MENTION_HEADER = "Внимание:\n"
ADDED_SELF_MESSAGE = "Готово, добавил вас в список для /all."
ADDED_REPLY_MESSAGE = "Готово, добавил вас и автора сообщения в список для /all."
ADDED_MANY_MESSAGE = "Готово, добавил в список: {count}."
ADD_MANY_USAGE_MESSAGE = "Использование: /addmany 123456789 987654321"
ADD_MANY_INVALID_IDS_MESSAGE = "ID должны быть положительными целыми числами, разделёнными пробелами."
ADD_MANY_LIMIT_MESSAGE = "За один раз можно добавить не более {limit} пользователей."


def cooldown_message(wait_seconds: int) -> str:
    return f"Повторить /all можно через {wait_seconds} с."
