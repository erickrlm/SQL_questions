# SQL Prep

A local-first SQL interview preparation tool for data engineering, analytics engineering, and BI interviews. Lightweight, zero dependencies, runs entirely on your machine.

## Quick start

```bash
python3 server.py
# Open http://localhost:8420
```

Requires Python 3. No install step, no virtual environment needed — uses only the standard library.

## Features

- **35 multiple-choice questions** across 7 categories and 35 topics, covering SQL basics, window functions, query design, data modeling, query optimization, data warehousing, and ETL concepts
- **3 difficulty levels** — easy, medium, hard
- **Keyboard-driven** — answer with A/B/C/D keys, switch views with 1/2/3, advance with Enter
- **Progress tracking** — accuracy by topic and difficulty, response time, confidence self-assessment, weak topic detection
- **Dark/light theme** with system-persisted preference
- **Filterable question browser** by difficulty, topic, and category

## Architecture

```
server.py        # HTTP server + JSON API (stdlib http.server)
database.py      # SQLite CRUD, stats, seeding
frontend/
  index.html     # SPA shell
  app.js         # Client-side logic (vanilla JS)
  style.css      # Dark/light theme
data/
  studytool.db   # SQLite database (auto-created on first run)
```

- **Backend:** Python `http.server` — no FastAPI, no Flask
- **Database:** SQLite via `sqlite3` stdlib module
- **Frontend:** Plain HTML/CSS/JS — no framework, no build step, no npm
- **Total dependencies:** 0

## API

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/questions` | List questions (filter by `?difficulty=&topic=&category=`) |
| GET | `/api/questions/:id` | Single question by ID |
| GET | `/api/topics` | All topics and categories |
| GET | `/api/progress/stats` | Accuracy, totals, by-topic, by-difficulty breakdowns |
| GET | `/api/progress/weak-topics?threshold=60` | Topics below accuracy threshold |
| POST | `/api/progress` | Record an answer or confidence rating |

## Adding questions

Questions are seeded from the `questions` list in `database.py:seed_questions()`. To add more:

1. Add entries to the `questions` list in `database.py`
2. Delete `data/studytool.db` to trigger re-seed
3. Restart the server

Each question follows this schema:

```python
{
    "id": "q036",
    "category": "SQL Basics",
    "topic": "joins",
    "difficulty": "medium",        # easy | medium | hard
    "prompt": "Question text?",
    "choices": json.dumps(["A", "B", "C", "D"]),
    "correct_answer": "A",
    "explanation": "Why A is correct.",
    "hints": json.dumps(["Optional hint 1", "Optional hint 2"]),
    "tags": json.dumps(["sql", "joins"]),
}
```

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| A–D | Select answer choice |
| Enter | Next question (after answering) |
| 1 | Practice view |
| 2 | Stats view |
| 3 | Question list |
| Ctrl+R | Random question |

## Roadmap

Phase 2 (planned): SQL coding sandbox with query execution and result-set validation. Phase 3: spaced repetition and adaptive practice.
