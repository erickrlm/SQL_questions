import sqlite3
import json
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "studytool.db"

from seed_data import seed_questions, seed_datasets, seed_coding_questions


def get_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS questions (
            id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            topic TEXT NOT NULL,
            difficulty TEXT NOT NULL CHECK(difficulty IN ('easy','medium','hard')),
            type TEXT NOT NULL DEFAULT 'Multiple choice',
            prompt TEXT NOT NULL,
            choices TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            explanation TEXT NOT NULL,
            hints TEXT NOT NULL DEFAULT '[]',
            tags TEXT NOT NULL DEFAULT '[]',
            dataset_reference TEXT
        );

        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id TEXT NOT NULL REFERENCES questions(id),
            completed_at TEXT NOT NULL,
            correct INTEGER NOT NULL,
            response_time_ms INTEGER,
            confidence TEXT CHECK(confidence IN ('low','medium','high')),
            user_answer TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS datasets (
            name TEXT PRIMARY KEY,
            description TEXT NOT NULL DEFAULT '',
            ddl TEXT NOT NULL,
            sample_data TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_progress_question ON progress(question_id);
        CREATE INDEX IF NOT EXISTS idx_progress_completed ON progress(completed_at);
    """)
    conn.commit()
    conn.close()
    seed_questions(get_db)
    seed_datasets(get_db)
    seed_coding_questions(get_db)
    return get_db()


def get_dataset(name):
    """Fetch a dataset by name."""
    conn = get_db()
    row = conn.execute("SELECT * FROM datasets WHERE name = ?", (name,)).fetchone()
    conn.close()
    return dict(row) if row else None


MAX_RESULT_ROWS = 200


def _create_sandbox(dataset_name):
    """Create an in-memory SQLite DB, load the dataset DDL and sample data."""
    dataset = get_dataset(dataset_name)
    if not dataset:
        raise ValueError(f"Dataset '{dataset_name}' not found")
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(dataset["ddl"])
    conn.executescript(dataset["sample_data"])
    return conn


def execute_query(dataset_name, sql):
    """Execute a user's SQL query against a dataset sandbox.

    Returns a dict with columns/rows on success, or an error dict.
    Only SELECT queries are allowed.
    """
    # Basic safety: reject non-SELECT statements (WITH covers CTEs, including recursive ones)
    stripped = sql.strip().upper()
    if not (stripped.startswith("SELECT") or stripped.startswith("WITH")):
        return {"error": "Only SELECT queries are supported."}

    try:
        conn = _create_sandbox(dataset_name)
    except ValueError as e:
        return {"error": str(e)}

    try:
        cursor = conn.execute(sql)
        if cursor.description is None:
            return {"error": "Only SELECT queries are supported."}
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchmany(MAX_RESULT_ROWS + 1)
        truncated = len(rows) > MAX_RESULT_ROWS
        rows = [[cell for cell in r] for r in rows[:MAX_RESULT_ROWS]]
        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "truncated": truncated,
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()


def validate_query(dataset_name, user_sql, expected_sql):
    """Run user and expected queries in a sandbox and compare result sets.

    Comparison is done on sorted result sets — column count, row count,
    then sorted row-by-row. Column names are not compared to avoid
    false failures from alias differences.
    """
    try:
        conn = _create_sandbox(dataset_name)
    except ValueError as e:
        return {"match": False, "error": str(e)}

    try:
        user_cursor = conn.execute(user_sql)
        if user_cursor.description is None:
            return {"match": False, "error": "User query must be a SELECT."}
        user_columns = [desc[0] for desc in user_cursor.description]
        user_rows = [tuple(r) for r in user_cursor.fetchall()]
    except Exception as e:
        conn.close()
        return {"match": False, "error": f"Query error: {e}"}

    try:
        exp_cursor = conn.execute(expected_sql)
        exp_columns = [desc[0] for desc in exp_cursor.description]
        exp_rows = [tuple(r) for r in exp_cursor.fetchall()]
    except Exception as e:
        conn.close()
        return {"match": False, "error": f"Validation error: {e}"}

    conn.close()

    # 1. Column count
    if len(user_columns) != len(exp_columns):
        return {
            "match": False,
            "details": f"Column count mismatch. Got {len(user_columns)}, expected {len(exp_columns)}.",
            "user_columns": user_columns,
            "expected_columns": exp_columns,
            "user_row_count": len(user_rows),
            "expected_row_count": len(exp_rows),
        }

    # 2. Row count
    if len(user_rows) != len(exp_rows):
        return {
            "match": False,
            "details": f"Row count mismatch. Got {len(user_rows)}, expected {len(exp_rows)}.",
            "user_columns": user_columns,
            "expected_columns": exp_columns,
            "user_row_count": len(user_rows),
            "expected_row_count": len(exp_rows),
        }

    # 3. Sorted row-by-row comparison
    if sorted(user_rows) != sorted(exp_rows):
        return {
            "match": False,
            "details": "Row values do not match the expected output.",
            "user_columns": user_columns,
            "expected_columns": exp_columns,
            "user_row_count": len(user_rows),
            "expected_row_count": len(exp_rows),
        }

    return {
        "match": True,
        "details": "",
        "user_columns": user_columns,
        "user_row_count": len(user_rows),
        "expected_row_count": len(exp_rows),
    }


def get_questions(category=None, topic=None, difficulty=None, question_type=None):
    conn = get_db()
    query = "SELECT * FROM questions WHERE 1=1"
    params = []
    if category:
        query += " AND category = ?"
        params.append(category)
    if topic:
        query += " AND topic = ?"
        params.append(topic)
    if difficulty:
        query += " AND difficulty = ?"
        params.append(difficulty)
    if question_type:
        query += " AND type = ?"
        params.append(question_type)
    query += " ORDER BY category, difficulty, id"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_question(question_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def save_progress(question_id, correct, user_answer, response_time_ms=None, confidence=None):
    conn = get_db()
    conn.execute("""
        INSERT INTO progress (question_id, completed_at, correct, user_answer, response_time_ms, confidence)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (question_id, time.strftime("%Y-%m-%dT%H:%M:%S"), int(correct), user_answer,
          response_time_ms, confidence))
    conn.commit()
    conn.close()


