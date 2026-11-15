from __future__ import annotations

from dataclasses import dataclass
from os import getenv
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Settings:
    token: str
    database_path: Path
    cooldown_seconds: int

    @classmethod
    def from_environment(cls) -> "Settings":
        load_dotenv()
        token = getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is not set")

        cooldown = int(getenv("PING_BOT_COOLDOWN_SECONDS", "300"))
        if cooldown < 0:
            raise RuntimeError("PING_BOT_COOLDOWN_SECONDS must not be negative")

        return cls(
            token=token,
            database_path=Path(getenv("PING_BOT_DATABASE_PATH", "data/ping_bot.sqlite3")),
            cooldown_seconds=cooldown,
        )
