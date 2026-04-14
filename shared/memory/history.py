import os
import json
import datetime


HISTORY_DIR = os.path.expanduser("~/orcas-reports/history")


def save_session(history: list, agent_chain: list = None):
    \"\"\"Save a completed session to disk as JSON.\"\"\"
    os.makedirs(HISTORY_DIR, exist_ok=True)

    ts       = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"session_{ts}.json"
    filepath = os.path.join(HISTORY_DIR, filename)

    data = {
        "timestamp"  : datetime.datetime.now().isoformat(),
        "agents_used": agent_chain or [],
        "turns"      : len(history) // 2,
        "messages"   : history,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return filepath


def load_last_session() -> list:
    \"\"\"Load the most recent saved session.\"\"\"
    if not os.path.exists(HISTORY_DIR):
        return []

    files = sorted([
        f for f in os.listdir(HISTORY_DIR)
        if f.startswith("session_") and f.endswith(".json")
    ])

    if not files:
        return []

    latest = os.path.join(HISTORY_DIR, files[-1])
    try:
        with open(latest, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("messages", [])
    except Exception:
        return []


def list_sessions() -> str:
    \"\"\"List all saved sessions.\"\"\"
    if not os.path.exists(HISTORY_DIR):
        return "No sessions saved yet."

    files = sorted([
        f for f in os.listdir(HISTORY_DIR)
        if f.startswith("session_") and f.endswith(".json")
    ])

    if not files:
        return "No sessions saved yet."

    lines = [f"SAVED SESSIONS ({len(files)} total)", "="*40]
    for f in files[-10:]:   # show last 10
        path = os.path.join(HISTORY_DIR, f)
        try:
            with open(path) as fp:
                data = json.load(fp)
            lines.append(
                f"{f}  |  {data.get('turns', 0)} turns  |  "
                f"agents: {', '.join(data.get('agents_used', []))}"
            )
        except Exception:
            lines.append(f"{f}  |  [unreadable]")

    return "\n".join(lines)
