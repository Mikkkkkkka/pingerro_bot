from ping_bot.commands import _parse_user_ids


def test_parse_user_ids_removes_duplicates() -> None:
    assert _parse_user_ids("/addmany 10 20 10") == [10, 20]


def test_parse_user_ids_rejects_non_numeric_values() -> None:
    assert _parse_user_ids("/addmany @someone") is None


def test_parse_user_ids_requires_arguments() -> None:
    assert _parse_user_ids("/addmany") == []
