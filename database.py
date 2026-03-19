import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "interviews.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS interviews (
            id TEXT PRIMARY KEY,
            candidate TEXT NOT NULL,
            recruiter TEXT NOT NULL,
            time TEXT NOT NULL,
            meeting_link TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_interview(interview):
    conn = get_connection()
    conn.execute("""
        INSERT INTO interviews (id, candidate, recruiter, time, meeting_link)
        VALUES (:id, :candidate, :recruiter, :time, :meeting_link)
    """, interview)
    conn.commit()
    conn.close()

def get_all_interviews():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM interviews ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_interview_by_id(interview_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM interviews WHERE id = ?", (interview_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

    