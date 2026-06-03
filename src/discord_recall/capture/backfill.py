"""Channel history backfill — paginate through Discord channel history."""

import asyncio
from datetime import datetime, timezone

import discord
from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert

from discord_recall.config import get_settings
from discord_recall.db import get_session_factory
from discord_recall.db.ingest import upsert_channel, upsert_thread, upsert_message
from discord_recall.db.models import BackfillStatus, ChannelBackfillState


async def _get_backfill_state(session, channel_id: int) -> ChannelBackfillState | None:
    result = await session.execute(
        select(ChannelBackfillState).where(ChannelBackfillState.channel_id == channel_id)
    )
    return result.scalar_one_or_none()


async def _set_backfill_status(session, channel_id: int, status: BackfillStatus, **kwargs):
    values = dict(channel_id=channel_id, status=status.value, **kwargs)
    stmt = insert(ChannelBackfillState).values(**values).on_conflict_do_update(
        index_elements=[ChannelBackfillState.channel_id],
        set_=dict(status=status.value, **kwargs),
    )
    await session.execute(stmt)
    await session.commit()


async def backfill_channel(client: discord.Client, channel: discord.TextChannel | discord.Thread):
    """Backfill a single channel's message history."""
    settings = get_settings()
    session_factory = get_session_factory()
    batch_size = settings.backfill_batch_size
    delay = settings.backfill_delay_seconds

    is_thread = isinstance(channel, discord.Thread)
    channel_name = f"#{channel.name}" if hasattr(channel, "name") else str(channel.id)
    guild_name = channel.guild.name if channel.guild else "unknown"

    # Ensure channel/server rows exist before tracking backfill state
    async with session_factory() as session:
        if is_thread:
            await upsert_thread(session, channel)
        else:
            await upsert_channel(session, channel)
        await session.commit()

    # channel_backfill_state FK references channels table.
    # Threads live in the threads table, so we track by parent channel for threads.
    track_id = channel.parent_id if is_thread else channel.id

    # Check existing state for resume
    async with session_factory() as session:
        state = await _get_backfill_state(session, track_id)
        after_msg_id = state.last_message_id if state else None

    if state and state.status == BackfillStatus.complete:
        logger.info(f"[{guild_name}/{channel_name}] Already complete, skipping")
        return

    logger.info(
        f"[{guild_name}/{channel_name}] Starting backfill"
        + (f" (resuming after {after_msg_id})" if after_msg_id else "")
    )

    # Mark in progress
    async with session_factory() as session:
        await _set_backfill_status(session, track_id, BackfillStatus.in_progress)

    total = 0
    last_id = after_msg_id
    after = discord.Object(id=after_msg_id) if after_msg_id else None

    try:
        while True:
            batch = []
            async for msg in channel.history(limit=batch_size, after=after, oldest_first=True):
                batch.append(msg)

            if not batch:
                break

            async with session_factory() as session:
                for msg in batch:
                    await upsert_message(session, msg)
                await session.commit()

            last_id = batch[-1].id
            total += len(batch)
            after = discord.Object(id=last_id)

            # Save progress
            async with session_factory() as session:
                await _set_backfill_status(
                    session,
                    track_id,
                    BackfillStatus.in_progress,
                    last_message_id=last_id,
                    backfilled_through=batch[-1].created_at,
                )

            logger.info(f"[{guild_name}/{channel_name}] {total} messages so far...")

            if len(batch) < batch_size:
                break

            await asyncio.sleep(delay)

        # Mark complete
        async with session_factory() as session:
            await _set_backfill_status(
                session,
                track_id,
                BackfillStatus.complete,
                last_message_id=last_id,
                backfilled_through=datetime.now(timezone.utc),
            )

        logger.info(f"[{guild_name}/{channel_name}] Backfill complete — {total} messages")

    except Exception:
        async with session_factory() as session:
            await _set_backfill_status(
                session,
                track_id,
                BackfillStatus.failed,
                last_message_id=last_id,
            )
        logger.exception(f"[{guild_name}/{channel_name}] Backfill failed after {total} messages")
        raise


async def backfill_server(client: discord.Client, guild: discord.Guild):
    """Backfill all text channels and threads in a server."""
    logger.info(f"Backfilling server: {guild.name} ({guild.id})")

    # Text channels
    text_channels = [ch for ch in guild.channels if isinstance(ch, discord.TextChannel)]
    text_channels.sort(key=lambda c: c.position or 0)

    for ch in text_channels:
        try:
            await backfill_channel(client, ch)
        except discord.Forbidden:
            logger.warning(f"  No access to #{ch.name}, skipping")
        except Exception:
            logger.exception(f"  Failed to backfill #{ch.name}")

    # Active threads
    try:
        threads = await guild.active_threads()
        for thread in threads:
            try:
                await backfill_channel(client, thread)
            except discord.Forbidden:
                logger.warning(f"  No access to thread #{thread.name}, skipping")
            except Exception:
                logger.exception(f"  Failed to backfill thread #{thread.name}")
    except Exception:
        logger.exception("  Failed to fetch active threads")

    logger.info(f"Server backfill complete: {guild.name}")


class BackfillClient(discord.Client):
    """Ephemeral client that connects, runs backfill, then disconnects."""

    def __init__(self, channel_id: int | None = None, server_id: int | None = None):
        super().__init__()
        self._target_channel_id = channel_id
        self._target_server_id = server_id

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} for backfill")
        try:
            if self._target_channel_id:
                channel = self.get_channel(self._target_channel_id)
                if channel is None:
                    channel = await self.fetch_channel(self._target_channel_id)
                await backfill_channel(self, channel)

            elif self._target_server_id:
                guild = self.get_guild(self._target_server_id)
                if guild is None:
                    logger.error(f"Server {self._target_server_id} not found")
                else:
                    await backfill_server(self, guild)
        except Exception:
            logger.exception("Backfill failed")
        finally:
            await self.close()


def run_backfill(channel_id: int | None = None, server_id: int | None = None):
    settings = get_settings()
    if not settings.discord_token:
        raise SystemExit("DISCORD_TOKEN is not set in .env")

    client = BackfillClient(channel_id=channel_id, server_id=server_id)
    client.run(settings.discord_token, log_handler=None)
