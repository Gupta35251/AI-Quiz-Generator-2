# import json
# import sqlite3
# from pathlib import Path
# from contextlib import contextmanager

# DB_PATH = Path(__file__).resolve().parent / "quiz_history.db"



# @contextmanager
# def get_connection():
#     connection = sqlite3.connect(DB_PATH)
#     connection.row_factory = sqlite3.Row
#     try:
#         yield connection
#         connection.commit()
#     except Exception:
#         connection.rollback()
#         raise
#     finally:
#         connection.close()

# def init_auth_db():
#     with get_connection() as connection:
#         connection.execute("""
#             CREATE TABLE IF NOT EXISTS users (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 email TEXT NOT NULL UNIQUE,
#                 password_hash TEXT NOT NULL,
#                 created_at TEXT DEFAULT CURRENT_TIMESTAMP
#             )
#         """)

#         columns = {
#             row["name"]
#             for row in connection.execute(
#                 "PRAGMA table_info(quiz_history)"
#             ).fetchall()
#         }

#         if "user_id" not in columns:
#             connection.execute(
#                 "ALTER TABLE quiz_history ADD COLUMN user_id INTEGER"
#             )

# def create_user(email, password_hash):
#     with get_connection() as connection:
#         cursor = connection.execute(
#             "INSERT INTO users (email, password_hash) VALUES (?, ?)",
#             (email.lower().strip(), password_hash),
#         )
#         return cursor.lastrowid


# def find_user_by_email(email):
#     with get_connection() as connection:
#         row = connection.execute(
#             "SELECT * FROM users WHERE email = ?",
#             (email.lower().strip(),),
#         ).fetchone()
#         return dict(row) if row else None

# def find_user_by_id(user_id):
#     with get_connection() as connection:
#         row = connection.execute(
#             "SELECT id, email FROM users WHERE id = ?",
#             (user_id,),
#         ).fetchone()
#         return dict(row) if row else None


# def init_db():
#     with get_connection() as connection:
#         connection.execute("""
#             CREATE TABLE IF NOT EXISTS quiz_history (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 date TEXT,
#                 quiz TEXT,
#                 results TEXT,
#                 score INTEGER
#             )
#         """)
#         connection.execute("""
#             CREATE TABLE IF NOT EXISTS quiz_sessions (
#                 session_id TEXT PRIMARY KEY,
#                 date TEXT NOT NULL,
#                 quiz TEXT NOT NULL,
#                 submitted INTEGER NOT NULL DEFAULT 0
#             )
#         """)


# def save_quiz(date, quiz, results, score):
#     with get_connection() as connection:
#         cursor = connection.execute("""
#             INSERT INTO quiz_history(date, quiz, results, score)
#             VALUES (?, ?, ?, ?)
#         """, (
#             date,
#             json.dumps(quiz, ensure_ascii=False),
#             json.dumps(results, ensure_ascii=False),
#             score,
#         ))
#         return cursor.lastrowid


# def create_quiz_session(session_id, date, quiz):
#     with get_connection() as connection:
#         connection.execute("""
#             INSERT INTO quiz_sessions(session_id, date, quiz, submitted)
#             VALUES (?, ?, ?, 0)
#         """, (session_id, date, json.dumps(quiz, ensure_ascii=False)))


# def get_quiz_session(session_id):
#     with get_connection() as connection:
#         row = connection.execute(
#             "SELECT session_id, date, quiz, submitted FROM quiz_sessions WHERE session_id = ?",
#             (session_id,),
#         ).fetchone()
#         return dict(row) if row else None


# def mark_quiz_session_submitted(session_id):
#     with get_connection() as connection:
#         connection.execute(
#             "UPDATE quiz_sessions SET submitted = 1 WHERE session_id = ?",
#             (session_id,),
#         )


# def get_all_history():
#     with get_connection() as connection:
#         rows = connection.execute(
#             "SELECT id, date, quiz, results, score FROM quiz_history ORDER BY id DESC"
#         ).fetchall()

#     items = []
#     for row in rows:
#         quiz = json.loads(row["quiz"])
#         results = json.loads(row["results"])
#         items.append({
#             "id": row["id"],
#             "date": row["date"],
#             "topic": quiz.get("topic", "Quiz"),
#             "score": row["score"] or 0,
#             "total": len(results),
#             "question_count": len(quiz.get("questions", [])),
#         })
#     return items


# def get_history_by_id(quiz_id):
#     with get_connection() as connection:
#         row = connection.execute(
#             "SELECT id, date, quiz, results, score FROM quiz_history WHERE id = ?",
#             (quiz_id,),
#         ).fetchone()

#     if not row:
#         return None

#     return {
#         "id": row["id"],
#         "date": row["date"],
#         "quiz": json.loads(row["quiz"]),
#         "results": json.loads(row["results"]),
#         "score": row["score"] or 0,
#     }


# init_db()






