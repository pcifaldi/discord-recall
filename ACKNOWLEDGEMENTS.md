# Acknowledgements

This project stands on the shoulders of a lot of excellent open-source work.

## Inspiration & core library

- **[discord.py-self](https://github.com/dolfies/discord.py-self)** by
  [**dolfies**](https://github.com/dolfies) and its contributors — the
  user-account (self-bot) library that makes message capture possible, and the
  primary inspiration for this project. Thank you to dolfies and everyone who
  maintains it.
- **[discord.py](https://github.com/Rapptz/discord.py)** by
  [Rapptz](https://github.com/Rapptz) and contributors — the original library
  that `discord.py-self` is forked from.

## Built with

- [SQLAlchemy](https://www.sqlalchemy.org/) & [Alembic](https://alembic.sqlalchemy.org/) — ORM and migrations
- [Typer](https://typer.tiangolo.com/) — the CLI
- [Pydantic](https://docs.pydantic.dev/) & [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) — config and validation
- [httpx](https://www.python-httpx.org/) — async HTTP client for the LLM calls
- [python-telegram-bot](https://python-telegram-bot.org/) — Telegram delivery
- [loguru](https://github.com/Delgan/loguru) — logging
- [OpenRouter](https://openrouter.ai/) — LLM gateway for enrichment/summarization
- [uv](https://github.com/astral-sh/uv) — Python packaging and environment management

## A note on ethics

Capturing messages with a user-account self-bot **violates Discord's Terms of
Service** and can get accounts terminated. This project exists for personal
research and educational purposes. Please respect the privacy of the people in
the communities you participate in, and the licenses and terms of every tool
listed above.
