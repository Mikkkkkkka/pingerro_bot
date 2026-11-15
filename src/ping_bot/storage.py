from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Member:
    user_id: int
    full_name: str
    username: str | None


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

    def claim_cooldown(self, chat_id: int, cooldown_seconds: int) -> int:
        """Claim the `/all` slot and return seconds to wait; zero means claimed."""
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
