START_MESSAGE = (
    "Добавьте меня администратором группы. Я буду запоминать пользователей, "
    "которые пишут сообщения, а администраторы смогут вызвать /non_pinging_all."
)
ADMIN_ONLY_MESSAGE = "Эту команду могут использовать только администраторы группы."
NO_MEMBERS_MESSAGE = "Я ещё не видел сообщений от участников этой группы."
MENTION_HEADER = "Внимание:\n"
ADDED_SELF_MESSAGE = "Готово, добавил вас в список участников."
ADDED_REPLY_MESSAGE = "Готово, добавил вас и автора сообщения в список участников."
ADDED_MANY_MESSAGE = "Готово, добавил в список: {count}."
ADD_MANY_USAGE_MESSAGE = "Использование: /addmany 123456789 987654321"
ADD_MANY_INVALID_IDS_MESSAGE = "ID должны быть положительными целыми числами, разделёнными пробелами."
ADD_MANY_LIMIT_MESSAGE = "За один раз можно добавить не более {limit} пользователей."
NO_USERNAMES_MESSAGE = "В базе этой группы пока нет пользователей с username."
COPY_USERNAMES_MESSAGE = "Скопируйте этот фрагмент и отправьте его в группу от своего имени."
COPY_BUTTON_TEXT = "Скопировать упоминания {number}/{total}"


def cooldown_message(wait_seconds: int) -> str:
    return f"Повторить /non_pinging_all можно через {wait_seconds} с."
