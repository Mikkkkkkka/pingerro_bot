from ping_bot.main import _mention_chunks
from ping_bot.storage import Member


def test_mentions_use_user_id_links() -> None:
    chunks = _mention_chunks([Member(user_id=42, full_name="Анна & Олег", username=None)])

    assert chunks == ['Внимание:\n<a href="tg://user?id=42">Анна &amp; Олег</a>']


def test_mentions_are_split() -> None:
    members = [Member(user_id=index, full_name="x", username=None) for index in range(51)]

    chunks = _mention_chunks(members)

    assert len(chunks) == 2
    assert all(chunk.startswith("Внимание:\n") for chunk in chunks)
