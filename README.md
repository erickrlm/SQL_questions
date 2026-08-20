# SQL Prep

A local-first SQL interview preparation tool for data engineering, analytics engineering, and BI interviews. Lightweight, zero dependencies, runs entirely on your machine.

## Quick start

```bash
python3 server.py
# Open http://localhost:8420
```

Requires Python 3. No install step, no virtual environment needed — uses only the standard library.

## Features

- **117 questions** (102 multiple choice + 15 coding) across 7 categories and 40+ topics, covering SQL basics, window functions, query design, data modeling, query optimization, data warehousing, and ETL concepts
- **Two question types** — Multiple choice (pick the correct answer) and Query (write a SQL query against a real dataset)
- **SQL coding sandbox** (Phase 2) — write and execute SQL queries in-browser with result-set validation, schema inspection, and instant feedback — like Leetcode for SQL
- **3 difficulty levels** — easy, medium, hard
- **4 views** — Practice (multiple choice), Code (SQL sandbox), Stats (progress tracking), and Questions (browse all)
- **Keyboard-driven** — answer with A/B/C/D keys, switch views with 1/2/3/4, advance with Enter, run queries with Ctrl+Enter
- **Progress tracking** — accuracy by topic and difficulty, response time, confidence self-assessment, weak topic detection — shared across both Practice and Code modes
- **Dark/light theme** with system-persisted preference
- **Filterable question browser** by difficulty, topic, category, and type

## Architecture

```
server.py        # HTTP server + JSON API (stdlib http.server)
database.py      # Schema, CRUD, stats, SQL sandbox execution
seed_data.py     # All 147 questions and 4 datasets (pure data)
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
- **Code/data separation:** `database.py` (~290 lines) handles logic; `seed_data.py` (~2,500 lines) holds all question and dataset definitions

## API

### Questions

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/questions` | List questions (filter by `?difficulty=&topic=&category=&type=`) |
| GET | `/api/questions/:id` | Single question by ID |
| GET | `/api/topics` | All topics and categories |

### Code sandbox

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/code/questions/:id` | Coding question with dataset schema (DDL) |
| POST | `/api/code/execute` | Run a user's SQL query against the question's dataset (body: `{question_id, query}`) |
| POST | `/api/code/submit` | Validate a query answer against expected output and save progress (body: `{question_id, query}`) |

### Progress

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/progress/stats` | Accuracy, totals, by-topic, by-difficulty breakdowns |
| GET | `/api/progress/weak-topics?threshold=60` | Topics below accuracy threshold |
| POST | `/api/progress` | Record an answer or confidence rating |

### Data validation

The query sandbox validates by **comparing result sets**, not SQL text. Your query is correct if it produces the same output as the expected solution — column count, row count, and sorted row values all match. Equivalent queries (CTE vs subquery, JOIN vs EXISTS) are accepted as long as the output matches.

Each query execution runs in a fresh **in-memory SQLite database** — destructive queries can't affect anything. Results are capped at 200 rows.

## Datasets

Three reusable datasets power the coding questions:

| Dataset | Tables | Rows | Topics |
|---------|--------|------|--------|
| `employees` | departments, employees | 17 | JOINs, aggregation, self-joins, correlated subqueries, recursive CTEs |
| `sales` | customers, products, orders | 25 | Filtering, aggregation, window functions, running totals, MoM growth |
| `university` | students, courses, enrollments | 26 | Sorting, subqueries, grouping, window functions |

## Adding questions

Questions are seeded from three functions in `seed_data.py`:

- `seed_questions(get_db)` — multiple choice questions
- `seed_coding_questions(get_db)` — SQL coding questions
- `seed_datasets(get_db)` — dataset schemas and sample data for coding questions

To add more:

1. Add entries to the appropriate list in `seed_data.py`
2. Restart the server

Seeding uses `INSERT OR IGNORE` keyed on `id`, so it runs on every startup: existing questions and your progress history are left untouched, and only IDs not already in the database get inserted. Deleting `data/studytool.db` is no longer needed (and would wipe your progress along with it) — only do that if you actually want a clean slate. Editing an existing question's text in `seed_data.py` won't update it in the database, since its `id` already exists; give it a new `id` instead, or delete that row manually.

### Multiple choice question schema

```python
{
    "id": "q042",
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

### Coding question schema

```python
{
    "id": "c016",
    "category": "Query Design",
    "topic": "ctes",
    "difficulty": "hard",
    "dataset_reference": "employees",     # references a dataset in seed_datasets()
    "prompt": "Write a query to find ...",
    "correct_answer": "SELECT ...",       # the expected query (for result-set validation)
    "explanation": "Explanation of the solution approach.",
}
```

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| A–D | Select answer choice (Practice view) |
| Enter | Next question (after answering) |
| Ctrl+Enter | Run SQL query (Code view) |
| 1 | Practice view |
| 2 | Stats view |
| 3 | Questions list |
| 4 | Code view |
| Ctrl+R | Random question |

## Roadmap

Phase 3 (planned): spaced repetition and adaptive practice.
