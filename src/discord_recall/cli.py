"""CLI entry point for discord-recall."""

import asyncio
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import typer

app = typer.Typer(name="discord-recall", help="Personal Discord intelligence system.")


@app.command()
def listen():
    """Start real-time Discord message capture."""
    from discord_recall.capture.listener import run_listener

    run_listener()


@app.command()
def backfill(
    channel_id: int = typer.Option(None, "--channel", "-c", help="Backfill a single channel by ID."),
    server_id: int = typer.Option(None, "--server", "-s", help="Backfill all channels in a server by ID."),
):
    """Backfill message history for a channel or entire server."""
    if not channel_id and not server_id:
        typer.echo("Provide --channel <id> or --server <id>")
        raise typer.Exit(1)

    from discord_recall.capture.backfill import run_backfill

    run_backfill(channel_id=channel_id, server_id=server_id)


@app.command()
def digest(
    server_id: int = typer.Option(None, "--server", "-s", help="Server ID to digest."),
    channel_id: int = typer.Option(None, "--channel", "-c", help="Single channel ID to digest."),
    date: str = typer.Option(None, "--date", "-d", help="Date to digest (YYYY-MM-DD). Default: yesterday."),
    send: bool = typer.Option(False, "--send", help="Send digest via Telegram."),
):
    """Generate a daily digest for a server or channel."""
    from discord_recall.digest.builder import build_daily_digest, build_server_daily_digest
    from discord_recall.digest.telegram import send_digest

    if date:
        day = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        day = datetime.now(timezone.utc) - timedelta(days=1)

    async def _run():
        if server_id:
            text = await build_server_daily_digest(server_id, day)
        elif channel_id:
            d = await build_daily_digest(channel_id, day)
            text = d.content if d else None
        else:
            typer.echo("Provide --server <id> or --channel <id>")
            raise typer.Exit(1)

        if not text:
            typer.echo("No activity found for that period.")
            return

        typer.echo(text)

        if send:
            await send_digest(text)

    asyncio.run(_run())


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question to ask about the conversations."),
    server_id: int = typer.Option(None, "--server", "-s", help="Scope to a server."),
    channel_id: int = typer.Option(None, "--channel", "-c", help="Scope to a channel."),
    user: str = typer.Option(None, "--user", "-u", help="Filter to a specific user."),
):
    """Ask a question about Discord conversations."""
    from discord_recall.digest.query import ask as ask_query

    async def _run():
        answer = await ask_query(
            question=question,
            channel_id=channel_id,
            server_id=server_id,
            username=user,
        )
        typer.echo(answer)

    asyncio.run(_run())


@app.command(name="digest-backfill")
def digest_backfill(
    channel_id: int = typer.Option(..., "--channel", "-c", help="Channel ID to backfill digests for."),
):
    """Backfill digests: monthly (>1yr), weekly (last year), daily (today onward)."""
    from discord_recall.digest.builder import backfill_digests

    asyncio.run(backfill_digests(channel_id))


@app.command()
def migrate():
    """Run database migrations (alembic upgrade head)."""
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