import sqlite3
import json
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).resolve().parent / "quiz_history.db"


@contextmanager
def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db():
    with get_connection() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS quiz_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                quiz TEXT NOT NULL,
                results TEXT NOT NULL,
                score INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS quiz_sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                quiz TEXT NOT NULL,
                submitted INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS weak_concepts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                concept TEXT NOT NULL,
                correct_count INTEGER NOT NULL DEFAULT 0,
                wrong_count INTEGER NOT NULL DEFAULT 0,
                last_attempt TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, concept),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS weekly_quizzes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

def init_auth_db():
    init_db()
# User accounts

def create_user(email, password_hash):
    with get_connection() as db:
        cursor = db.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email.lower().strip(), password_hash),
        )
        return cursor.lastrowid


def find_user_by_email(email):
    with get_connection() as db:
        row = db.execute(
            "SELECT * FROM users WHERE email = ?",
            (email.lower().strip(),),
        ).fetchone()
        return dict(row) if row else None


def find_user_by_id(user_id):
    with get_connection() as db:
        row = db.execute(
            "SELECT id, email FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None


# Quiz sessions

def create_quiz_session(session_id, user_id, date, quiz):
    with get_connection() as db:
        db.execute("""
            INSERT INTO quiz_sessions
                (session_id, user_id, date, quiz)
            VALUES (?, ?, ?, ?)
        """, (
            session_id, user_id, date,
            json.dumps(quiz, ensure_ascii=False),
        ))


def get_quiz_session(session_id, user_id):
    with get_connection() as db:
        row = db.execute("""
            SELECT * FROM quiz_sessions
            WHERE session_id = ? AND user_id = ?
        """, (session_id, user_id)).fetchone()

        if not row:
            return None

        item = dict(row)
        item["quiz"] = json.loads(item["quiz"])
        return item


def mark_quiz_session_submitted(session_id, user_id):
    with get_connection() as db:
        cursor = db.execute("""
            UPDATE quiz_sessions
            SET submitted = 1
            WHERE session_id = ?
              AND user_id = ?
              AND submitted = 0
        """, (session_id, user_id))
        return cursor.rowcount == 1


# Quiz history

def save_quiz(user_id, date, quiz, results, score):
    with get_connection() as db:
        cursor = db.execute("""
            INSERT INTO quiz_history
                (user_id, date, quiz, results, score)
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_id, date,
            json.dumps(quiz, ensure_ascii=False),
            json.dumps(results, ensure_ascii=False),
            score,
        ))
        return cursor.lastrowid


def get_all_history(user_id):
    with get_connection() as db:
        rows = db.execute("""
            SELECT id, date, quiz, results, score
            FROM quiz_history
            WHERE user_id = ?
            ORDER BY id DESC
        """, (user_id,)).fetchall()

        items = []
        for row in rows:
            item = dict(row)
            item["quiz"] = json.loads(item["quiz"])
            item["results"] = json.loads(item["results"])
            items.append(item)

        return items


def get_history_by_id(history_id, user_id):
    with get_connection() as db:
        row = db.execute("""
            SELECT id, date, quiz, results, score
            FROM quiz_history
            WHERE id = ? AND user_id = ?
        """, (history_id, user_id)).fetchone()

        if not row:
            return None

        item = dict(row)
        item["quiz"] = json.loads(item["quiz"])
        item["results"] = json.loads(item["results"])
        return item


# Weak concepts

def record_concept_result(user_id, concept, is_correct):
    concept = (concept or "General").strip() or "General"

    with get_connection() as db:
        db.execute("""
            INSERT INTO weak_concepts
                (user_id, concept, correct_count, wrong_count)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, concept) DO UPDATE SET
                correct_count = correct_count + excluded.correct_count,
                wrong_count = wrong_count + excluded.wrong_count,
                last_attempt = CURRENT_TIMESTAMP
        """, (
            user_id,
            concept,
            1 if is_correct else 0,
            0 if is_correct else 1,
        ))


def get_weak_concepts(user_id):
    with get_connection() as db:
        rows = db.execute("""
            SELECT concept, correct_count, wrong_count, last_attempt
            FROM weak_concepts
            WHERE user_id = ? AND wrong_count > 0
            ORDER BY
                CAST(wrong_count AS REAL) /
                MAX(correct_count + wrong_count, 1) DESC,
                wrong_count DESC
        """, (user_id,)).fetchall()

        return [dict(row) for row in rows]


# Weekly quizzes

def get_last_weekly_quiz(user_id):
    with get_connection() as db:
        row = db.execute("""
            SELECT session_id, created_at
            FROM weekly_quizzes
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (user_id,)).fetchone()

        return dict(row) if row else None


def save_weekly_quiz(user_id, session_id):
    with get_connection() as db:
        db.execute("""
            INSERT INTO weekly_quizzes (user_id, session_id)
            VALUES (?, ?)
        """, (user_id, session_id))
