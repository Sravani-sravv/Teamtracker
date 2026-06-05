from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import os

app = FastAPI(title="Team Availability Tracker")

# Allow frontend (any origin) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "team.db"

# ─── Database setup ───────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT    NOT NULL,
            role      TEXT    NOT NULL,
            available INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Seed default members only if table is empty
    count = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]
    if count == 0:
        seed = [
            ("Priya Sharma",   "Frontend Dev",    1),
            ("Arjun Mehta",    "Backend Dev",     0),
            ("Sneha Reddy",    "UI/UX Designer",  1),
            ("Kiran Patel",    "DevOps Engineer", 1),
            ("Nisha Gupta",    "ML Engineer",     0),
            ("Rahul Verma",    "QA Engineer",     1),
        ]
        conn.executemany(
            "INSERT INTO members (name, role, available) VALUES (?, ?, ?)", seed
        )
    conn.commit()
    conn.close()

init_db()

# ─── Schemas ──────────────────────────────────────────────────────
class MemberCreate(BaseModel):
    name: str
    role: str
    available: bool = True

class AvailabilityUpdate(BaseModel):
    available: bool

# ─── Routes ───────────────────────────────────────────────────────

@app.get("/members")
def get_all_members():
    """Return all team members."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM members ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/members", status_code=201)
def add_member(member: MemberCreate):
    """Add a new team member."""
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO members (name, role, available) VALUES (?, ?, ?)",
        (member.name, member.role, int(member.available))
    )
    conn.commit()
    new_id = cur.lastrowid
    row = conn.execute("SELECT * FROM members WHERE id = ?", (new_id,)).fetchone()
    conn.close()
    return dict(row)


@app.patch("/members/{member_id}/availability")
def update_availability(member_id: int, body: AvailabilityUpdate):
    """Toggle availability for a specific member."""
    conn = get_db()
    row = conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Member not found")
    conn.execute(
        "UPDATE members SET available = ?, updated_at = datetime('now') WHERE id = ?",
        (int(body.available), member_id)
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
    conn.close()
    return dict(updated)


@app.delete("/members/{member_id}", status_code=204)
def delete_member(member_id: int):
    """Remove a team member."""
    conn = get_db()
    row = conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Member not found")
    conn.execute("DELETE FROM members WHERE id = ?", (member_id,))
    conn.commit()
    conn.close()


@app.get("/stats")
def get_stats():
    """Return quick availability stats."""
    conn = get_db()
    total     = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]
    available = conn.execute("SELECT COUNT(*) FROM members WHERE available = 1").fetchone()[0]
    conn.close()
    return {"total": total, "available": available, "busy": total - available}
