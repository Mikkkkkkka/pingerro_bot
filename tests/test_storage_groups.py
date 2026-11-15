from pathlib import Path

from ping_bot.storage import Storage


def test_groups_are_scoped_to_chat_and_owner_can_delete(tmp_path: Path) -> None:
    storage = Storage(tmp_path / "bot.sqlite3")
    try:
        storage.upsert_member(1, 10, "First", "first")
        storage.upsert_member(2, 10, "Second", "second")

        assert storage.add_user_to_group(1, "Водилы", 10) == (True, True)
        assert storage.add_user_to_group(2, "Водилы", 10) == (True, True)
        assert [group.name for group in storage.list_groups(1)] == ["Водилы"]
        assert storage.get_group_members(1, "водилы")[0].full_name == "First"
        token = storage.create_group_delete_confirmation(1, "Водилы", requester_user_id=10)
        assert storage.confirm_group_deletion(token, requester_user_id=99).status == "forbidden"
        assert storage.confirm_group_deletion(token, requester_user_id=10).status == "deleted"
        assert storage.get_group(1, "Водилы") is None
        assert storage.get_group(2, "Водилы") is not None
    finally:
        storage.close()


def test_owner_is_transferred_when_owner_leaves(tmp_path: Path) -> None:
    storage = Storage(tmp_path / "bot.sqlite3")
    try:
        storage.upsert_member(1, 10, "Owner", "owner")
        storage.upsert_member(1, 20, "Member", "member")
        storage.add_user_to_group(1, "Водилы", 10)
        storage.add_user_to_group(1, "Водилы", 20)

        removal = storage.remove_user_from_group(1, "Водилы", 10)

        assert removal.removed
        assert removal.ownership_transferred
        assert storage.get_group(1, "Водилы").owner_user_id == 20
    finally:
        storage.close()


def test_only_owner_can_approve_join_request(tmp_path: Path) -> None:
    storage = Storage(tmp_path / "bot.sqlite3")
    try:
        storage.upsert_member(1, 10, "Owner", "owner")
        storage.upsert_member(1, 20, "Applicant", "applicant")
        storage.add_user_to_group(1, "Водилы", 10)
        token = storage.create_group_join_confirmation(1, "Водилы", requester_user_id=20)

        assert storage.confirm_group_join(token, owner_user_id=99).status == "forbidden"
        assert storage.confirm_group_join(token, owner_user_id=10).status == "accepted"
        assert storage.is_user_in_group(1, "Водилы", 20)
    finally:
        storage.close()
