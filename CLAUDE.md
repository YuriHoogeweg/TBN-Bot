# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Bot

```bash
python3 main.py
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Requires Python 3.11.

## Configuration

The bot reads from `devconfig.ini` (not `config.ini`) at startup. Copy `config.ini` as a template and fill in real values as `devconfig.ini`. The `Configuration` class (`config.py`) is a singleton that loads all settings on first access.

Key config sections:
- `[discord]` — TOKEN, GUILD_IDS (comma-separated list of server IDs), and various channel/role IDs
- `[openai]` — OpenAI API key
- `[grok]` — Grok (xAI) API key

Setting `GUILD_IDS` to your server ID(s) makes slash commands propagate immediately to those guilds. Add multiple IDs separated by commas to register commands on multiple guilds at once (e.g. `GUILD_IDS = 461610790114426882,987654321098765432`).

## Architecture

**Entry point:** `main.py` creates the `InteractionBot`, instantiates all cogs, and runs the bot.

**Cog pattern:** All features are implemented as disnake `commands.Cog` subclasses in `cogs/`. Slash commands use a plain `@commands.slash_command(...)` decorator with no `guild_ids` argument — guild registration is handled at the bot level via `test_guilds=Configuration.instance().GUILD_IDS` on `InteractionBot`.

**AI cog base class:** `cogs/shared/chatcompletion_cog.py` — `ChatCompletionCog` is a base class for cogs that need LLM responses. It supports both OpenAI and Grok backends. Call `set_message_context(sys_prompt, user_msgs, assistant_msgs)` in `__init__` to set up the few-shot prompt, then call `await get_response(message, placeholder_replacements, llm)` to get completions. The `%username%` placeholder is replaced at call time with the Discord user's display name.

**Cogs that extend `ChatCompletionCog`:**
- `SandBot` — `/sand` and `/sands_thoughts` commands, role-plays as "sand-fish"
- `CoryBot` — similar AI character bot
- `Birthdays` — uses OpenAI to generate birthday announcements

**Database:** SQLite via SQLAlchemy ORM. `database/tbnbotdatabase.py` defines models (`TbnMember`, `TbnMemberAudit`, `JoinTime`) and exports `database_session()`. The database file lives at `resources/tbn-bot-database.db`. Schema migrations are done manually via `add_column_if_not_exists()` — no Alembic migrations are used despite Alembic being in requirements.

**Stream announcer:** `StreamAnnouncer` listens to `on_presence_update`, detects new Twitch streams from members with the streamer role, and posts an AI-generated announcement. Rate-limited to once per hour per member via the database.

**Anonymous messaging:** `Anonymous` cog provides `/send_anonymous_channel_message` (posts an embed with a randomly-chosen online member's name as a decoy footer) and `/anon_last5` (admin view of recent anonymous messages, in-memory only). Sender identity is logged to `logs/anonymous_messages.log`.

**Logging:** `logger_config.py` sets up rotating file logs in `logs/app.log` (10MB max, 5 backups). Anonymous messages have a separate logger at `logs/anonymous_messages.log`.

**URL sanitizer:** `utils/url_sanitizer.py` — used by `StreamAnnouncer` to prevent LLMs from modifying stream URLs in their generated text.

**Drawing utilities:** `utils/drawing/` — Pillow/matplotlib-based image generation used by Dota-related cogs (`formulaone.py`, `cogs/sandbot.py` area for Dota stats).
