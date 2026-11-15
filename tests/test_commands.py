from ping_bot.commands import _group_name_argument, _parse_group_and_user_ids, _parse_user_ids


def test_parse_user_ids_removes_duplicates() -> None:
    assert _parse_user_ids("/addmany 10 20 10") == [10, 20]


def test_parse_user_ids_rejects_non_numeric_values() -> None:
    assert _parse_user_ids("/addmany @someone") is None


def test_parse_user_ids_requires_arguments() -> None:
    assert _parse_user_ids("/addmany") == []


def test_group_name_is_normalized() -> None:
    assert _group_name_argument("/group   Водилы   СПб ") == "Водилы СПб"


def test_parse_group_and_user_ids_supports_group_names_with_spaces() -> None:
    assert _parse_group_and_user_ids("/addmany_group Водилы СПб 10 20") == (
        "Водилы СПб",
        [10, 20],
    )
