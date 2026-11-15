# Ping bot

Telegram bot for group chats. It remembers non-bot users who write messages in each group and lets a group administrator call `/all` to mention those users.

Telegram does not provide bots with a full member list. Therefore `/all` contains only members seen by the bot after it was added to the group. The bot must be a group administrator to receive all normal messages.

## Setup

1. Create a bot with [@BotFather](https://t.me/BotFather) and put its token in `.env` (use `.env.example` as a template).
2. Install dependencies with Poetry:

   ```bash
   poetry install
   ```

3. Run it:

   ```bash
   poetry run python -m ping_bot
   ```

4. Add the bot to a group as an administrator. It needs permission to send messages. `/all` is restricted to the group's owner and administrators.

## Behaviour

- The database is SQLite and defaults to `data/ping_bot.sqlite3`.
- Each `(chat_id, user_id)` pair is unique. A later message refreshes the display name, username and `last_seen_at`.
- `/all` uses ID-based inline mentions, so a public `@username` is not required.
- Mentions are split into several messages to stay below Telegram's 4096-character message limit. The bot applies a per-group cooldown (five minutes by default).
- User records are removed when Telegram supplies a `chat_member` update saying that the user left or was removed. Historical records may still exist if the bot was not present when the departure happened.

Do not use this for unsolicited mass pings. The cooldown and administrator-only command are safeguards, not a substitute for the group's rules.