def get_stats():
    conn = get_db()
    stats = {}

    total = conn.execute("SELECT COUNT(*) FROM progress").fetchone()[0]
    correct = conn.execute("SELECT COUNT(*) FROM progress WHERE correct = 1").fetchone()[0]
    stats["total_answered"] = total
    stats["total_correct"] = correct
    stats["accuracy"] = round(correct / total * 100, 1) if total > 0 else 0

    by_topic = conn.execute("""
        SELECT q.topic, COUNT(*) as cnt, SUM(p.correct) as correct
        FROM progress p JOIN questions q ON p.question_id = q.id
        GROUP BY q.topic ORDER BY cnt DESC
    """).fetchall()
    stats["by_topic"] = [{"topic": r["topic"], "total": r["cnt"],
                          "accuracy": round(r["correct"]/r["cnt"]*100, 1)} for r in by_topic]

    by_difficulty = conn.execute("""
        SELECT q.difficulty, COUNT(*) as cnt, SUM(p.correct) as correct
        FROM progress p JOIN questions q ON p.question_id = q.id
        GROUP BY q.difficulty ORDER BY cnt DESC
    """).fetchall()
    stats["by_difficulty"] = [{"difficulty": r["difficulty"], "total": r["cnt"],
                                "accuracy": round(r["correct"]/r["cnt"]*100, 1)} for r in by_difficulty]

    recent = conn.execute("""
        SELECT p.*, q.topic, q.difficulty
        FROM progress p JOIN questions q ON p.question_id = q.id
        ORDER BY p.completed_at DESC LIMIT 20
    """).fetchall()
    stats["recent"] = [dict(r) for r in recent]

    conn.close()
    return stats


def get_weak_topics(threshold=60):
    conn = get_db()
    rows = conn.execute("""
        SELECT q.topic, COUNT(*) as cnt, SUM(p.correct) as correct,
               ROUND(SUM(p.correct)*100.0/COUNT(*), 1) as accuracy
        FROM progress p JOIN questions q ON p.question_id = q.id
        GROUP BY q.topic
        HAVING accuracy < ?
        ORDER BY accuracy ASC
    """, (threshold,)).fetchall()
    conn.close()
    return [{"topic": r["topic"], "total": r["cnt"], "accuracy": r["accuracy"]} for r in rows]
