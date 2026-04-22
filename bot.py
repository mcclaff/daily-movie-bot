import json, os, random, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo
import pysrt, requests

# ===== CONFIG — edit these for your setup =====
TZ = ZoneInfo("UTC")   # any IANA tz name, e.g. "America/New_York", "Australia/Sydney"
WINDOWS = [            # (label, start_hour, end_hour) — local to TZ, 24h, end exclusive
    ("morning",   8, 10),   #  8:00–10:00
    ("midday",   12, 15),   # 12:00–15:00
    ("evening",  19, 22),   # 19:00–22:00
]
SRT_PATH = "source.srt"
# ==============================================

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
STATE_PATH = "state.json"

def target_minute(label, start_h, end_h):
    """Post time for this window. Pinned to the window start so *any* cron run
    inside the window fires, maximizing resilience against GitHub cron drift."""
    return start_h * 60

def load_state():
    today = datetime.now(TZ).date().isoformat()
    try:
        with open(STATE_PATH) as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}
    if state.get("date") != today:
        state = {"date": today, "fired": []}
    return state

def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")

def is_pure_annotation(text):
    """True if the cue is only stage directions like [SIREN WAILING], music notes, etc."""
    stripped = re.sub(r'<[^>]+>', '', text).strip()
    if not stripped:
        return True
    no_brackets = re.sub(r'\[[^\]]*\]', '', stripped).strip()
    no_brackets = re.sub(r'^[-\s♪♫]+$', '', no_brackets).strip()
    return not no_brackets

def clean_line(text):
    return re.sub(r'<[^>]+>', '', text).replace("\n", " ").strip()

def pick_block():
    subs = [s for s in pysrt.open(SRT_PATH) if not is_pure_annotation(s.text)]
    start = random.randint(0, max(0, len(subs) - 3))
    n = random.choice([2, 3])
    lines = [clean_line(subs[i].text) for i in range(start, min(start + n, len(subs)))]
    return "\n".join(lines)

def send(text):
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text},
    )
    r.raise_for_status()

def pending_window(state):
    """First window whose target has passed, is still inside the window, and hasn't fired yet."""
    now = datetime.now(TZ)
    now_min = now.hour * 60 + now.minute
    for label, sh, eh in WINDOWS:
        if label in state.get("fired", []):
            continue
        t = target_minute(label, sh, eh)
        if t <= now_min < eh * 60:
            return label, t
    return None

if __name__ == "__main__":
    # Manual trigger: always post, don't touch state.
    if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        msg = pick_block()
        send(msg)
        print("Posted (manual):", msg)
        sys.exit(0)

    state = load_state()
    hit = pending_window(state)
    if hit is None:
        print(f"No window pending. State: {state}")
        print("Targets today (local time):")
        for label, sh, eh in WINDOWS:
            t = target_minute(label, sh, eh)
            print(f"  {label:8s} {t // 60:02d}:{t % 60:02d}  ({'fired' if label in state.get('fired', []) else 'pending'})")
        sys.exit(0)

    label, t = hit
    msg = pick_block()
    send(msg)
    state["fired"].append(label)
    save_state(state)
    print(f"Posted ({label}, target {t // 60:02d}:{t % 60:02d}):", msg)
