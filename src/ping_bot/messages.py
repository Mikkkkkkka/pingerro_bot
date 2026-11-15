START_MESSAGE = (
    "Добавьте меня администратором группы. Я буду запоминать пользователей, "
    "которые пишут сообщения, а администраторы смогут вызвать /all."
)
HELP_MESSAGE = """Я помогаю собрать упоминания участников группы.

Я запоминаю пользователей, которые пишут сообщения в группе. Telegram не даёт боту полный список участников, поэтому в базе есть только пользователи, которых я уже видел или которых добавили вручную.

/add — добавить себя в список.
/addmany <ID...> — добавить до 100 пользователей по числовым Telegram ID.
/all — отправить список известных участников.
/all_copy или /allc — показать кнопки для копирования @username; скопированный текст можно отправить от своего имени.
/group <название> — перечислить участников группы интересов.
/add_group <название> — создать группу или отправить владельцу заявку на вступление.
/addmany_group <название> <ID...> — владельцу пакетно добавить участников по ID.
/groups — показать все группы в этом чате.
/remove_group <название> — выйти из группы.
/delete_group <название> — удалить группу, если вы её владелец.
/group_copy или /groupc <название> — показать кнопки копирования @username участников группы.
/help — показать эту справку.

По умолчанию /addmany, /all и /all_copy доступны администраторам группы."""
ADMIN_ONLY_MESSAGE = "Эту команду могут использовать только администраторы группы."
NO_MEMBERS_MESSAGE = "Я ещё не видел сообщений от участников этой группы."
MENTION_HEADER = "Внимание:\n"
ADDED_SELF_MESSAGE = "Готово, добавил вас в список участников."
ADDED_REPLY_MESSAGE = "Готово, добавил вас и автора сообщения в список участников."
ADDED_MANY_MESSAGE = "Готово, добавил в список: {count}."
ADD_MANY_USAGE_MESSAGE = "Использование: /addmany 123456789 987654321"
ADD_MANY_INVALID_IDS_MESSAGE = "ID должны быть положительными целыми числами, разделёнными пробелами."
ADD_MANY_LIMIT_MESSAGE = "За один раз можно добавить не более {limit} пользователей."
ADD_MANY_GROUP_USAGE_MESSAGE = "Использование: /addmany_group <группа> 123456789 987654321"
ADD_MANY_GROUP_ADDED_MESSAGE = "Готово, добавил в группу «{name}»: {count}."
NO_USERNAMES_MESSAGE = "В базе этой группы пока нет пользователей с username."
COPY_USERNAMES_MESSAGE = "Скопируйте этот фрагмент и отправьте его в группу от своего имени."
COPY_BUTTON_TEXT = "Скопировать упоминания {number}/{total}"
GROUP_USAGE_MESSAGE = "Укажите название группы: /{command} <название>."
GROUP_NOT_FOUND_MESSAGE = "Группа «{name}» не найдена."
GROUP_CREATED_MESSAGE = "Группа «{name}» создана, вы добавлены в неё как владелец."
GROUP_ADDED_MESSAGE = "Вы добавлены в группу «{name}»."
GROUP_ALREADY_MEMBER_MESSAGE = "Вы уже состоите в группе «{name}»."
GROUP_JOIN_REQUEST_MESSAGE = "Заявка {user} в группу «{name}». Владелец, подтвердите вступление."
GROUP_JOIN_BUTTON = "Принять в группу"
GROUP_JOIN_ACCEPTED_MESSAGE = "Пользователь добавлен в группу «{name}»."
GROUP_JOIN_FORBIDDEN_MESSAGE = "Подтвердить заявку может только текущий владелец группы."
GROUP_JOIN_EXPIRED_MESSAGE = "Заявка на вступление истекла. Пользователь может отправить /add_group снова."
GROUP_REMOVED_MESSAGE = "Вы вышли из группы «{name}»."
GROUP_OWNERSHIP_TRANSFERRED_MESSAGE = "Владение группой случайно передано одному из оставшихся участников."
EMPTY_GROUP_DELETED_MESSAGE = "Группа удалена, потому что в ней не осталось участников."
GROUP_NOT_MEMBER_MESSAGE = "Вы не состоите в группе «{name}»."
GROUP_DELETED_MESSAGE = "Группа «{name}» удалена."
GROUP_DELETE_FORBIDDEN_MESSAGE = "Удалить группу может только её владелец."
GROUP_OWNER_ONLY_MESSAGE = "Эта команда доступна только владельцу группы."
GROUP_DELETE_CONFIRMATION_MESSAGE = (
    "Удалить группу «{name}» вместе со всеми записями об её участниках? "
    "Это действие нельзя отменить."
)
GROUP_DELETE_BUTTON = "Удалить группу"
GROUP_DELETE_CANCEL_BUTTON = "Отмена"
GROUP_DELETE_CANCELLED_MESSAGE = "Удаление группы отменено."
GROUP_DELETE_EXPIRED_MESSAGE = "Подтверждение удаления истекло. Повторите /delete_group."
NO_GROUPS_MESSAGE = "В этом чате пока нет групп."
GROUPS_HEADER = "Группы этого чата:\n"
GROUP_MEMBERS_HEADER = "Участники группы «{name}»: \n"
NO_GROUP_MEMBERS_MESSAGE = "В группе «{name}» пока нет участников."


def cooldown_message(wait_seconds: int) -> str:
    return f"Повторить /all можно через {wait_seconds} с."
