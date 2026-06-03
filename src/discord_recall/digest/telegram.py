"""Telegram delivery for digests."""

from loguru import logger
from telegram import Bot
from telegram.constants import ParseMode

from discord_recall.config import get_settings

MAX_MESSAGE_LENGTH = 4096


async def send_digest(text: str) -> None:
    """Send a digest to the configured Telegram chat, splitting if needed."""
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.warning("Telegram not configured, printing to stdout instead")
        print(text)
        return

    bot = Bot(token=settings.telegram_bot_token)

    # Split long messages
    chunks = _split_message(text)
    for i, chunk in enumerate(chunks):
        try:
            await bot.send_message(
                chat_id=settings.telegram_chat_id,
                text=chunk,
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            # Retry without markdown if parsing fails
            try:
                await bot.send_message(
                    chat_id=settings.telegram_chat_id,
                    text=chunk,
                )
            except Exception:
                logger.exception(f"Failed to send Telegram message chunk {i+1}/{len(chunks)}")

    logger.info(f"Sent digest to Telegram ({len(chunks)} message(s))")


def _split_message(text: str) -> list[str]:
    """Split text into chunks that fit Telegram's message limit."""
    if len(text) <= MAX_MESSAGE_LENGTH:
        return [text]

    chunks = []
    while text:
        if len(text) <= MAX_MESSAGE_LENGTH:
            chunks.append(text)
            break

        # Find a good split point (prefer paragraph breaks)
        split_at = text.rfind("\n\n", 0, MAX_MESSAGE_LENGTH)
        if split_at == -1:
            split_at = text.rfind("\n", 0, MAX_MESSAGE_LENGTH)
        if split_at == -1:
            split_at = MAX_MESSAGE_LENGTH

        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")

    return chunks
