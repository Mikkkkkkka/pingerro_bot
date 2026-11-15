from __future__ import annotations

from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Settings:
    token: str
    database_url: str
    cooldown_seconds: int

    @classmethod
    def from_environment(cls) -> "Settings":
        load_dotenv()
        token = getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is not set")

        cooldown = int(getenv("PING_BOT_COOLDOWN_SECONDS", "10"))
        if cooldown < 0:
            raise RuntimeError("PING_BOT_COOLDOWN_SECONDS must not be negative")

        database_url = getenv("PING_BOT_DATABASE_URL") or getenv("DATABASE_URL")
        if database_url is None:
            database_url = getenv("PING_BOT_DATABASE_PATH", "data/ping_bot.sqlite3")

        return cls(
            token=token,
            database_url=database_url,
            cooldown_seconds=cooldown,
        )
