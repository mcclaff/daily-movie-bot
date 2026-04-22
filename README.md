# Daily Movie Bot

Posts random 2–3 line excerpts from an SRT subtitle file into a Telegram channel at randomized times each day. Runs for free on GitHub Actions — no server required.

Good for: sharing memorable dialogue from a favorite movie, show, or podcast transcript with a group, one snippet at a time.

## How it works

Three configurable posting windows per day. For each window, today's date is hashed into a deterministic pseudo-random target minute. A cron job runs every 30 minutes, and the first one that lands at or after the target fires that window's post. A small `state.json` (auto-committed by the workflow) tracks which windows have fired today so nothing double-posts and cron skips can be caught up.

Timezones are handled by `zoneinfo`, so DST is automatic.

## Setup

1. **Create a Telegram bot.** Message [@BotFather](https://t.me/BotFather) → `/newbot` → save the token it gives you. The bot's username ends in `_bot`.

2. **Add the bot to your channel.** Make it an **administrator** with at least the "Post Messages" permission. Channels don't let regular-member bots post.

3. **Find the channel's chat ID.** Post any message in the channel yourself, then open this URL in a browser (put your token right after `bot`, no space):

   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```

   Look for `"chat":{"id":...}`. Channel IDs are negative, e.g. `-1001234567890`. If you see `{"result":[]}`, post another message after adding the bot and refresh.

4. **Use this template.** Click **"Use this template"** on this repo, then clone your new copy locally.

5. **Set GitHub Actions secrets.** In your new repo: **Settings → Secrets and variables → Actions → New repository secret**. Add both:
   - `TELEGRAM_BOT_TOKEN` — the token from BotFather
   - `TELEGRAM_CHAT_ID` — the chat ID from step 3

6. **Add your SRT.** Save your subtitle file as `source.srt` in the repo root and commit it. See `source.srt.example` for the expected format.

7. **Edit `bot.py`'s CONFIG block.** Change the timezone and windows to your preference (see Config below).

8. **Smoke-test.** Push your changes, then go to **Actions → Daily Telegram Ping → Run workflow**. A random snippet should land in your channel within seconds.

## Config

Near the top of `bot.py`:

```python
TZ = ZoneInfo("UTC")   # any IANA tz name, e.g. "America/New_York", "Australia/Sydney"
WINDOWS = [
    ("morning",   8, 10),   #  8:00–10:00 local
    ("midday",   12, 15),   # 12:00–15:00 local
    ("evening",  19, 22),   # 19:00–22:00 local
]
SRT_PATH = "source.srt"
```

- `TZ` — any [IANA timezone name](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).
- `WINDOWS` — list of `(label, start_hour, end_hour)` tuples. Hours are local, 24-hour clock, end exclusive. Each window posts once per day at a random minute inside it. Labels must be unique; they're used as hash salts.
- Fewer or more windows work fine — the code loops over whatever's in the list.

## Gotchas

- **First scheduled runs will fail until you finish setup.** Once you create your repo from the template, GitHub starts firing the cron immediately — runs before you've set `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and dropped in a `source.srt` will show as red in the Actions tab. That's expected; they'll start passing once everything's in place.
- **Cron drift.** GitHub's scheduled workflows drift 5–20 min on good days and sometimes skip entire hours. The state-file logic lets a later cron run in the same window catch up, but a cron blackout for the full remaining window still results in a missed post.
- **SRT speaker labels are inconsistent.** Most SRTs tag speakers on only some lines (e.g. `VINCENT: …`, `ALICE: …`). The bot preserves whatever's in the text — it doesn't invent speaker info.
- **Stage directions are filtered.** Cues that are purely annotations like `[SIREN WAILING]` or `[APPLAUSE]` are skipped, and `<i>…</i>` italics tags are stripped. Inline annotations embedded inside dialogue are left alone.
- **Variety.** A typical 1,500-line feature-film SRT yields a few thousand possible 2–3 line blocks. At three posts a day, that's multi-year variety before repeats become likely.
- **Actions minutes.** Every-30-min cron uses ~1,440 minutes/month, inside the 2,000-min free tier for private repos. Public repos get unlimited Actions minutes.

## Files

- `bot.py` — posting logic
- `requirements.txt` — `pysrt`, `requests`
- `.github/workflows/daily-ping.yml` — GitHub Actions cron + commit-back-state
- `state.json` — auto-managed; tracks which windows have fired today
- `source.srt` — **you provide this**
- `source.srt.example` — minimal example showing the SRT format

## License

MIT. See [LICENSE](LICENSE).
