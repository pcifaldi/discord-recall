"""Real-time Discord message capture via self-bot events."""

import discord
from loguru import logger

from discord_recall.config import get_settings
from discord_recall.db import get_session_factory
from discord_recall.db.ingest import mark_message_deleted, upsert_message


class Listener(discord.Client):
    def __init__(self):
        super().__init__()
        self._session_factory = get_session_factory()
        self._server_ids: set[int] = set(get_settings().server_ids)

    def _watching(self, guild_id: int | None) -> bool:
        if guild_id is None:
            return False
        if not self._server_ids:
            return True  # empty = watch all
        return guild_id in self._server_ids

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        watched = [g for g in self.guilds if self._watching(g.id)]
        ignored = [g for g in self.guilds if not self._watching(g.id)]
        logger.info(f"Watching {len(watched)} servers:")
        for guild in watched:
            logger.info(f"  + {guild.name} ({guild.id})")
        if ignored:
            logger.info(f"Ignoring {len(ignored)} servers:")
            for guild in ignored:
                logger.info(f"  - {guild.name} ({guild.id})")

    async def on_message(self, message: discord.Message):
        if not self._watching(getattr(message.guild, "id", None)):
            return
        try:
            async with self._session_factory() as session:
                await upsert_message(session, message)
                await session.commit()
            logger.debug(
                f"[{message.guild.name}/#{message.channel}] "
                f"{message.author}: {message.content[:80]}"
            )
        except Exception:
            logger.exception(f"Failed to ingest message {message.id}")

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not self._watching(getattr(after.guild, "id", None)):
            return
        try:
            async with self._session_factory() as session:
                await upsert_message(session, after)
                await session.commit()
            logger.debug(f"Edited message {after.id}")
        except Exception:
            logger.exception(f"Failed to ingest edit for message {after.id}")

    async def on_message_delete(self, message: discord.Message):
        try:
            async with self._session_factory() as session:
                await mark_message_deleted(session, message.id)
                await session.commit()
            logger.debug(f"Deleted message {message.id}")
        except Exception:
            logger.exception(f"Failed to mark message {message.id} as deleted")

    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        # Covers messages not in cache
        try:
            async with self._session_factory() as session:
                await mark_message_deleted(session, payload.message_id)
                await session.commit()
        except Exception:
            logger.exception(f"Failed to mark raw-deleted message {payload.message_id}")


def run_listener():
    settings = get_settings()
    if not settings.discord_token:
        raise SystemExit("DISCORD_TOKEN is not set in .env")

    logger.info("Starting Discord listener...")
    client = Listener()
    client.run(settings.discord_token, log_handler=None)
