# Ping bot

Telegram bot for group chats. It remembers non-bot users who write messages in each group and lets a group administrator call `/all` to mention those users.

Telegram does not provide bots with a full member list. Therefore `/all` contains only members seen by the bot after it was added to the group. The bot must be a group administrator to receive all normal messages.

Use `/help` in Telegram to see the bot's commands and limitations.

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

   To allow any group member to run every command, start it with:

   ```bash
   poetry run python -m ping_bot --dont-require-admin
   ```

4. Add the bot to a group. It needs permission to send messages. Making it an administrator lets it remember authors of all normal messages; otherwise users can register themselves with `/add`. `/all` and `/all_copy` are restricted to the group's owner and administrators.

## Behaviour

- SQLite is the default database at `data/ping_bot.sqlite3`. To use PostgreSQL, set `PING_BOT_DATABASE_URL=postgresql://user:password@host:5432/database` in `.env`; it takes precedence over `PING_BOT_DATABASE_PATH`. The common `DATABASE_URL` name is also accepted.
- Each `(chat_id, user_id)` pair is unique. A later message refreshes the display name, username and `last_seen_at`.
- `/all` uses `@username` when it is known. Users without a username are mentioned via an ID-based inline mention instead.
- Before `/all`, `/all_copy`, `/group` and `/group_copy`, the bot tries to refresh members missing a username via `getChatMember` when Telegram permits it.
- `/all_copy` (alias: `/allc`) sends copy buttons containing `@username` lists. Copy and send each fragment from a user account when notification delivery from the bot is not suitable. Telegram limits every copied fragment to 256 characters.
- Groups are chat-scoped: `/add_group <name>` creates a group on first use and makes that member its owner. For an existing group it sends a five-minute application that only the owner can approve. A group owner can also use `/addmany_group <name> <ID...>` to add up to 100 users directly. Use `/group <name>`, `/groups`, `/remove_group <name>`, `/delete_group <name>` and `/group_copy <name>` (alias: `/groupc`) to manage and use groups. Only the group's owner can delete it. If the owner leaves using `/remove_group`, ownership is transferred randomly to a remaining member; an empty group is deleted.
- `/add` registers the user who sends it even if the bot is not an administrator. Used as a reply, it also registers the author of the replied-to message when Telegram includes that author in the update. With Privacy Mode enabled, use `/add@your_bot_username` if Telegram does not otherwise deliver the command to the bot.
- Group administrators can use `/addmany 123456789 987654321` to add up to 100 positive numeric Telegram IDs at once. For every ID, the bot tries `getChatMember` first and stores the member's current name and `@username` when Telegram permits it; otherwise it stores a placeholder that is refreshed when the user sends a message.
- By default only group administrators can run `/all`, `/all_copy` and `/addmany`. The `--dont-require-admin` start flag removes their administrator checks.
- Mentions are split into several messages to stay below Telegram's 4096-character message limit. The bot applies a per-group cooldown (five minutes by default).
- User records are removed when Telegram supplies a `chat_member` update saying that the user left or was removed. Historical records may still exist if the bot was not present when the departure happened.

Do not use this for unsolicited mass pings. The cooldown and administrator-only command are safeguards, not a substitute for the group's rules.
