import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = "profbot.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            role TEXT DEFAULT 'participant',
            registered_at TEXT
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            date TEXT,
            place TEXT,
            equipment TEXT,
            safety_rules TEXT,
            max_participants INTEGER DEFAULT 0,
            created_by INTEGER,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            user_id INTEGER,
            username TEXT,
            full_name TEXT,
            age INTEGER,
            school TEXT,
            phone TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            UNIQUE(event_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            user_id INTEGER,
            username TEXT,
            question TEXT,
            answer TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            quiz_name TEXT,
            score INTEGER,
            total INTEGER,
            created_at TEXT
        );
        """)
    print("База данных инициализирована.")


# ===== Пользователи =====

def add_user(user_id: int, username: str, full_name: str, role: str = "participant"):
    with get_conn() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO users (user_id, username, full_name, role, registered_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, username, full_name, role, datetime.now().isoformat()),
        )


def get_user(user_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()


# ===== Мероприятия =====

def create_event(title, description, date, place, equipment, safety_rules, max_participants, created_by):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO events (title, description, date, place, equipment, safety_rules,
                                   max_participants, created_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, description, date, place, equipment, safety_rules,
             max_participants, created_by, datetime.now().isoformat()),
        )
        return cur.lastrowid


def list_events():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM events ORDER BY date").fetchall()


def get_event(event_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()


def delete_event(event_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM registrations WHERE event_id = ?", (event_id,))
        conn.execute("DELETE FROM questions WHERE event_id = ?", (event_id,))
        conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
    print(f"Мероприятие id={event_id} удалено.")


# ===== Регистрации =====

def register_for_event(event_id, user_id, username, full_name, age, school, phone):
    with get_conn() as conn:
        try:
            conn.execute(
                """INSERT INTO registrations
                   (event_id, user_id, username, full_name, age, school, phone, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (event_id, user_id, username, full_name, age, school, phone,
                 datetime.now().isoformat()),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def event_participants(event_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM registrations WHERE event_id = ? ORDER BY created_at",
            (event_id,),
        ).fetchall()


def count_participants(event_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM registrations WHERE event_id = ? AND status != 'rejected'",
            (event_id,),
        ).fetchone()
        return row["cnt"] if row else 0


def set_registration_status(reg_id: int, status: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE registrations SET status = ? WHERE id = ?",
            (status, reg_id),
        )


def get_registration(reg_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM registrations WHERE id = ?", (reg_id,)
        ).fetchone()


def get_registrations_by_event(event_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM registrations WHERE event_id = ? ORDER BY created_at",
            (event_id,),
        ).fetchall()


# ===== Вопросы спикерам =====

def add_question(event_id, user_id, username, question):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO questions (event_id, user_id, username, question, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (event_id, user_id, username, question, datetime.now().isoformat()),
        )


def list_questions(event_id: int = None):
    with get_conn() as conn:
        if event_id:
            return conn.execute(
                "SELECT * FROM questions WHERE event_id = ? ORDER BY created_at",
                (event_id,),
            ).fetchall()
        return conn.execute("SELECT * FROM questions ORDER BY created_at DESC").fetchall()


def answer_question(question_id: int, answer: str):
    with get_conn() as conn:
        conn.execute("UPDATE questions SET answer = ? WHERE id = ?", (answer, question_id))


# ===== Викторины =====

def save_quiz_result(user_id, username, quiz_name, score, total):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO quiz_results (user_id, username, quiz_name, score, total, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, username, quiz_name, score, total, datetime.now().isoformat()),
        )