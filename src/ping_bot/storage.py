from __future__ import annotations

import sqlite3
from secrets import token_urlsafe
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Member:
    user_id: int
    full_name: str
    username: str | None


@dataclass(frozen=True, slots=True)
class InterestGroup:
    name: str
    owner_user_id: int


@dataclass(frozen=True, slots=True)
class GroupRemoval:
    removed: bool
    ownership_transferred: bool
    group_deleted: bool


@dataclass(frozen=True, slots=True)
class GroupDeletion:
    status: str
    name: str | None = None


class Storage:
    def __init__(self, database_path: Path) -> None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(database_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS members (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                full_name TEXT NOT NULL,
                username TEXT,
                last_seen_at TEXT NOT NULL,
                PRIMARY KEY (chat_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS chat_cooldowns (
                chat_id INTEGER PRIMARY KEY,
                last_all_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS interest_groups (
                chat_id INTEGER NOT NULL,
                group_key TEXT NOT NULL,
                name TEXT NOT NULL,
                creator_user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (chat_id, group_key)
            );

            CREATE TABLE IF NOT EXISTS interest_group_members (
                chat_id INTEGER NOT NULL,
                group_key TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                PRIMARY KEY (chat_id, group_key, user_id),
                FOREIGN KEY (chat_id, group_key)
                    REFERENCES interest_groups (chat_id, group_key)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS group_delete_confirmations (
                token TEXT PRIMARY KEY,
                chat_id INTEGER NOT NULL,
                group_key TEXT NOT NULL,
                requester_user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS group_join_confirmations (
                token TEXT PRIMARY KEY,
                chat_id INTEGER NOT NULL,
                group_key TEXT NOT NULL,
                requester_user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def upsert_member(
        self, chat_id: int, user_id: int, full_name: str, username: str | None
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO members (chat_id, user_id, full_name, username, last_seen_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET
                full_name = excluded.full_name,
                username = excluded.username,
                last_seen_at = excluded.last_seen_at
            """,
            (chat_id, user_id, full_name, username, _utc_now()),
        )
        self.connection.commit()

    def remove_member(self, chat_id: int, user_id: int) -> None:
        self.connection.execute(
            "DELETE FROM members WHERE chat_id = ? AND user_id = ?", (chat_id, user_id)
        )
        self.connection.execute(
            "DELETE FROM interest_group_members WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id),
        )
        self.connection.commit()

    def get_members(self, chat_id: int) -> list[Member]:
        rows = self.connection.execute(
            """
            SELECT user_id, full_name, username
            FROM members
            WHERE chat_id = ?
            ORDER BY last_seen_at DESC
            """,
            (chat_id,),
        ).fetchall()
        return [Member(**dict(row)) for row in rows]

    def get_member(self, chat_id: int, user_id: int) -> Member | None:
        row = self.connection.execute(
            """
            SELECT user_id, full_name, username
            FROM members
            WHERE chat_id = ? AND user_id = ?
            """,
            (chat_id, user_id),
        ).fetchone()
        return Member(**dict(row)) if row else None

    def add_members_by_ids(self, chat_id: int, user_ids: list[int]) -> None:
        """Add IDs received from an administrator without replacing known names."""
        seen_at = _utc_now()
        self.connection.executemany(
            """
            INSERT INTO members (chat_id, user_id, full_name, username, last_seen_at)
            VALUES (?, ?, ?, NULL, ?)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET
                last_seen_at = excluded.last_seen_at
            """,
            [(chat_id, user_id, f"Пользователь {user_id}", seen_at) for user_id in user_ids],
        )
        self.connection.commit()

    def add_user_to_group(
        self, chat_id: int, name: str, user_id: int
    ) -> tuple[bool, bool]:
        """Add a user and return (group_was_created, user_was_added)."""
        group_key = _group_key(name)
        cursor = self.connection.execute(
            """
            INSERT INTO interest_groups (chat_id, group_key, name, creator_user_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(chat_id, group_key) DO NOTHING
            """,
            (chat_id, group_key, name, user_id, _utc_now()),
        )
        group_was_created = cursor.rowcount == 1
        cursor = self.connection.execute(
            """
            INSERT INTO interest_group_members (chat_id, group_key, user_id)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id, group_key, user_id) DO NOTHING
            """,
            (chat_id, group_key, user_id),
        )
        self.connection.commit()
        return group_was_created, cursor.rowcount == 1

    def get_group(self, chat_id: int, name: str) -> InterestGroup | None:
        row = self.connection.execute(
            """
            SELECT name, creator_user_id AS owner_user_id
            FROM interest_groups
            WHERE chat_id = ? AND group_key = ?
            """,
            (chat_id, _group_key(name)),
        ).fetchone()
        return InterestGroup(**dict(row)) if row else None

    def get_group_members(self, chat_id: int, name: str) -> list[Member]:
        rows = self.connection.execute(
            """
            SELECT members.user_id, members.full_name, members.username
            FROM interest_group_members AS group_members
            JOIN members ON members.chat_id = group_members.chat_id
                AND members.user_id = group_members.user_id
            WHERE group_members.chat_id = ? AND group_members.group_key = ?
            ORDER BY members.last_seen_at DESC
            """,
            (chat_id, _group_key(name)),
        ).fetchall()
        return [Member(**dict(row)) for row in rows]

    def is_user_in_group(self, chat_id: int, name: str, user_id: int) -> bool:
        row = self.connection.execute(
            """
            SELECT 1 FROM interest_group_members
            WHERE chat_id = ? AND group_key = ? AND user_id = ?
            """,
            (chat_id, _group_key(name), user_id),
        ).fetchone()
        return row is not None

    def add_users_to_group(self, chat_id: int, name: str, user_ids: list[int]) -> None:
        self.connection.executemany(
            """
            INSERT INTO interest_group_members (chat_id, group_key, user_id)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id, group_key, user_id) DO NOTHING
            """,
            [(chat_id, _group_key(name), user_id) for user_id in user_ids],
        )
        self.connection.commit()

    def list_groups(self, chat_id: int) -> list[InterestGroup]:
        rows = self.connection.execute(
            """
            SELECT name, creator_user_id AS owner_user_id
            FROM interest_groups
            WHERE chat_id = ?
            ORDER BY name COLLATE NOCASE
            """,
            (chat_id,),
        ).fetchall()
        return [InterestGroup(**dict(row)) for row in rows]

    def remove_user_from_group(
        self, chat_id: int, name: str, user_id: int
    ) -> GroupRemoval:
        group_key = _group_key(name)
        group = self.get_group(chat_id, name)
        if group is None:
            return GroupRemoval(
                removed=False, ownership_transferred=False, group_deleted=False
            )

        cursor = self.connection.execute(
            """
            DELETE FROM interest_group_members
            WHERE chat_id = ? AND group_key = ? AND user_id = ?
            """,
            (chat_id, group_key, user_id),
        )
        removed = cursor.rowcount == 1
        ownership_transferred = False
        group_deleted = False
        if removed and group.owner_user_id == user_id:
            new_owner = self.connection.execute(
                """
                SELECT user_id FROM interest_group_members
                WHERE chat_id = ? AND group_key = ?
                ORDER BY RANDOM()
                LIMIT 1
                """,
                (chat_id, group_key),
            ).fetchone()
            if new_owner is not None:
                self.connection.execute(
                    """
                    UPDATE interest_groups
                    SET creator_user_id = ?
                    WHERE chat_id = ? AND group_key = ?
                    """,
                    (new_owner["user_id"], chat_id, group_key),
                )
                ownership_transferred = True
            else:
                self.connection.execute(
                    "DELETE FROM interest_groups WHERE chat_id = ? AND group_key = ?",
                    (chat_id, group_key),
                )
                group_deleted = True
        self.connection.commit()
        return GroupRemoval(
            removed=removed,
            ownership_transferred=ownership_transferred,
            group_deleted=group_deleted,
        )

    def create_group_delete_confirmation(
        self, chat_id: int, name: str, requester_user_id: int
    ) -> str:
        token = token_urlsafe(12)
        expires_at = datetime.now(UTC).timestamp() + 300
        self.connection.execute(
            """
            INSERT INTO group_delete_confirmations
                (token, chat_id, group_key, requester_user_id, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (token, chat_id, _group_key(name), requester_user_id, str(expires_at)),
        )
        self.connection.commit()
        return token

    def create_group_join_confirmation(
        self, chat_id: int, name: str, requester_user_id: int
    ) -> str:
        token = token_urlsafe(12)
        expires_at = datetime.now(UTC).timestamp() + 300
        self.connection.execute(
            """
            INSERT INTO group_join_confirmations
                (token, chat_id, group_key, requester_user_id, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (token, chat_id, _group_key(name), requester_user_id, str(expires_at)),
        )
        self.connection.commit()
        return token

    def confirm_group_join(self, token: str, owner_user_id: int) -> GroupDeletion:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            confirmation = self.connection.execute(
                """
                SELECT chat_id, group_key, requester_user_id, expires_at
                FROM group_join_confirmations WHERE token = ?
                """,
                (token,),
            ).fetchone()
            if confirmation is None:
                self.connection.rollback()
                return GroupDeletion(status="expired")
            if float(confirmation["expires_at"]) < datetime.now(UTC).timestamp():
                self.connection.execute(
                    "DELETE FROM group_join_confirmations WHERE token = ?", (token,)
                )
                self.connection.commit()
                return GroupDeletion(status="expired")

            group = self.connection.execute(
                """
                SELECT name FROM interest_groups
                WHERE chat_id = ? AND group_key = ? AND creator_user_id = ?
                """,
                (confirmation["chat_id"], confirmation["group_key"], owner_user_id),
            ).fetchone()
            if group is None:
                self.connection.rollback()
                return GroupDeletion(status="forbidden")

            self.connection.execute(
                "DELETE FROM group_join_confirmations WHERE token = ?", (token,)
            )
            self.connection.execute(
                """
                INSERT INTO interest_group_members (chat_id, group_key, user_id)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id, group_key, user_id) DO NOTHING
                """,
                (
                    confirmation["chat_id"],
                    confirmation["group_key"],
                    confirmation["requester_user_id"],
                ),
            )
            self.connection.commit()
            return GroupDeletion(status="accepted", name=group["name"])
        except Exception:
            self.connection.rollback()
            raise

    def confirm_group_deletion(self, token: str, requester_user_id: int) -> GroupDeletion:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            confirmation = self.connection.execute(
                """
                SELECT chat_id, group_key, requester_user_id, expires_at
                FROM group_delete_confirmations WHERE token = ?
                """,
                (token,),
            ).fetchone()
            if confirmation is None:
                self.connection.rollback()
                return GroupDeletion(status="expired")
            if confirmation["requester_user_id"] != requester_user_id:
                self.connection.rollback()
                return GroupDeletion(status="forbidden")

            self.connection.execute(
                "DELETE FROM group_delete_confirmations WHERE token = ?", (token,)
            )
            if float(confirmation["expires_at"]) < datetime.now(UTC).timestamp():
                self.connection.commit()
                return GroupDeletion(status="expired")

            group = self.connection.execute(
                """
                SELECT name FROM interest_groups
                WHERE chat_id = ? AND group_key = ? AND creator_user_id = ?
                """,
                (
                    confirmation["chat_id"],
                    confirmation["group_key"],
                    requester_user_id,
                ),
            ).fetchone()
            if group is None:
                self.connection.commit()
                return GroupDeletion(status="forbidden")

            self.connection.execute(
                "DELETE FROM interest_groups WHERE chat_id = ? AND group_key = ?",
                (confirmation["chat_id"], confirmation["group_key"]),
            )
            self.connection.commit()
            return GroupDeletion(status="deleted", name=group["name"])
        except Exception:
            self.connection.rollback()
            raise

    def cancel_group_deletion(self, token: str, requester_user_id: int) -> bool:
        cursor = self.connection.execute(
            """
            DELETE FROM group_delete_confirmations
            WHERE token = ? AND requester_user_id = ?
            """,
            (token, requester_user_id),
        )
        self.connection.commit()
        return cursor.rowcount == 1

    def claim_cooldown(self, chat_id: int, cooldown_seconds: int) -> int:
        """Claim the `/non_pinging_all` slot and return seconds to wait; zero means claimed."""
        now = datetime.now(UTC)
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            row = self.connection.execute(
                "SELECT last_all_at FROM chat_cooldowns WHERE chat_id = ?", (chat_id,)
            ).fetchone()
            if row is not None:
                elapsed = (now - datetime.fromisoformat(row["last_all_at"])).total_seconds()
                remaining = cooldown_seconds - elapsed
                if remaining > 0:
                    self.connection.rollback()
                    return max(1, int(remaining))

            self.connection.execute(
                """
                INSERT INTO chat_cooldowns (chat_id, last_all_at) VALUES (?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET last_all_at = excluded.last_all_at
                """,
                (chat_id, now.isoformat()),
            )
            self.connection.commit()
            return 0
        except Exception:
            self.connection.rollback()
            raise

    def close(self) -> None:
        self.connection.close()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _group_key(name: str) -> str:
    return " ".join(name.split()).casefold()
