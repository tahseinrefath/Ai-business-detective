"""XP, levels and badges - a light 'detective rank' system based on what the user actually did."""
from src.database.db import get_db

XP = {"upload": 10, "investigate": 5, "report": 15, "whatif": 5, "note": 3, "goal": 5}
LEVELS = ["Rookie", "Analyst", "Detective", "Inspector", "Chief Inspector", "Legend"]
XP_PER_LEVEL = 40
BADGES = [  # id, icon, name, how to earn, test(counts, has_avatar)
    ("first_case", "🕵️", "First Case", "Upload your first dataset", lambda c, a: c["upload"] >= 1),
    ("sharp_eye", "🔍", "Sharp Eye", "Run 5 investigations", lambda c, a: c["investigate"] >= 5),
    ("case_closed", "📄", "Case Closed", "Generate a report", lambda c, a: c["report"] >= 1),
    ("mad_scientist", "🧪", "Mad Scientist", "Run 3 what-if scenarios", lambda c, a: c["whatif"] >= 3),
    ("note_taker", "📝", "Note Taker", "Write 3 case notes", lambda c, a: c["note"] >= 3),
    ("goal_setter", "🎯", "Goal Setter", "Set a monthly goal", lambda c, a: c["goal"] >= 1),
    ("face_of_case", "🖼️", "Face of the Case", "Upload a profile picture", lambda c, a: a),
    ("data_wrangler", "🧹", "Data Wrangler", "Upload 3 datasets", lambda c, a: c["upload"] >= 3),
]


def record(user_id: int, kind: str):
    db = get_db()
    db.execute("INSERT INTO events (user_id, kind) VALUES (?, ?)", (user_id, kind))
    db.commit()


def counts(user_id: int) -> dict:
    rows = get_db().execute("SELECT kind, COUNT(*) n FROM events WHERE user_id = ? GROUP BY kind", (user_id,)).fetchall()
    c = {k: 0 for k in XP}
    c.update({r["kind"]: r["n"] for r in rows})
    return c


def summary(user_id: int, has_avatar: bool | None = None) -> dict:
    from src.auth.security import avatar_path
    c = counts(user_id)
    xp = sum(XP[k] * c.get(k, 0) for k in XP)
    level = xp // XP_PER_LEVEL + 1
    has_avatar = avatar_path(user_id).exists() if has_avatar is None else has_avatar
    return {
        "xp": xp, "level": level, "title": LEVELS[min(level - 1, len(LEVELS) - 1)],
        "xp_into_level": xp % XP_PER_LEVEL, "xp_per_level": XP_PER_LEVEL, "counts": c,
        "badges": [{"id": i, "icon": ic, "name": n, "how": h, "earned": bool(t(c, has_avatar))} for i, ic, n, h, t in BADGES],
    }
