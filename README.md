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

   To allow any group member to run every command, start it with:

   ```bash
   poetry run python -m ping_bot --dont-require-admin
   ```

4. Add the bot to a group. It needs permission to send messages. Making it an administrator lets it remember authors of all normal messages; otherwise users can register themselves with `/add`. `/all` is restricted to the group's owner and administrators.

## Behaviour

- The database is SQLite and defaults to `data/ping_bot.sqlite3`.
- Each `(chat_id, user_id)` pair is unique. A later message refreshes the display name, username and `last_seen_at`.
- `/all` uses `@username` when it is known, so Telegram sends a standard mention notification. Users without a username are mentioned via an ID-based inline mention instead.
- `/add` registers the user who sends it even if the bot is not an administrator. Used as a reply, it also registers the author of the replied-to message when Telegram includes that author in the update. With Privacy Mode enabled, use `/add@your_bot_username` if Telegram does not otherwise deliver the command to the bot.
- Group administrators can use `/addmany 123456789 987654321` to add up to 100 positive numeric Telegram IDs at once. For every ID, the bot tries `getChatMember` first and stores the member's current name and `@username` when Telegram permits it; otherwise it stores a placeholder that is refreshed when the user sends a message.
- By default only group administrators can run `/all` and `/addmany`. The `--dont-require-admin` start flag removes administrator checks from both commands.
- Mentions are split into several messages to stay below Telegram's 4096-character message limit. The bot applies a per-group cooldown (five minutes by default).
- User records are removed when Telegram supplies a `chat_member` update saying that the user left or was removed. Historical records may still exist if the bot was not present when the departure happened.

Do not use this for unsolicited mass pings. The cooldown and administrator-only command are safeguards, not a substitute for the group's rules.
