# Discord Recall — Settings & Customization Reference

Every user-facing setting decision made during development, documented for future GUI/config panel implementation.

---

## Connection Settings

| Setting | Env Var | Type | Default | Description |
|---|---|---|---|---|
| Discord Token | `DISCORD_TOKEN` | string (secret) | — | User account token (self-bot). Obtained from browser DevTools → Network tab → Authorization header. |
| Database URL | `DATABASE_URL` | string | `postgresql+asyncpg://discord_recall:discord_recall@localhost:5433/discord_recall` | Async Postgres connection string. Port 5433 to avoid conflict with local Postgres on 5432. |

## Server & Channel Selection

| Setting | Env Var | Type | Default | Description |
|---|---|---|---|---|
| Watched Server IDs | `SERVER_IDS` | list[int] (JSON) | `[]` (all) | Which Discord servers to capture. Empty = capture all servers the account is in. User selected 3 out of 28 servers. |

**Design decision**: Server-level filtering only, not per-channel. Within a watched server, all readable channels are captured. This keeps config simple — most users want full server coverage. Per-channel filtering could be a future addition.

**GUI element**: Multi-select checklist of servers (populated from Discord connection). Show server name + icon + member count.

## LLM Provider

| Setting | Env Var | Type | Default | Description |
|---|---|---|---|---|
| OpenRouter API Key | `OPENROUTER_API_KEY` | string (secret) | — | API key from openrouter.ai. Chosen over direct Anthropic API for model flexibility. |
| Model | `OPENROUTER_MODEL` | string | `google/gemini-3.1-flash-lite` | Any OpenRouter-compatible model ID. User chose Gemini Flash Lite for cost efficiency on high-volume digest generation. |

**Design decision**: OpenRouter as the LLM gateway instead of direct provider SDKs. Allows swapping models without code changes — just change one env var. Uses OpenAI-compatible chat completions API via raw httpx calls (no SDK dependency).

**GUI element**: Dropdown of popular models with cost/speed indicators. Text field for custom model ID. API key field with show/hide toggle.

## Telegram Delivery

| Setting | Env Var | Type | Default | Description |
|---|---|---|---|---|
| Telegram Bot Token | `TELEGRAM_BOT_TOKEN` | string (secret) | — | Bot token from @BotFather. |
| Telegram Chat ID | `TELEGRAM_CHAT_ID` | string | — | Chat/channel/group ID to send digests to. |

**GUI element**: Setup wizard — "Send a message to your bot, we'll auto-detect the chat ID."

## Backfill Settings

| Setting | Env Var | Type | Default | Description |
|---|---|---|---|---|
| Batch Size | `BACKFILL_BATCH_SIZE` | int | `100` | Messages fetched per Discord API call during backfill. |
| Delay Between Batches | `BACKFILL_DELAY_SECONDS` | float | `1.0` | Pause between batches to avoid rate limits. |

**Design decision**: Conservative defaults (100 msgs, 1s delay) to avoid Discord rate limiting / account flags. Power users could increase batch size and decrease delay, but the risk is account termination.

**GUI element**: Slider for batch size (50-200). Slider for delay (0.5-5.0s). Warning badge if settings are aggressive.

## Digest Settings

| Setting | Location | Type | Current Value | Description |
|---|---|---|---|---|
| Chunk Size | `builder.py:CHUNK_SIZE` | int | `400` | Max messages per LLM call. Larger values = fewer API calls but risk context window limits. |
| Digest Backfill Tiers | `builder.py:backfill_digests()` | hardcoded | see below | How historical digests are generated. |

### Digest Tier Strategy

| Period | Coverage | Rationale |
|---|---|---|
| **Monthly** | Messages older than 1 year | Compresses years of history into manageable summaries without thousands of LLM calls. |
| **Weekly** | Last 12 months to today | More granular for recent history where details still matter. |
| **Daily** | Today onward (real-time) | Full resolution for current activity. Generated on-demand or scheduled. |

**Design decision**: Tiered approach avoids the cost of generating hourly/daily digests for 5 years of history. Monthly digests for old data, weekly for recent, daily going forward. As an example, a busy channel with ~120,000 messages spanning ~5 years would need ~1,850 LLM calls for daily digests vs ~100 with the tiered approach.

**GUI element**: Date pickers for tier boundaries. Dropdown for each tier's granularity. "Estimate cost" button that counts messages per period and shows projected API calls.

## LLM System Prompts

| Prompt | Location | Purpose |
|---|---|---|
| `DIGEST_SYSTEM` | `builder.py` | Summarizes raw message transcripts into digests. Emphasizes conciseness, user attribution, capturing debates, no editorializing. |
| `SYNTHESIS_SYSTEM` | `builder.py` | Synthesizes multiple chunk summaries into a single coherent digest. Used when a period has more messages than `CHUNK_SIZE`. |
| `QUERY_SYSTEM` | `query.py` | Answers user questions from context (wiki pages + digests + raw messages). Emphasizes citing sources, distinguishing data from inference. |

**GUI element**: Editable text areas with "Reset to default" buttons. Preview of what the prompt produces on a sample.

---

## Future Settings (Not Yet Implemented)

These are settings that will likely be needed as features are built out:

- **Per-channel filtering**: Include/exclude specific channels within a watched server
- **Digest schedule**: Cron expression or simple picker for automated daily digest generation
- **Telegram format**: Markdown vs plain text, summary length preference
- **Query model override**: Use a different (smarter/larger) model for queries vs digests
- **Wiki update frequency**: How often wiki pages get refreshed from new digests
- **Notification filters**: Keywords or users that trigger immediate Telegram alerts vs batched digests
