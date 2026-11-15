from ping_bot.replies import mention_chunks, username_chunks
from ping_bot.storage import Member


def test_mentions_use_user_id_links() -> None:
    chunks = mention_chunks([Member(user_id=42, full_name="Анна & Олег", username=None)])

    assert chunks == ['Внимание:\n<a href="tg://user?id=42">Анна &amp; Олег</a>']


def test_mentions_prefer_username() -> None:
    chunks = mention_chunks([Member(user_id=42, full_name="Анна", username="anna")])

    assert chunks == ["Внимание:\n@anna"]


def test_mentions_are_split() -> None:
    members = [Member(user_id=index, full_name="x", username=None) for index in range(51)]

    chunks = mention_chunks(members)

    assert len(chunks) == 2
    assert all(chunk.startswith("Внимание:\n") for chunk in chunks)


def test_username_chunks_skip_members_without_username() -> None:
    chunks = username_chunks(
        [
            Member(user_id=1, full_name="One", username="one"),
            Member(user_id=2, full_name="Two", username=None),
            Member(user_id=3, full_name="Three", username="three"),
        ]
    )

    assert chunks == ["@one @three"]
