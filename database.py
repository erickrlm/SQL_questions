import sqlite3
import json
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "studytool.db"


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
            type TEXT NOT NULL DEFAULT 'multiple_choice',
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

        CREATE INDEX IF NOT EXISTS idx_progress_question ON progress(question_id);
        CREATE INDEX IF NOT EXISTS idx_progress_completed ON progress(completed_at);
    """)
    conn.commit()
    return conn


def seed_questions():
    conn = get_db()
    existing = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    if existing > 0:
        conn.close()
        return

    questions = [
        {
            "id": "q001",
            "category": "SQL Basics",
            "topic": "filtering",
            "difficulty": "easy",
            "prompt": "Which clause filters rows AFTER aggregation?",
            "choices": json.dumps(["WHERE", "HAVING", "FILTER", "QUALIFY"]),
            "correct_answer": "HAVING",
            "explanation": "WHERE filters before aggregation. HAVING filters after GROUP BY aggregation. QUALIFY is for window functions in some databases.",
            "hints": json.dumps(["Think about the order of operations: FROM → WHERE → GROUP BY → ??? → SELECT"]),
            "tags": json.dumps(["sql", "aggregation", "basics"]),
        },
        {
            "id": "q002",
            "category": "SQL Basics",
            "topic": "joins",
            "difficulty": "easy",
            "prompt": "Which JOIN returns all rows from the left table and matching rows from the right table?",
            "choices": json.dumps(["INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "CROSS JOIN"]),
            "correct_answer": "LEFT JOIN",
            "explanation": "LEFT JOIN keeps every row from the left table. Unmatched right-side columns become NULL. LEFT JOIN and LEFT OUTER JOIN are synonymous in most databases.",
            "hints": json.dumps(["Also called LEFT OUTER JOIN"]),
            "tags": json.dumps(["sql", "joins", "basics"]),
        },
        {
            "id": "q003",
            "category": "SQL Basics",
            "topic": "sorting",
            "difficulty": "easy",
            "prompt": "What does ORDER BY 2 DESC do?",
            "choices": json.dumps([
                "Sorts by the second character of each value descending",
                "Sorts by the second column in the SELECT list descending",
                "Sorts by column named '2' descending",
                "Returns only the second row in descending order"
            ]),
            "correct_answer": "Sorts by the second column in the SELECT list descending",
            "explanation": "ORDER BY ordinal position references columns by their position in the SELECT clause. ORDER BY 2 means the second column. This is convenient but fragile — adding columns to SELECT can silently change behavior.",
            "hints": json.dumps(["Ordinal positions start at 1, not 0"]),
            "tags": json.dumps(["sql", "sorting", "basics"]),
        },
        {
            "id": "q004",
            "category": "Window Functions",
            "topic": "ranking",
            "difficulty": "medium",
            "prompt": "What is the difference between ROW_NUMBER() and RANK()?",
            "choices": json.dumps([
                "ROW_NUMBER() is faster, otherwise identical",
                "ROW_NUMBER() assigns unique sequential numbers; RANK() gives ties the same rank and leaves gaps",
                "RANK() requires ORDER BY, ROW_NUMBER() does not",
                "ROW_NUMBER() works only with PARTITION BY"
            ]),
            "correct_answer": "ROW_NUMBER() assigns unique sequential numbers; RANK() gives ties the same rank and leaves gaps",
            "explanation": "ROW_NUMBER() always produces unique numbers (1,2,3,4). RANK() assigns tied rows the same rank and skips the next number (1,2,2,4). DENSE_RANK() also ties but doesn't skip (1,2,2,3).",
            "hints": json.dumps(["Think about what happens when two rows have the same ORDER BY value"]),
            "tags": json.dumps(["sql", "window-functions", "ranking"]),
        },
        {
            "id": "q005",
            "category": "Window Functions",
            "topic": "frames",
            "difficulty": "medium",
            "prompt": "What does ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW define?",
            "choices": json.dumps([
                "A running total from the start of the partition to the current row",
                "All rows in the partition",
                "Only the current row",
                "The current row and all following rows"
            ]),
            "correct_answer": "A running total from the start of the partition to the current row",
            "explanation": "This is the default window frame for ORDER BY. It creates a cumulative (running) calculation — each row's window includes itself and all preceding rows in the partition.",
            "hints": json.dumps(["This is why SUM(x) OVER (ORDER BY date) gives a running total"]),
            "tags": json.dumps(["sql", "window-functions", "frames"]),
        },
        {
            "id": "q006",
            "category": "Query Design",
            "topic": "ctes",
            "difficulty": "medium",
            "prompt": "When would you prefer a CTE over a subquery?",
            "choices": json.dumps([
                "When the query runs slowly and needs optimization",
                "When the same derived result is referenced multiple times or for readability of complex logic",
                "CTEs are always preferred — they are faster",
                "When filtering on an aggregated value"
            ]),
            "correct_answer": "When the same derived result is referenced multiple times or for readability of complex logic",
            "explanation": "CTEs improve readability for complex queries and allow referencing the same derived table multiple times. They don't inherently improve performance — in PostgreSQL they're optimization fences; in SQLite/MySQL they're inlined. Use them for clarity, not speed.",
            "hints": json.dumps(["WITH clause defines CTEs", "Consider a query that needs the same subquery in both SELECT and WHERE"]),
            "tags": json.dumps(["sql", "ctes", "query-design"]),
        },
        {
            "id": "q007",
            "category": "Query Design",
            "topic": "subqueries",
            "difficulty": "medium",
            "prompt": "Which subquery type can return multiple columns?",
            "choices": json.dumps([
                "Scalar subquery",
                "Correlated subquery",
                "Row subquery",
                "EXISTS subquery"
            ]),
            "correct_answer": "Row subquery",
            "explanation": "A row subquery returns a single row with multiple columns, used with row constructors: WHERE (a, b) = (SELECT x, y FROM ...). Scalar subqueries return one value. EXISTS only checks for presence.",
            "hints": json.dumps(["Think about (col1, col2) IN (subquery) syntax"]),
            "tags": json.dumps(["sql", "subqueries", "query-design"]),
        },
        {
            "id": "q008",
            "category": "Data Modeling",
            "topic": "normalization",
            "difficulty": "medium",
            "prompt": "What does third normal form (3NF) eliminate?",
            "choices": json.dumps([
                "Duplicate rows",
                "Transitive dependencies",
                "Partial key dependencies",
                "Multi-valued dependencies"
            ]),
            "correct_answer": "Transitive dependencies",
            "explanation": "3NF requires that non-key columns depend on 'the key, the whole key, and nothing but the key.' It eliminates transitive dependencies where a non-key column depends on another non-key column. 2NF eliminates partial dependencies. 4NF handles multi-valued dependencies.",
            "hints": json.dumps(["1NF = atomic values, 2NF = no partial dependencies, 3NF = no transitive dependencies"]),
            "tags": json.dumps(["data-modeling", "normalization", "theory"]),
        },
        {
            "id": "q009",
            "category": "Data Modeling",
            "topic": "schemas",
            "difficulty": "medium",
            "prompt": "In a star schema, what is the difference between fact and dimension tables?",
            "choices": json.dumps([
                "Fact tables are small; dimension tables are large",
                "Fact tables store measurable events; dimension tables store descriptive attributes",
                "Dimension tables have foreign keys; fact tables have primary keys only",
                "They are the same thing in different databases"
            ]),
            "correct_answer": "Fact tables store measurable events; dimension tables store descriptive attributes",
            "explanation": "Fact tables contain quantitative measures (sales amount, quantity) and foreign keys to dimensions. Dimension tables contain descriptive attributes (customer name, product category, date attributes). Fact tables are typically much larger.",
            "hints": json.dumps(["Think about a sales database: what is the 'what' vs the 'who/when/where'?"]),
            "tags": json.dumps(["data-modeling", "star-schema", "warehousing"]),
        },
        {
            "id": "q010",
            "category": "Data Warehousing",
            "topic": "scd",
            "difficulty": "hard",
            "prompt": "A slowly changing dimension type 2 (SCD2) tracks history by:",
            "choices": json.dumps([
                "Overwriting old values with new values",
                "Adding a new row with effective dates and a current flag",
                "Keeping a separate history table with a trigger",
                "Storing the previous value in a separate column"
            ]),
            "correct_answer": "Adding a new row with effective dates and a current flag",
            "explanation": "SCD Type 2 preserves history by inserting a new row for each change, typically with start_date, end_date, and is_current columns. Type 1 overwrites (no history). Type 3 keeps only the previous value in additional columns.",
            "hints": json.dumps(["SCD1 = overwrite, SCD2 = new row with dates, SCD3 = previous value column"]),
            "tags": json.dumps(["data-warehousing", "scd", "modeling"]),
        },
        {
            "id": "q011",
            "category": "Query Optimization",
            "topic": "indexes",
            "difficulty": "hard",
            "prompt": "Why might a query NOT use an index even when one exists on the filtered column?",
            "choices": json.dumps([
                "Indexes expire after a table reaches a certain size",
                "The query planner determines a full table scan is cheaper (low selectivity, small table, or function-wrapped column)",
                "Indexes only work with primary keys",
                "Indexes are disabled by default"
            ]),
            "correct_answer": "The query planner determines a full table scan is cheaper (low selectivity, small table, or function-wrapped column)",
            "explanation": "Query planners use cost-based optimization. A full scan can be faster when: the table is small, the predicate matches most rows (low selectivity), the column is wrapped in a function like WHERE UPPER(name) = 'X', or the index is poorly suited (e.g., second column in a composite index without the first).",
            "hints": json.dumps(["Think about what makes an index useful: selectivity, covering the query, not wrapping columns in functions"]),
            "tags": json.dumps(["sql", "optimization", "indexes"]),
        },
        {
            "id": "q012",
            "category": "ETL Concepts",
            "topic": "data-quality",
            "difficulty": "medium",
            "prompt": "What is the difference between ETL and ELT?",
            "choices": json.dumps([
                "ETL uses SQL; ELT uses Python",
                "ETL transforms before loading; ELT loads raw data first then transforms in the target system",
                "ETL is for batch processing; ELT is for streaming",
                "They are identical — the terms are interchangeable"
            ]),
            "correct_answer": "ETL transforms before loading; ELT loads raw data first then transforms in the target system",
            "explanation": "In ETL, data is transformed on an intermediate server before loading into the warehouse. In ELT, raw data is loaded into the warehouse first and transformed there using the warehouse's compute power (e.g., dbt models on Snowflake/BigQuery). ELT has become more common with cloud data warehouses.",
            "hints": json.dumps(["Where does the T happen? Before or after hitting the warehouse?"]),
            "tags": json.dumps(["etl", "data-engineering", "pipelines"]),
        },
        {
            "id": "q013",
            "category": "SQL Basics",
            "topic": "null-handling",
            "difficulty": "easy",
            "prompt": "What is the result of: SELECT NULL = NULL?",
            "choices": json.dumps(["TRUE", "FALSE", "NULL", "ERROR"]),
            "correct_answer": "NULL",
            "explanation": "NULL represents unknown. Comparing two unknowns yields unknown (NULL), not TRUE or FALSE. This is why we use IS NULL / IS NOT NULL and why NOT IN with NULLs can produce unexpected results — NULL = anything is NULL, which is not TRUE.",
            "hints": json.dumps(["NULL means unknown. Can you say two unknown things are equal?"]),
            "tags": json.dumps(["sql", "null", "basics"]),
        },
        {
            "id": "q014",
            "category": "Query Optimization",
            "topic": "execution",
            "difficulty": "hard",
            "prompt": "What is the logical query processing order in SQL?",
            "choices": json.dumps([
                "SELECT → FROM → WHERE → GROUP BY → HAVING → ORDER BY",
                "FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY",
                "FROM → SELECT → WHERE → GROUP BY → ORDER BY → HAVING",
                "WHERE → FROM → SELECT → GROUP BY → HAVING → ORDER BY"
            ]),
            "correct_answer": "FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY",
            "explanation": "SQL's logical processing order: FROM (including JOINs), WHERE, GROUP BY, HAVING, SELECT (including aliases, window functions), ORDER BY, LIMIT/OFFSET. This is why column aliases defined in SELECT can't be used in WHERE but can be used in ORDER BY.",
            "hints": json.dumps(["Why can you use a SELECT alias in ORDER BY but not in WHERE?"]),
            "tags": json.dumps(["sql", "optimization", "execution-plan"]),
        },
        {
            "id": "q015",
            "category": "Window Functions",
            "topic": "lag-lead",
            "difficulty": "medium",
            "prompt": "What does LAG(sales, 1, 0) OVER (ORDER BY month) return?",
            "choices": json.dumps([
                "The next month's sales, defaulting to 0 if there is no next month",
                "The previous month's sales, defaulting to 0 for the first row",
                "The difference between current and previous month sales",
                "The highest sale value among all preceding rows"
            ]),
            "correct_answer": "The previous month's sales, defaulting to 0 for the first row",
            "explanation": "LAG accesses a previous row's value. LAG(sales, 1, 0) means: look back 1 row at the sales column, return 0 if there is no previous row (first row in partition). LEAD looks forward instead.",
            "hints": json.dumps(["LAG = look behind, LEAD = look ahead. Second arg is offset, third is default."]),
            "tags": json.dumps(["sql", "window-functions", "lag-lead"]),
        },
        {
            "id": "q016",
            "category": "SQL Basics",
            "topic": "set-operations",
            "difficulty": "medium",
            "prompt": "What is the key difference between UNION and UNION ALL?",
            "choices": json.dumps([
                "UNION requires the same number of columns; UNION ALL does not",
                "UNION removes duplicates; UNION ALL keeps all rows",
                "UNION works across databases; UNION ALL is PostgreSQL-only",
                "UNION sorts results; UNION ALL returns rows in random order"
            ]),
            "correct_answer": "UNION removes duplicates; UNION ALL keeps all rows",
            "explanation": "UNION deduplicates results (like adding DISTINCT), which requires a sort or hash operation. UNION ALL simply concatenates row sets. If you know there are no duplicates or don't need deduplication, UNION ALL is significantly faster.",
            "hints": json.dumps(["Think about the performance cost — when would you pick one over the other?"]),
            "tags": json.dumps(["sql", "set-operations", "basics"]),
        },
        {
            "id": "q017",
            "category": "Query Design",
            "topic": "correlated-subqueries",
            "difficulty": "medium",
            "prompt": "What makes a subquery 'correlated'?",
            "choices": json.dumps([
                "It appears in both the SELECT and WHERE clauses",
                "It references a column from the outer query and is re-evaluated for each outer row",
                "It returns the same result set as another subquery in the statement",
                "It uses a JOIN internally"
            ]),
            "correct_answer": "It references a column from the outer query and is re-evaluated for each outer row",
            "explanation": "A correlated subquery depends on the outer query — it references outer columns, so it must be executed once per outer row. Example: SELECT name FROM employees e WHERE salary > (SELECT AVG(salary) FROM employees WHERE dept_id = e.dept_id). Non-correlated subqueries are independent and evaluated once.",
            "hints": json.dumps(["It 'correlates' with the outer query — the inner query can't run alone"]),
            "tags": json.dumps(["sql", "subqueries", "query-design"]),
        },
        {
            "id": "q018",
            "category": "Query Design",
            "topic": "exists-vs-in",
            "difficulty": "medium",
            "prompt": "When would you prefer EXISTS over IN for a subquery?",
            "choices": json.dumps([
                "IN is always faster — EXISTS is obsolete",
                "When checking for presence in a large result set, especially when NULLs may be involved",
                "When the subquery returns exactly one row",
                "EXISTS works only with correlated subqueries"
            ]),
            "correct_answer": "When checking for presence in a large result set, especially when NULLs may be involved",
            "explanation": "EXISTS short-circuits — it stops scanning as soon as it finds a match. NOT IN can produce surprising results if the subquery contains NULLs (NOT IN with a NULL in the list always returns empty), while NOT EXISTS handles NULLs correctly. EXISTS is also often more efficient because it doesn't need to materialize the full subquery result.",
            "hints": json.dumps(["What happens with: WHERE id NOT IN (SELECT manager_id FROM employees) if manager_id can be NULL?"]),
            "tags": json.dumps(["sql", "subqueries", "query-design", "optimization"]),
        },
        {
            "id": "q019",
            "category": "SQL Basics",
            "topic": "coalesce-nullif",
            "difficulty": "medium",
            "prompt": "What does COALESCE(NULL, NULL, 0, 100) return?",
            "choices": json.dumps([
                "NULL",
                "0",
                "100",
                "An error — COALESCE requires exactly two arguments"
            ]),
            "correct_answer": "0",
            "explanation": "COALESCE returns the first non-NULL argument, evaluated left to right. It's equivalent to a chain of CASE WHEN x IS NOT NULL THEN x ELSE ... END. NULLIF(a, b) does the opposite — it returns NULL if a equals b, otherwise returns a.",
            "hints": json.dumps(["COALESCE = first non-NULL value. NULLIF = NULL if equal."]),
            "tags": json.dumps(["sql", "null", "basics"]),
        },
        {
            "id": "q020",
            "category": "SQL Basics",
            "topic": "cross-join",
            "difficulty": "medium",
            "prompt": "What does a CROSS JOIN produce?",
            "choices": json.dumps([
                "The intersection of matching rows from two tables",
                "The Cartesian product — every row from table A paired with every row from table B",
                "Only rows that have a match in both tables",
                "A join that crosses database schemas"
            ]),
            "correct_answer": "The Cartesian product — every row from table A paired with every row from table B",
            "explanation": "CROSS JOIN produces all possible row combinations (n × m rows). It's useful for generating grids, date-spine tables, or paired comparisons. SELECT * FROM a, b (old-style comma join with no WHERE) also produces a cross join, but explicit CROSS JOIN is clearer. Be careful: joining two 1000-row tables this way produces 1,000,000 rows.",
            "hints": json.dumps(["Think of a matrix: every row × every row. Useful for generating all combinations."]),
            "tags": json.dumps(["sql", "joins", "basics"]),
        },
        {
            "id": "q021",
            "category": "Data Warehousing",
            "topic": "materialized-views",
            "difficulty": "medium",
            "prompt": "What is a materialized view?",
            "choices": json.dumps([
                "A view that only exists in memory and is lost on restart",
                "A physical copy of query results stored on disk that can be refreshed",
                "A temporary table that is automatically dropped after the session ends",
                "A view with row-level security policies applied"
            ]),
            "correct_answer": "A physical copy of query results stored on disk that can be refreshed",
            "explanation": "A materialized view stores the result set of a query as a physical table. Unlike regular views (which are just saved queries), materialized views trade storage and staleness for query speed. They're critical for pre-computing expensive aggregations in data warehouses and are commonly refreshed on a schedule.",
            "hints": json.dumps(["Regular view = saved query (no data stored). Materialized view = saved result (data stored)."]),
            "tags": json.dumps(["data-warehousing", "views", "optimization"]),
        },
        {
            "id": "q022",
            "category": "Data Modeling",
            "topic": "keys",
            "difficulty": "medium",
            "prompt": "What is a key advantage of surrogate keys over natural keys?",
            "choices": json.dumps([
                "Surrogate keys are always faster to query",
                "Surrogate keys are stable — they don't change when business attributes change",
                "Surrogate keys use less storage",
                "Surrogate keys can be shared across databases easily"
            ]),
            "correct_answer": "Surrogate keys are stable — they don't change when business attributes change",
            "explanation": "Surrogate keys (auto-incremented integers or UUIDs) are meaningless identifiers. Their key advantage: they never need to change. Natural keys (email, SSN, product_code) seem convenient but can change when business rules change — and cascading those changes is painful. Surrogate keys also avoid the problem of composite natural keys in joins.",
            "hints": json.dumps(["What happens to foreign keys everywhere when someone changes their email address?"]),
            "tags": json.dumps(["data-modeling", "keys", "theory"]),
        },
        {
            "id": "q023",
            "category": "SQL Basics",
            "topic": "transactions",
            "difficulty": "medium",
            "prompt": "Which ACID property ensures that a transaction either fully completes or has no effect at all?",
            "choices": json.dumps([
                "Consistency",
                "Isolation",
                "Atomicity",
                "Durability"
            ]),
            "correct_answer": "Atomicity",
            "explanation": "Atomicity means all or nothing — if any part of a transaction fails, the entire transaction rolls back. Consistency ensures the database remains valid before and after. Isolation controls how concurrent transactions see each other's changes. Durability guarantees committed data survives crashes.",
            "hints": json.dumps(["Think of the word 'atom' — indivisible. The transaction can't be split."]),
            "tags": json.dumps(["sql", "transactions", "theory", "basics"]),
        },
        {
            "id": "q024",
            "category": "Window Functions",
            "topic": "partition-by",
            "difficulty": "medium",
            "prompt": "How does PARTITION BY differ from GROUP BY?",
            "choices": json.dumps([
                "They are the same — PARTITION BY is just newer syntax",
                "PARTITION BY divides rows into groups for window function calculation but preserves all rows; GROUP BY collapses each group into a single row",
                "PARTITION BY requires an ORDER BY; GROUP BY does not",
                "PARTITION BY works only with numeric columns"
            ]),
            "correct_answer": "PARTITION BY divides rows into groups for window function calculation but preserves all rows; GROUP BY collapses each group into a single row",
            "explanation": "GROUP BY aggregates: multiple input rows become one output row per group. PARTITION BY defines a window for window functions: every input row still appears in the output, with the window function calculated for each row within its partition. You can use both in the same query.",
            "hints": json.dumps(["Check the number of output rows: same as input (window) vs fewer (aggregation)"]),
            "tags": json.dumps(["sql", "window-functions", "aggregation"]),
        },
        {
            "id": "q025",
            "category": "Query Optimization",
            "topic": "index-types",
            "difficulty": "medium",
            "prompt": "Which type of index is the default in most databases and is ideal for equality and range queries on sorted data?",
            "choices": json.dumps([
                "Hash index",
                "Bitmap index",
                "B-tree index",
                "GiST index"
            ]),
            "correct_answer": "B-tree index",
            "explanation": "B-tree (balanced tree) is the default index type in PostgreSQL, MySQL, and SQLite. It supports =, <, >, BETWEEN, LIKE 'prefix%', and ORDER BY efficiently. Hash indexes only support = comparisons. Bitmap indexes are ideal for low-cardinality columns in data warehouses. GiST/GIN support full-text search and geometric data.",
            "hints": json.dumps(["What index structure supports range scans (<, >, BETWEEN) in O(log n) time?"]),
            "tags": json.dumps(["sql", "optimization", "indexes"]),
        },
        {
            "id": "q026",
            "category": "SQL Basics",
            "topic": "isolation-levels",
            "difficulty": "hard",
            "prompt": "Which transaction isolation level prevents phantom reads but still allows the serialization anomaly?",
            "choices": json.dumps([
                "READ UNCOMMITTED",
                "READ COMMITTED",
                "REPEATABLE READ",
                "SERIALIZABLE"
            ]),
            "correct_answer": "REPEATABLE READ",
            "explanation": "REPEATABLE READ prevents dirty reads, non-repeatable reads, and phantom reads (in PostgreSQL and SQL Server — MySQL InnoDB's REPEATABLE READ also prevents phantoms via gap locks). However, it doesn't prevent serialization anomalies (write skew) where two transactions read overlapping data and make conflicting writes. Only SERIALIZABLE guarantees full isolation.",
            "hints": json.dumps(["4 levels: Read Uncommitted → Read Committed → Repeatable Read → Serializable. Each level adds protection."]),
            "tags": json.dumps(["sql", "transactions", "theory"]),
        },
        {
            "id": "q027",
            "category": "Query Design",
            "topic": "recursive-ctes",
            "difficulty": "hard",
            "prompt": "What are the two required parts of a recursive CTE definition?",
            "choices": json.dumps([
                "A SELECT and an INSERT",
                "A base case (anchor member) and a recursive member joined by UNION ALL",
                "An initial CTE and a terminal CTE separated by UNION",
                "A parent query and a child query joined by INNER JOIN"
            ]),
            "correct_answer": "A base case (anchor member) and a recursive member joined by UNION ALL",
            "explanation": "A recursive CTE has: (1) an anchor member — the non-recursive starting query, and (2) a recursive member that references the CTE itself, connected by UNION ALL. Example: traversing an org chart, generating a date series. Always include a termination condition to avoid infinite loops. Syntax: WITH RECURSIVE cte AS (anchor UNION ALL recursive) SELECT * FROM cte.",
            "hints": json.dumps(["Think about factorial: the base case f(1)=1 and the recursive case f(n)=n*f(n-1)."]),
            "tags": json.dumps(["sql", "ctes", "query-design", "recursion"]),
        },
        {
            "id": "q028",
            "category": "Query Optimization",
            "topic": "explain-plans",
            "difficulty": "hard",
            "prompt": "In an EXPLAIN plan, what does a 'sequential scan' on a large table indicate?",
            "choices": json.dumps([
                "The query is fully optimized and running at peak speed",
                "The database is reading every row because no suitable index exists, the predicate is too broad, or the planner calculated this is cheaper",
                "The table has no primary key defined",
                "The query will always be fast regardless of table size"
            ]),
            "correct_answer": "The database is reading every row because no suitable index exists, the predicate is too broad, or the planner calculated this is cheaper",
            "explanation": "A sequential scan reads every block of the table. On small tables this is fine — an index lookup plus random reads can be slower than a sequential read. But on large tables filtering a small percentage of rows, a sequential scan usually means a missing or unusable index, or a function-wrapped column defeating index usage.",
            "hints": json.dumps(["Sequential scan = full table scan. Is this OK for a table with 100 rows? 100 million?"]),
            "tags": json.dumps(["sql", "optimization", "execution-plan"]),
        },
        {
            "id": "q029",
            "category": "Data Modeling",
            "topic": "sharding",
            "difficulty": "hard",
            "prompt": "What is the primary trade-off when sharding a database by user_id versus by geographic region?",
            "choices": json.dumps([
                "User_id sharding is always faster; region sharding is always simpler",
                "User_id sharding distributes load evenly but makes cross-user queries hard; region sharding keeps regional data together but risks hot shards",
                "Region-based sharding is impossible in most databases",
                "There is no difference — the shard key is irrelevant"
            ]),
            "correct_answer": "User_id sharding distributes load evenly but makes cross-user queries hard; region sharding keeps regional data together but risks hot shards",
            "explanation": "Sharding by user_id (or a hash of it) gives uniform distribution but queries spanning multiple users hit many shards. Sharding by region co-locates related data (all of Europe on one shard) but regions may be unevenly sized — the US shard may be overwhelmed while APAC is idle. The choice depends on access patterns.",
            "hints": json.dumps(["Think about your queries: do they touch one user at a time, or do they aggregate across regions?"]),
            "tags": json.dumps(["data-modeling", "sharding", "system-design"]),
        },
        {
            "id": "q030",
            "category": "Data Warehousing",
            "topic": "storage-models",
            "difficulty": "hard",
            "prompt": "Why are columnar databases generally faster than row-based databases for analytical queries on wide tables?",
            "choices": json.dumps([
                "Columnar databases have better indexes",
                "Columnar storage reads only relevant columns from disk, benefits from better compression via homogeneous data, and uses vectorized processing",
                "Row-based databases are obsolete",
                "Columnar databases use faster hardware"
            ]),
            "correct_answer": "Columnar storage reads only relevant columns from disk, benefits from better compression via homogeneous data, and uses vectorized processing",
            "explanation": "Analytical queries often touch few columns (e.g., SUM(revenue) GROUP BY region) but scan many rows. Columnar storage stores each column separately, so only the needed columns are read. Columns of the same type compress extremely well (run-length encoding, dictionary encoding). Vectorized processing operates on batches of column values, leveraging modern CPU SIMD instructions.",
            "hints": json.dumps(["If your query only needs 3 of 50 columns, how much of a row-based table must be read from disk?"]),
            "tags": json.dumps(["data-warehousing", "storage", "optimization"]),
        },
        {
            "id": "q031",
            "category": "Data Modeling",
            "topic": "denormalization",
            "difficulty": "hard",
            "prompt": "When is denormalization an appropriate optimization?",
            "choices": json.dumps([
                "Always — normalized schemas are slow by design",
                "When read performance for a specific query pattern is critical, the redundant data can be kept consistent, and the write overhead is acceptable",
                "Only during data migration projects",
                "Denormalization is never appropriate in a well-designed system"
            ]),
            "correct_answer": "When read performance for a specific query pattern is critical, the redundant data can be kept consistent, and the write overhead is acceptable",
            "explanation": "Denormalization trades write performance and data integrity risk for read speed. It makes sense for read-heavy analytical workloads (OLAP), caching frequent joins, or when the cost of joins at query time exceeds the cost of maintaining redundant data. But it introduces update anomalies — you must have a strategy to keep denormalized data consistent.",
            "hints": json.dumps(["Which is more expensive in your workload: computing the join every time, or maintaining duplicate data?"]),
            "tags": json.dumps(["data-modeling", "denormalization", "optimization"]),
        },
        {
            "id": "q032",
            "category": "SQL Basics",
            "topic": "upsert",
            "difficulty": "hard",
            "prompt": "What potential race condition does a naive 'SELECT then INSERT or UPDATE' pattern have that MERGE (or INSERT...ON CONFLICT) solves?",
            "choices": json.dumps([
                "The SELECT might return stale data from cache",
                "A concurrent transaction could insert the same key between your SELECT and INSERT, causing a duplicate key error or lost update",
                "MERGE is just syntactic sugar — it provides no concurrency benefits",
                "SELECT-then-INSERT is faster than MERGE in all databases"
            ]),
            "correct_answer": "A concurrent transaction could insert the same key between your SELECT and INSERT, causing a duplicate key error or lost update",
            "explanation": "The SELECT-then-INSERT pattern has a TOCTOU (time-of-check to time-of-use) race condition. Two concurrent sessions can both SELECT and find no row, then both INSERT — one fails with a duplicate key. MERGE (SQL standard) and INSERT...ON CONFLICT (PostgreSQL/SQLite) make the upsert atomic: the database handles the conditional insert-or-update in a single operation.",
            "hints": json.dumps(["Think about two users registering with the same email at the exact same moment."]),
            "tags": json.dumps(["sql", "transactions", "concurrency", "basics"]),
        },
        {
            "id": "q033",
            "category": "Query Design",
            "topic": "lateral-joins",
            "difficulty": "hard",
            "prompt": "What capability does a LATERAL JOIN provide that a regular JOIN cannot?",
            "choices": json.dumps([
                "LATERAL JOINs are faster than regular JOINs in all cases",
                "A LATERAL subquery can reference columns from preceding FROM items, enabling per-row dynamic queries like 'top N related rows per parent'",
                "LATERAL JOINs automatically create indexes",
                "LATERAL JOINs work only with LEFT JOINs"
            ]),
            "correct_answer": "A LATERAL subquery can reference columns from preceding FROM items, enabling per-row dynamic queries like 'top N related rows per parent'",
            "explanation": "LATERAL lets a subquery in the FROM clause reference columns from tables listed before it. This enables patterns like: 'for each user, find their 3 most recent orders' using a single query. Without LATERAL, you'd use a correlated subquery in SELECT (returning one column) or a window function. LATERAL returns full rows per iteration.",
            "hints": json.dumps(["Think 'for each X, run this subquery with X as a parameter.' It's a foreach loop in SQL."]),
            "tags": json.dumps(["sql", "joins", "query-design"]),
        },
        {
            "id": "q034",
            "category": "Data Warehousing",
            "topic": "view-refresh",
            "difficulty": "hard",
            "prompt": "What is the downside of a materialized view with REFRESH COMPLETE versus REFRESH FAST (incremental)?",
            "choices": json.dumps([
                "REFRESH COMPLETE yields incorrect results",
                "REFRESH COMPLETE recomputes the entire view from scratch, which can be slow and resource-intensive on large tables",
                "REFRESH FAST requires dropping and recreating the view",
                "There is no difference — they are synonyms"
            ]),
            "correct_answer": "REFRESH COMPLETE recomputes the entire view from scratch, which can be slow and resource-intensive on large tables",
            "explanation": "COMPLETE refresh reruns the entire defining query — fine for small datasets, prohibitive for billion-row fact tables. FAST (incremental) refresh only applies changes since the last refresh using materialized view logs that track inserts, updates, and deletes. The trade-off: FAST refresh requires maintaining these logs (storage + write overhead) but refreshes much faster.",
            "hints": json.dumps(["Complete = full re-run. Fast = only changes. What must the database track to support 'only changes'?"]),
            "tags": json.dumps(["data-warehousing", "views", "optimization"]),
        },
        {
            "id": "q035",
            "category": "Query Optimization",
            "topic": "bloom-filters",
            "difficulty": "hard",
            "prompt": "How are Bloom filters used in database query processing?",
            "choices": json.dumps([
                "To encrypt data at rest",
                "To quickly test whether a value might exist in a set before doing an expensive lookup — used in join optimization and LSM-trees",
                "To sort data faster than a B-tree",
                "To compress column data losslessly"
            ]),
            "correct_answer": "To quickly test whether a value might exist in a set before doing an expensive lookup — used in join optimization and LSM-trees",
            "explanation": "A Bloom filter is a probabilistic data structure that answers 'might this key exist?' — it can return false positives (says 'maybe' when the key isn't there) but never false negatives. Databases use them for semi-join reductions, LSM-tree reads (check if a key might be in a given SSTable before reading it), and distributed query optimization to avoid shipping unnecessary rows.",
            "hints": json.dumps(["Probabilistic: 'maybe present' or 'definitely absent.' Why is 'definitely absent' useful?"]),
            "tags": json.dumps(["sql", "optimization", "data-structures"]),
        },

        # ========== EASY (10) ==========
        {
            "id": "q036",
            "category": "SQL Basics",
            "topic": "distinct",
            "difficulty": "easy",
            "prompt": "What does SELECT DISTINCT do?",
            "choices": json.dumps([
                "Selects only the first row from the result set",
                "Removes duplicate rows from the result set",
                "Sorts the result set alphabetically",
                "Selects rows that are different from the previous query"
            ]),
            "correct_answer": "Removes duplicate rows from the result set",
            "explanation": "DISTINCT eliminates duplicate rows so each row in the result is unique. It applies to all columns in the SELECT list. SELECT DISTINCT ON (col) in PostgreSQL returns only the first row for each distinct value of col.",
            "hints": json.dumps(["What if you run SELECT department FROM employees and get 100 rows but only 5 unique departments?"]),
            "tags": json.dumps(["sql", "basics", "distinct"]),
        },
        {
            "id": "q037",
            "category": "SQL Basics",
            "topic": "aggregation",
            "difficulty": "easy",
            "prompt": "What is the difference between COUNT(*) and COUNT(column)?",
            "choices": json.dumps([
                "COUNT(*) is slower; COUNT(column) is faster",
                "COUNT(*) counts all rows; COUNT(column) counts only non-NULL values in that column",
                "COUNT(*) includes NULLs; COUNT(column) counts NULLs twice",
                "There is no difference"
            ]),
            "correct_answer": "COUNT(*) counts all rows; COUNT(column) counts only non-NULL values in that column",
            "explanation": "COUNT(*) counts every row regardless of NULLs. COUNT(column) counts only rows where that column is NOT NULL. COUNT(DISTINCT column) counts unique non-NULL values. This is a common interview question because it reveals whether you understand NULL handling.",
            "hints": json.dumps(["What happens if the column contains NULL values?"]),
            "tags": json.dumps(["sql", "aggregation", "basics"]),
        },
        {
            "id": "q038",
            "category": "SQL Basics",
            "topic": "limit",
            "difficulty": "easy",
            "prompt": "What does LIMIT 10 do in a query?",
            "choices": json.dumps([
                "Restricts each column to 10 characters",
                "Returns only the first 10 rows of the result set",
                "Limits the query execution time to 10 seconds",
                "Paginates the result into groups of 10"
            ]),
            "correct_answer": "Returns only the first 10 rows of the result set",
            "explanation": "LIMIT restricts the number of rows returned. Often paired with OFFSET for pagination: LIMIT 10 OFFSET 20 returns rows 21-30. Note: without ORDER BY, which 10 rows you get is non-deterministic. Different databases use different syntax: FETCH FIRST (SQL standard), TOP (SQL Server), ROWNUM (Oracle).",
            "hints": json.dumps(["If you combine LIMIT with ORDER BY, you get 'top N' semantics."]),
            "tags": json.dumps(["sql", "basics", "limit"]),
        },
        {
            "id": "q039",
            "category": "SQL Basics",
            "topic": "insert",
            "difficulty": "easy",
            "prompt": "Which SQL statement adds new rows to a table?",
            "choices": json.dumps([
                "ADD",
                "INSERT",
                "CREATE",
                "APPEND"
            ]),
            "correct_answer": "INSERT",
            "explanation": "INSERT INTO table_name (col1, col2) VALUES (val1, val2) adds one or more rows. You can also INSERT INTO ... SELECT to copy rows from another table. Some databases support multi-row VALUES: INSERT INTO t (a, b) VALUES (1,2), (3,4), (5,6).",
            "hints": json.dumps(["The 'I' in CRUD (Create, Read, Update, Delete) — which SQL keyword implements Create?"]),
            "tags": json.dumps(["sql", "dml", "basics"]),
        },
        {
            "id": "q040",
            "category": "SQL Basics",
            "topic": "update",
            "difficulty": "easy",
            "prompt": "What happens if you run UPDATE users SET status = 'inactive' without a WHERE clause?",
            "choices": json.dumps([
                "Nothing — UPDATE requires a WHERE clause",
                "Every row's status column is set to 'inactive'",
                "Only the first row is updated",
                "The database throws a syntax error"
            ]),
            "correct_answer": "Every row's status column is set to 'inactive'",
            "explanation": "Without a WHERE clause, UPDATE affects every row in the table. This is one of the most common (and dangerous) SQL mistakes. Always double-check your WHERE clause before running UPDATE or DELETE. Some tools require explicit confirmation for unqualified writes — consider using BEGIN/ROLLBACK as a safety net.",
            "hints": json.dumps(["UPDATE without WHERE is like 'update ALL rows.' Is that usually intended?"]),
            "tags": json.dumps(["sql", "dml", "basics"]),
        },
        {
            "id": "q041",
            "category": "SQL Basics",
            "topic": "delete-vs-truncate",
            "difficulty": "easy",
            "prompt": "What is the key difference between DELETE and TRUNCATE?",
            "choices": json.dumps([
                "DELETE removes rows; TRUNCATE removes columns",
                "DELETE is DML and can have a WHERE clause; TRUNCATE is DDL that removes all rows faster and resets auto-increment counters",
                "TRUNCATE is slower than DELETE",
                "DELETE requires a transaction; TRUNCATE does not"
            ]),
            "correct_answer": "DELETE is DML and can have a WHERE clause; TRUNCATE is DDL that removes all rows faster and resets auto-increment counters",
            "explanation": "DELETE logs each row removal individually, can be rolled back, and fires triggers. TRUNCATE deallocates data pages — much faster on large tables — but usually can't be rolled back in all databases and doesn't fire row-level triggers. TRUNCATE also resets identity/auto-increment counters.",
            "hints": json.dumps(["One is row-by-row (slow, safe), the other is bulk (fast, less granular). Which is which?"]),
            "tags": json.dumps(["sql", "dml", "ddl", "basics"]),
        },
        {
            "id": "q042",
            "category": "SQL Basics",
            "topic": "like",
            "difficulty": "easy",
            "prompt": "What does WHERE name LIKE 'A%' match?",
            "choices": json.dumps([
                "Names that contain the letter A anywhere",
                "Names that start with the letter A",
                "Names that end with the letter A",
                "Names exactly equal to 'A'"
            ]),
            "correct_answer": "Names that start with the letter A",
            "explanation": "In LIKE patterns: % matches any sequence of characters (including empty), _ matches exactly one character. 'A%' = starts with A. '%A' = ends with A. '%A%' = contains A. 'A_' = A followed by exactly one character. Use ILIKE (PostgreSQL) for case-insensitive matching. LIKE on an indexed column can use the index for prefix searches ('A%') but not for '%A'.",
            "hints": json.dumps(["% is a wildcard that matches zero or more characters. Where is it placed relative to A?"]),
            "tags": json.dumps(["sql", "filtering", "basics"]),
        },
        {
            "id": "q043",
            "category": "SQL Basics",
            "topic": "in-operator",
            "difficulty": "easy",
            "prompt": "What is the equivalent of WHERE status IN ('active', 'pending', 'trial') using basic operators?",
            "choices": json.dumps([
                "WHERE status = 'active' AND status = 'pending' AND status = 'trial'",
                "WHERE status = 'active' OR status = 'pending' OR status = 'trial'",
                "WHERE status BETWEEN 'active' AND 'trial'",
                "WHERE status IS ANY OF ('active', 'pending', 'trial')"
            ]),
            "correct_answer": "WHERE status = 'active' OR status = 'pending' OR status = 'trial'",
            "explanation": "IN is syntactic sugar for a chain of OR conditions. It's more readable and the query planner often optimizes it into a hash lookup. IN works with subqueries too: WHERE dept_id IN (SELECT id FROM departments WHERE region = 'West'). Be careful with NOT IN and NULLs — a single NULL in the subquery result makes NOT IN return no rows.",
            "hints": json.dumps(["If I ask 'Is the color red, blue, or green?' — how would you express that with simple equals checks?"]),
            "tags": json.dumps(["sql", "filtering", "basics"]),
        },
        {
            "id": "q044",
            "category": "SQL Basics",
            "topic": "between",
            "difficulty": "easy",
            "prompt": "Is BETWEEN 10 AND 20 inclusive or exclusive of the endpoints?",
            "choices": json.dumps([
                "Exclusive — returns values 11 through 19",
                "Inclusive — returns values 10 through 20 (including both 10 and 20)",
                "Inclusive of 10 but exclusive of 20",
                "It depends on the database"
            ]),
            "correct_answer": "Inclusive — returns values 10 through 20 (including both 10 and 20)",
            "explanation": "BETWEEN is inclusive on both ends in all SQL databases. WHERE price BETWEEN 10 AND 20 is equivalent to WHERE price >= 10 AND price <= 20. Be careful with dates: BETWEEN '2024-01-01' AND '2024-12-31' includes all of Dec 31, but BETWEEN with timestamps may miss the end of the last day.",
            "hints": json.dumps(["Write it out long-form: >= low AND <= high. Inclusive means the boundaries are included."]),
            "tags": json.dumps(["sql", "filtering", "basics"]),
        },
        {
            "id": "q045",
            "category": "SQL Basics",
            "topic": "aliases",
            "difficulty": "easy",
            "prompt": "When can you use a column alias defined in the SELECT clause in the WHERE clause?",
            "choices": json.dumps([
                "Always — aliases work everywhere in the query",
                "Never — WHERE is evaluated before SELECT in logical query processing",
                "Only when the alias is a single word",
                "Only in MySQL"
            ]),
            "correct_answer": "Never — WHERE is evaluated before SELECT in logical query processing",
            "explanation": "SQL's logical processing order is FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY. Aliases defined in SELECT don't exist yet when WHERE is processed. This is why you must repeat the expression: WHERE salary * 1.1 > 100000 instead of using an alias defined in SELECT. Aliases DO work in ORDER BY because SELECT has already been evaluated by then.",
            "hints": json.dumps(["Logical order: FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY. Where does SELECT fall relative to WHERE?"]),
            "tags": json.dumps(["sql", "aliases", "basics"]),
        },

        # ========== MEDIUM (10) ==========
        {
            "id": "q046",
            "category": "SQL Basics",
            "topic": "group-by",
            "difficulty": "medium",
            "prompt": "What does GROUP BY department, region produce?",
            "choices": json.dumps([
                "A single group per department, ignoring region",
                "One group for each unique combination of department and region",
                "Two separate GROUP BYs run sequentially",
                "An error — GROUP BY only accepts one column"
            ]),
            "correct_answer": "One group for each unique combination of department and region",
            "explanation": "GROUP BY with multiple columns creates groups for every distinct combination. If you have 5 departments and 4 regions, you could have up to 20 groups (fewer if some combinations don't exist). Every non-aggregated column in SELECT must appear in GROUP BY (unless functionally dependent in some databases like MySQL with ONLY_FULL_GROUP_BY disabled).",
            "hints": json.dumps(["Think of it like a pivot table: group first by department, then sub-group by region within each department."]),
            "tags": json.dumps(["sql", "aggregation", "group-by"]),
        },
        {
            "id": "q047",
            "category": "SQL Basics",
            "topic": "having-vs-where",
            "difficulty": "medium",
            "prompt": "Why would you use HAVING instead of WHERE in a query with GROUP BY?",
            "choices": json.dumps([
                "HAVING is faster than WHERE for grouped queries",
                "HAVING filters on aggregated values (e.g., SUM, COUNT) after grouping, while WHERE filters individual rows before grouping",
                "HAVING works with any column; WHERE only works with indexed columns",
                "They are interchangeable — it's just a style preference"
            ]),
            "correct_answer": "HAVING filters on aggregated values (e.g., SUM, COUNT) after grouping, while WHERE filters individual rows before grouping",
            "explanation": "WHERE filters rows before they enter GROUP BY. HAVING filters the groups after aggregation. You can't use aggregate functions in WHERE (WHERE SUM(sales) > 1000 is illegal). Best practice: put row-level filters in WHERE to reduce data before aggregation, then use HAVING for aggregate conditions.",
            "hints": json.dumps(["Can you filter on SUM(sales) in a WHERE clause? If not, where would you put that filter?"]),
            "tags": json.dumps(["sql", "aggregation", "filtering"]),
        },
        {
            "id": "q048",
            "category": "SQL Basics",
            "topic": "case-expressions",
            "difficulty": "medium",
            "prompt": "What does CASE WHEN x > 0 THEN 'positive' WHEN x < 0 THEN 'negative' ELSE 'zero' END do?",
            "choices": json.dumps([
                "Loops through all values of x and updates the table",
                "Returns a value based on the first matching condition, evaluating conditions in order",
                "Creates a temporary table with the categorized values",
                "Checks if column x exists and creates it if not"
            ]),
            "correct_answer": "Returns a value based on the first matching condition, evaluating conditions in order",
            "explanation": "CASE is SQL's if/else construct. Conditions are evaluated in order and the first match wins — subsequent WHEN clauses are skipped. If no WHEN matches and there's no ELSE, NULL is returned. CASE can be used in SELECT, WHERE, ORDER BY, and even GROUP BY. There's also a shorthand: CASE column WHEN value1 THEN ... for simple equality checks.",
            "hints": json.dumps(["Conditions are evaluated top-to-bottom. The first true condition wins — just like if/else-if/else in programming."]),
            "tags": json.dumps(["sql", "expressions", "case"]),
        },
        {
            "id": "q049",
            "category": "SQL Basics",
            "topic": "casting",
            "difficulty": "medium",
            "prompt": "What happens when you CAST('2024-01-15' AS DATE) on a string that doesn't match the expected format?",
            "choices": json.dumps([
                "The CAST silently returns NULL",
                "The database raises an error because the string format is invalid for the target type",
                "It defaults to January 1, 1900",
                "CAST never fails — it always returns the original string"
            ]),
            "correct_answer": "The database raises an error because the string format is invalid for the target type",
            "explanation": "CAST and :: (PostgreSQL shorthand) will error on invalid conversions. For safe conversions, use TRY_CAST (SQL Server), SAFE_CAST (BigQuery), or catch exceptions. Implicit casts happen automatically in expressions like '5' + 2 (database-dependent behavior). Always be explicit about type conversions for clarity and portability.",
            "hints": json.dumps(["If you try to turn 'hello' into an integer, what should happen?"]),
            "tags": json.dumps(["sql", "types", "casting"]),
        },
        {
            "id": "q050",
            "category": "SQL Basics",
            "topic": "string-functions",
            "difficulty": "medium",
            "prompt": "Which set of string functions would you use to extract the domain from an email address like 'user@example.com'?",
            "choices": json.dumps([
                "LEFT and RIGHT",
                "SUBSTRING combined with POSITION/CHARINDEX of '@'",
                "REPLACE and TRIM",
                "UPPER and LOWER"
            ]),
            "correct_answer": "SUBSTRING combined with POSITION/CHARINDEX of '@'",
            "explanation": "POSITION('@' IN email) or CHARINDEX('@', email) finds the index of '@'. Then SUBSTRING(email FROM position + 1) extracts everything after it. Common string functions: CONCAT, UPPER, LOWER, TRIM, LENGTH, REPLACE, LEFT, RIGHT. Note: function names vary across databases — check your DB's documentation.",
            "hints": json.dumps(["First find where '@' is, then take everything after that position."]),
            "tags": json.dumps(["sql", "string-functions", "basics"]),
        },
        {
            "id": "q051",
            "category": "SQL Basics",
            "topic": "date-functions",
            "difficulty": "medium",
            "prompt": "How would you count the number of days between two dates in standard SQL?",
            "choices": json.dumps([
                "DAYS_BETWEEN(date1, date2)",
                "Simply subtract one date from another: date1 - date2 (exact syntax varies by database)",
                "COUNT_DAYS(date1, date2)",
                "Dates can't be subtracted in SQL"
            ]),
            "correct_answer": "Simply subtract one date from another: date1 - date2 (exact syntax varies by database)",
            "explanation": "Date arithmetic varies significantly across databases. PostgreSQL: date1 - date2 returns integer days. SQL Server: DATEDIFF(day, date2, date1). MySQL: DATEDIFF(date1, date2). SQLite: julianday(date1) - julianday(date2). Always check your database's date functions — this is one of the least portable areas of SQL.",
            "hints": json.dumps(["In many databases, dates support arithmetic. What does 'Jan 10' - 'Jan 1' conceptually represent?"]),
            "tags": json.dumps(["sql", "dates", "functions"]),
        },
        {
            "id": "q052",
            "category": "SQL Basics",
            "topic": "self-join",
            "difficulty": "medium",
            "prompt": "What is a self-join used for?",
            "choices": json.dumps([
                "Joining a table with its own backup copy",
                "Querying hierarchical relationships within a single table, such as employees and their managers",
                "Making queries run twice as fast",
                "Self-joins are not supported in standard SQL"
            ]),
            "correct_answer": "Querying hierarchical relationships within a single table, such as employees and their managers",
            "explanation": "A self-join joins a table to itself using table aliases: SELECT e.name AS employee, m.name AS manager FROM employees e LEFT JOIN employees m ON e.manager_id = m.id. It's essential for adjacency-list hierarchies, finding duplicates, or comparing rows within the same table. If the hierarchy is deep, consider a recursive CTE instead.",
            "hints": json.dumps(["How would you list every employee alongside their manager if both are in the same employees table?"]),
            "tags": json.dumps(["sql", "joins", "self-join"]),
        },
        {
            "id": "q053",
            "category": "SQL Basics",
            "topic": "full-outer-join",
            "difficulty": "medium",
            "prompt": "When would you use a FULL OUTER JOIN?",
            "choices": json.dumps([
                "When you only want matching rows from both tables",
                "When you want all rows from both tables — matching where possible, NULLs where there's no match on either side",
                "When both tables have identical schemas",
                "FULL OUTER JOIN is the default join type in all databases"
            ]),
            "correct_answer": "When you want all rows from both tables — matching where possible, NULLs where there's no match on either side",
            "explanation": "FULL OUTER JOIN returns all rows from both tables. Rows with matches are combined; rows without a match on the left have NULLs for right columns, and vice versa. It's the union of LEFT JOIN and RIGHT JOIN. Common use: comparing two versions of a dataset to find additions, deletions, and changes in one query.",
            "hints": json.dumps(["LEFT JOIN = all from left. RIGHT JOIN = all from right. What gives you ALL from BOTH?"]),
            "tags": json.dumps(["sql", "joins", "outer-join"]),
        },
        {
            "id": "q054",
            "category": "Query Optimization",
            "topic": "composite-indexes",
            "difficulty": "medium",
            "prompt": "For a composite index on (last_name, first_name), which query benefits most?",
            "choices": json.dumps([
                "WHERE first_name = 'John'",
                "WHERE last_name = 'Smith'",
                "WHERE last_name = 'Smith' AND first_name = 'John'",
                "WHERE first_name = 'John' OR last_name = 'Smith'"
            ]),
            "correct_answer": "WHERE last_name = 'Smith' AND first_name = 'John'",
            "explanation": "A composite index is ordered by the first key, then the second. It's like a phone book: ordered by last_name, then first_name. The index can be used for: (1) last_name alone (prefix), (2) last_name + first_name together. It generally CANNOT be used for first_name alone (you can't efficiently find all 'John's without scanning the whole index). This is the 'leftmost prefix' rule.",
            "hints": json.dumps(["Think of a phone book sorted by last name then first name. Can you find all people named 'John' efficiently?"]),
            "tags": json.dumps(["sql", "optimization", "indexes"]),
        },
        {
            "id": "q055",
            "category": "Query Design",
            "topic": "cte-vs-subquery",
            "difficulty": "medium",
            "prompt": "Are CTEs always materialized (computed and stored) separately from the main query?",
            "choices": json.dumps([
                "Yes — that's what makes them faster",
                "No — in most databases CTEs are inlined into the main query like subqueries (PostgreSQL, SQLite, MySQL), though PostgreSQL can materialize them automatically as an optimization",
                "CTEs are always materialized in MySQL but never in PostgreSQL",
                "Yes — CTEs are always stored as temporary tables on disk"
            ]),
            "correct_answer": "No — in most databases CTEs are inlined into the main query like subqueries (PostgreSQL, SQLite, MySQL), though PostgreSQL can materialize them automatically as an optimization",
            "explanation": "Historically, PostgreSQL always materialized CTEs (acting as an optimization fence), but since PG 12 it can inline them — and does so by default. Use MATERIALIZED or NOT MATERIALIZED to control behavior. SQLite and MySQL inline CTEs. This matters because an inlined CTE can benefit from indexes and predicate pushdown, while a materialized one can prevent repeated computation when referenced multiple times.",
            "hints": json.dumps(["If a CTE is inlined, it's essentially a macro — the query planner sees the full query. Is that good or bad?"]),
            "tags": json.dumps(["sql", "ctes", "query-design", "optimization"]),
        },

        # ========== HARD (10) ==========
        {
            "id": "q056",
            "category": "Query Optimization",
            "topic": "join-algorithms",
            "difficulty": "hard",
            "prompt": "When would the query planner choose a Hash Join over a Nested Loop Join?",
            "choices": json.dumps([
                "When joining on indexed foreign keys with small lookup counts",
                "When joining large, unsorted tables on an equality condition — hash joins are O(n+m) while nested loops are O(n×m)",
                "When the join condition uses inequality (>, <, !=)",
                "Hash joins are always preferred over nested loops"
            ]),
            "correct_answer": "When joining large, unsorted tables on an equality condition — hash joins are O(n+m) while nested loops are O(n×m)",
            "explanation": "Nested loop: for each row in the outer table, scan the inner table — great for indexed lookups of few rows, terrible for large unindexed joins. Hash join: build a hash table from the smaller table, then probe it for each row from the larger table — excellent for large equality joins but only works with = conditions. Merge join: both inputs sorted by join key, then merged — great for large sorted datasets and supports range conditions.",
            "hints": json.dumps(["Think about the algorithm: O(n²) nested loops vs O(n) hashing. When does the O(n) win despite build cost?"]),
            "tags": json.dumps(["sql", "optimization", "join-algorithms"]),
        },
        {
            "id": "q057",
            "category": "SQL Basics",
            "topic": "deadlocks",
            "difficulty": "hard",
            "prompt": "What causes a database deadlock?",
            "choices": json.dumps([
                "A single query running too slowly and timing out",
                "Two or more transactions each holding locks that the other needs, creating a circular dependency where neither can proceed",
                "Running too many SELECT queries simultaneously",
                "Using too many indexes on a table"
            ]),
            "correct_answer": "Two or more transactions each holding locks that the other needs, creating a circular dependency where neither can proceed",
            "explanation": "Classic deadlock: TxA locks row 1 and wants row 2. TxB locks row 2 and wants row 1. Neither can proceed. The database detects this and kills one transaction (the 'victim'). Prevention: always lock resources in the same order, keep transactions short, use lower isolation levels when safe, and design your access patterns to avoid circular waits.",
            "hints": json.dumps(["Picture two people crossing a narrow bridge from opposite sides. Neither can move forward."]),
            "tags": json.dumps(["sql", "transactions", "concurrency", "theory"]),
        },
        {
            "id": "q058",
            "category": "Data Modeling",
            "topic": "partitioning",
            "difficulty": "hard",
            "prompt": "What is partition pruning and why does it improve query performance?",
            "choices": json.dumps([
                "It deletes old partitions to save disk space",
                "The query planner skips partitions that can't contain relevant data based on the WHERE clause, reducing the amount of data scanned",
                "It compresses partitions for faster reads",
                "It converts partitioned tables into regular tables"
            ]),
            "correct_answer": "The query planner skips partitions that can't contain relevant data based on the WHERE clause, reducing the amount of data scanned",
            "explanation": "When a table is partitioned by date (e.g., each month is a partition) and you query WHERE order_date = '2024-06-15', the planner knows to scan only the June 2024 partition — pruning the other partitions entirely. This turns a full-table scan into a scan of only relevant data. For it to work, the partition key must appear in WHERE without being wrapped in functions.",
            "hints": json.dumps(["If you partition by month and query a specific date, do you need to scan every partition?"]),
            "tags": json.dumps(["data-modeling", "partitioning", "optimization"]),
        },
        {
            "id": "q059",
            "category": "Query Optimization",
            "topic": "predicate-pushdown",
            "difficulty": "hard",
            "prompt": "What is predicate pushdown in query optimization?",
            "choices": json.dumps([
                "Moving WHERE conditions as close to the data source as possible — even into subqueries, CTEs, or remote foreign tables — to filter rows early",
                "Converting all predicates to use indexes automatically",
                "Removing unnecessary predicates from the query",
                "A technique to push updates to the database faster"
            ]),
            "correct_answer": "Moving WHERE conditions as close to the data source as possible — even into subqueries, CTEs, or remote foreign tables — to filter rows early",
            "explanation": "Predicate pushdown is a critical optimization: filter as early as possible. In a query like SELECT * FROM (SELECT * FROM huge_table) sub WHERE x > 100, the optimizer pushes x > 100 into the subquery rather than scanning the whole table. In federated queries (foreign data wrappers, BigQuery external tables), predicate pushdown sends filters to the remote source, reducing data transfer.",
            "hints": json.dumps(["Filter early, filter often. Why ship a million rows across the network when you only need 10?"]),
            "tags": json.dumps(["sql", "optimization", "execution-plan"]),
        },
        {
            "id": "q060",
            "category": "Query Optimization",
            "topic": "cardinality-estimation",
            "difficulty": "hard",
            "prompt": "Why does poor cardinality estimation lead to bad query plans?",
            "choices": json.dumps([
                "It doesn't — cardinality is unrelated to query performance",
                "The planner makes join order and algorithm decisions based on estimated row counts; if estimates are wrong, it may pick a slow nested loop instead of a hash join",
                "Cardinality only matters for ORM queries, not raw SQL",
                "Poor cardinality always causes full table scans"
            ]),
            "correct_answer": "The planner makes join order and algorithm decisions based on estimated row counts; if estimates are wrong, it may pick a slow nested loop instead of a hash join",
            "explanation": "The query planner relies on statistics (n_distinct, histograms, MCV lists) to estimate how many rows each operation will produce. If it estimates 10 rows (actually 1M), it might choose a nested loop that runs 1M times. If it estimates 1M rows (actually 10), it might build a hash table unnecessarily. Keeping statistics fresh (ANALYZE/VACUUM) and understanding your data's distribution is critical for tuning.",
            "hints": json.dumps(["ANALYZE updates table statistics. What happens to the planner if you never run it after massive data changes?"]),
            "tags": json.dumps(["sql", "optimization", "statistics"]),
        },
        {
            "id": "q061",
            "category": "Query Optimization",
            "topic": "covering-indexes",
            "difficulty": "hard",
            "prompt": "What makes an index a 'covering index' for a query?",
            "choices": json.dumps([
                "It covers only the primary key columns",
                "It includes all columns needed by the query — both in the WHERE and SELECT — so the database can satisfy the entire query from the index without touching the table",
                "It is the largest index on the table",
                "It uses a special covering algorithm to overlap with other indexes"
            ]),
            "correct_answer": "It includes all columns needed by the query — both in the WHERE and SELECT — so the database can satisfy the entire query from the index without touching the table",
            "explanation": "A covering index contains every column referenced in the query. The database can perform an index-only scan: all data comes from the index, never touching the heap/table. This can be dramatically faster because indexes are typically smaller and better cached. In PostgreSQL, include non-key columns with INCLUDE (col) clause. In SQL Server, use INCLUDE. In MySQL InnoDB, secondary indexes automatically include the primary key.",
            "hints": json.dumps(["If the index has every column the query asks for, why would the database ever need to read the actual table?"]),
            "tags": json.dumps(["sql", "optimization", "indexes"]),
        },
        {
            "id": "q062",
            "category": "Query Optimization",
            "topic": "full-text-indexes",
            "difficulty": "hard",
            "prompt": "Why can't a standard B-tree index efficiently handle WHERE description LIKE '%keyword%'?",
            "choices": json.dumps([
                "B-tree indexes can handle any LIKE pattern efficiently",
                "B-trees are optimized for prefix matching; a leading wildcard ('%keyword') means the database can't use the index and must scan every row",
                "B-tree indexes can only index integer columns",
                "LIKE queries are always fast regardless of indexing"
            ]),
            "correct_answer": "B-trees are optimized for prefix matching; a leading wildcard ('%keyword') means the database can't use the index and must scan every row",
            "explanation": "B-trees work by comparison order. LIKE 'prefix%' can use an index because it's a range scan (all values between 'prefix' and 'prefiy'). But '%middle%' requires finding the substring anywhere in the string — the B-tree has no way to locate these efficiently. For full-text search, use GIN (PostgreSQL), full-text indexes (SQL Server, MySQL), or specialized search engines like Elasticsearch.",
            "hints": json.dumps(["A B-tree knows what comes first and last, not what's in the middle. A phone book is sorted by names — can you quickly find all names containing 'son'?"]),
            "tags": json.dumps(["sql", "optimization", "indexes", "full-text"]),
        },
        {
            "id": "q063",
            "category": "SQL Basics",
            "topic": "mvcc",
            "difficulty": "hard",
            "prompt": "How does MVCC (Multi-Version Concurrency Control) allow readers to not block writers and writers to not block readers?",
            "choices": json.dumps([
                "It serializes all queries so no two can run simultaneously",
                "Writers create new versions of rows while old versions are kept for ongoing readers, so readers see a consistent snapshot without waiting for writers to finish",
                "It stores all data in memory so disk I/O never blocks queries",
                "It copies the entire database for each transaction"
            ]),
            "correct_answer": "Writers create new versions of rows while old versions are kept for ongoing readers, so readers see a consistent snapshot without waiting for writers to finish",
            "explanation": "MVCC keeps multiple versions of each row. When a transaction starts, it gets a snapshot — it sees the database as it existed at that moment. Writers create new row versions; readers continue reading the old versions. This eliminates read-write conflicts. The cost: old versions need periodic cleanup (VACUUM in PostgreSQL, undo log purging in MySQL/InnoDB). MVCC is why PostgreSQL, Oracle, and MySQL InnoDB handle concurrent workloads well.",
            "hints": json.dumps(["Old versions aren't immediately deleted when you UPDATE — they hang around. Who might still need them?"]),
            "tags": json.dumps(["sql", "transactions", "concurrency", "theory"]),
        },
        {
            "id": "q064",
            "category": "ETL Concepts",
            "topic": "change-data-capture",
            "difficulty": "hard",
            "prompt": "What is Change Data Capture (CDC) and when is it preferable to full-load ETL?",
            "choices": json.dumps([
                "CDC is just another name for full-table reloads",
                "CDC captures only the rows that changed (INSERTs, UPDATEs, DELETEs) since the last sync, making it ideal for large tables where only a small fraction changes between runs",
                "CDC replaces the need for primary keys",
                "CDC only works with cloud databases"
            ]),
            "correct_answer": "CDC captures only the rows that changed (INSERTs, UPDATEs, DELETEs) since the last sync, making it ideal for large tables where only a small fraction changes between runs",
            "explanation": "CDC tracks changes to source data and propagates only the deltas to downstream systems. Methods: trigger-based (DB triggers capture changes), log-based (reads the database's transaction log — minimal source impact, e.g., Debezium + Kafka), or timestamp/version column based. CDC enables near-real-time data warehousing, event-driven architectures, and avoids the cost of full-table reloads on billion-row tables.",
            "hints": json.dumps(["If only 0.1% of rows change each day, reloading the entire billion-row table every night is wasteful. What's the alternative?"]),
            "tags": json.dumps(["etl", "cdc", "data-engineering"]),
        },
        # ========== SCHEMAS (12: 7 medium, 5 hard) ==========
        {
            "id": "q066",
            "category": "Data Modeling",
            "topic": "schemas",
            "difficulty": "medium",
            "prompt": "How does a snowflake schema differ structurally from a star schema?",
            "choices": json.dumps([
                "Snowflake schemas have no fact tables",
                "Dimension tables in a snowflake schema are normalized into multiple related tables, while a star schema keeps each dimension in a single denormalized table",
                "Star schemas use foreign keys; snowflake schemas do not",
                "Snowflake schemas only work in cloud databases"
            ]),
            "correct_answer": "Dimension tables in a snowflake schema are normalized into multiple related tables, while a star schema keeps each dimension in a single denormalized table",
            "explanation": "A star schema has a central fact table surrounded by a single layer of denormalized dimension tables (like a star). A snowflake schema normalizes dimension tables further — e.g., Product → Category → Department — creating a branching, snowflake-like structure. Snowflake schemas save storage but require more joins, which can slow queries.",
            "hints": json.dumps(["Draw a star: one center, single-layer spokes. Draw a snowflake: branching off the branches."]),
            "tags": json.dumps(["data-modeling", "schemas", "star-schema", "snowflake-schema"]),
        },
        {
            "id": "q067",
            "category": "Data Modeling",
            "topic": "schemas",
            "difficulty": "medium",
            "prompt": "What does the 'grain' of a fact table define?",
            "choices": json.dumps([
                "The physical storage size of each fact row",
                "The level of detail each row represents — e.g., one row per transaction, per order line, or per day",
                "The number of dimension tables connected to the fact table",
                "How quickly the fact table grows over time"
            ]),
            "correct_answer": "The level of detail each row represents — e.g., one row per transaction, per order line, or per day",
            "explanation": "The grain is the most fundamental design decision for a fact table. It answers: 'What does one row in this table mean?' Common grains: transactional (one row per sale), line-item (one row per order line), periodic snapshot (one row per account per month), accumulating snapshot (one row per process, updated as milestones complete). All dimensions must match the grain.",
            "hints": json.dumps(["Ask yourself: 'What single event or measurement does each row represent?'"]),
            "tags": json.dumps(["data-modeling", "schemas", "fact-table", "grain"]),
        },
        {
            "id": "q068",
            "category": "Data Modeling",
            "topic": "schemas",
            "difficulty": "medium",
            "prompt": "What is a degenerate dimension?",
            "choices": json.dumps([
                "A dimension that has been accidentally deleted",
                "A dimensional attribute stored directly in the fact table without a separate dimension table — typically an identifier like an invoice number or transaction ID",
                "A dimension table that contains only one column",
                "A dimension that slowly degrades over time"
            ]),
            "correct_answer": "A dimensional attribute stored directly in the fact table without a separate dimension table — typically an identifier like an invoice number or transaction ID",
            "explanation": "A degenerate dimension is a dimension key that lives in the fact table with no corresponding dimension table. Common examples: invoice number, order number, transaction ID, POS receipt number. These identifiers are useful for grouping or tracing but have no additional attributes worth modeling as a full dimension — so they stay in the fact table as a degenerate dimension.",
            "hints": json.dumps(["Think of an order number: it's in the fact table, but does it need its own dimension with attributes? What else would you store about an order number?"]),
            "tags": json.dumps(["data-modeling", "schemas", "degenerate-dimension"]),
        },
        {
            "id": "q069",
            "category": "Data Modeling",
            "topic": "schemas",
            "difficulty": "medium",
            "prompt": "What is a junk dimension used for?",
            "choices": json.dumps([
                "Storing obsolete dimension data that should be deleted",
                "Combining multiple low-cardinality flags and indicators (like is_new_customer, payment_method, has_discount) into a single dimension table instead of cluttering the fact table",
                "A dimension table that has no relationship to any fact table",
                "A table for storing malformed or 'junk' data that failed validation"
            ]),
            "correct_answer": "Combining multiple low-cardinality flags and indicators (like is_new_customer, payment_method, has_discount) into a single dimension table instead of cluttering the fact table",
            "explanation": "A junk dimension consolidates many small, unrelated flags and categories that are too small to warrant their own dimension tables. Instead of 15 flag columns in the fact table, you create a junk dimension with all combinations of those flags that actually exist, then store a single foreign key in the fact table. This keeps the fact table narrow and manageable.",
            "hints": json.dumps(["If you have 10 boolean flags on your fact table, how many columns is that? Is there a more compact way?"]),
            "tags": json.dumps(["data-modeling", "schemas", "junk-dimension"]),
        },
        {
            "id": "q070",
            "category": "Data Modeling",
            "topic": "schemas",
            "difficulty": "hard",
            "prompt": "Why are conformed dimensions essential in a Kimball-style data warehouse with multiple data marts?",
            "choices": json.dumps([
                "They reduce storage costs by sharing dimension tables across servers",
                "They ensure the same dimension means the same thing across all data marts, enabling cross-mart queries — a conformed dimension is defined once and used consistently everywhere",
                "They are required for GDPR compliance",
                "Conformed dimensions are automatically indexed"
            ]),
            "correct_answer": "They ensure the same dimension means the same thing across all data marts, enabling cross-mart queries — a conformed dimension is defined once and used consistently everywhere",
            "explanation": "A conformed dimension is a dimension that has the same meaning, key structure, and content across multiple fact tables and data marts. Example: a 'Date' dimension or 'Customer' dimension used identically in sales, inventory, and support marts. This enables 'drill-across' queries where you combine facts from different marts by joining on the shared conformed dimension. Without conformed dimensions, each mart is a silo.",
            "hints": json.dumps(["If 'Customer ID' means different things in sales vs support, can you answer: 'Show support tickets alongside orders for the same customer'?"]),
            "tags": json.dumps(["data-modeling", "schemas", "conformed-dimensions", "kimball"]),
        },
        {
            "id": "q071",
            "category": "Data Modeling",
            "topic": "schemas",
            "difficulty": "hard",
            "prompt": "What is a role-playing dimension?",
            "choices": json.dumps([
                "A dimension table that changes its schema dynamically at query time",
                "A single physical dimension table referenced multiple times in the same fact table through different foreign keys, each playing a different role — like a Date dimension used as order_date, ship_date, and delivery_date",
                "A dimension that impersonates another dimension for security testing",
                "A dimension table used only in staging environments"
            ]),
            "correct_answer": "A single physical dimension table referenced multiple times in the same fact table through different foreign keys, each playing a different role — like a Date dimension used as order_date, ship_date, and delivery_date",
            "explanation": "Role-playing dimensions avoid duplicating dimension tables. A single Date dimension (dim_date) can be joined to the fact table three times with different aliases: JOIN dim_date AS order_date_dim ON fact.order_date_key = order_date_dim.date_key, then again as ship_date_dim, then as delivery_date_dim. Each 'role' is a separate logical view of the same physical table, typically surfaced through views in the presentation layer.",
            "hints": json.dumps(["How many date columns might an orders fact table have? Do you want a separate date dimension table for each?"]),
            "tags": json.dumps(["data-modeling", "schemas", "role-playing-dimension"]),
        },
        {
            "id": "q072",
            "category": "Data Modeling",
            "topic": "schemas",
            "difficulty": "medium",
            "prompt": "What is a factless fact table and when would you use one?",
            "choices": json.dumps([
                "A fact table that has been emptied by a DELETE operation",
                "A fact table with no measurable numeric facts — it captures events or conditions like student attendance, product eligibility, or coverage; the 'fact' is simply that something occurred",
                "A dimension table mistakenly designed as a fact table",
                "A fact table that only stores NULL values"
            ]),
            "correct_answer": "A fact table with no measurable numeric facts — it captures events or conditions like student attendance, product eligibility, or coverage; the 'fact' is simply that something occurred",
            "explanation": "Factless fact tables contain only dimension keys with no additive measures. Common use cases: tracking events (student attended class — the fact is presence), coverage/eligibility (which products are available in which stores), or conditions (which promotions apply to which items). The 'fact' is the relationship itself. COUNT(*) becomes the implicit measure — 'how many students attended?'",
            "hints": json.dumps(["If you want to know 'which products were promoted in which stores' and you only record the combination, what measurable value do you store?"]),
            "tags": json.dumps(["data-modeling", "schemas", "factless-fact-table"]),
        },
        {
            "id": "q073",
            "category": "Data Modeling",
            "topic": "schemas",
            "difficulty": "hard",
            "prompt": "How should a data warehouse handle late-arriving dimensions?",
            "choices": json.dumps([
                "Reject the fact row — the dimension data must arrive first",
                "Insert the fact row with a placeholder/surrogate key pointing to an 'unknown' dimension row, then update the fact row (or re-process) when the dimension data arrives later",
                "Delete all fact data and reload from scratch",
                "Store the fact in a separate 'pending' table permanently"
            ]),
            "correct_answer": "Insert the fact row with a placeholder/surrogate key pointing to an 'unknown' dimension row, then update the fact row (or re-process) when the dimension data arrives later",
            "explanation": "Late-arriving dimensions occur when fact events arrive before their associated dimension attributes. Example: a sales transaction references a new customer ID, but the customer master data arrives a day later. Standard approach: the fact row references a pre-created 'Unknown' or 'Late Arriving' dimension row (surrogate key -1 or 0). When the real dimension data arrives, either update the fact row's foreign key or re-process that partition of the fact table.",
            "hints": json.dumps(["You can't hold up the entire pipeline for one new customer. You need a placeholder. What happens when the real data arrives?"]),
            "tags": json.dumps(["data-modeling", "schemas", "late-arriving-dimension", "etl"]),
        },
        {
            "id": "q074",
            "category": "Data Modeling",
            "topic": "schemas",
            "difficulty": "hard",
            "prompt": "When do you need a bridge table (or factless fact table) to model a many-to-many relationship between a dimension and a fact table?",
            "choices": json.dumps([
                "All relationships in a star schema should use bridge tables",
                "When a fact row can be associated with multiple instances of a dimension — e.g., a bank transaction having multiple account holders, or a patient visit involving multiple diagnoses",
                "Bridge tables are required for any dimension with more than 1 million rows",
                "Only when using a snowflake schema"
            ]),
            "correct_answer": "When a fact row can be associated with multiple instances of a dimension — e.g., a bank transaction having multiple account holders, or a patient visit involving multiple diagnoses",
            "explanation": "Standard star schemas assume 1:M between dimension and fact — each fact row references one dimension row. When the relationship is truly M:M (a bank transaction splits across multiple customers), you need a bridge table between fact and dimension. The bridge contains the fact grain + dimension key combinations, with a weighting/allocation factor to distribute the fact's measures across the dimension members for reporting.",
            "hints": json.dumps(["If one transaction splits between two customers, can a single foreign key in the fact table represent that?"]),
            "tags": json.dumps(["data-modeling", "schemas", "bridge-table", "many-to-many"]),
        },
        {
            "id": "q075",
            "category": "Data Modeling",
            "topic": "schemas",
            "difficulty": "medium",
            "prompt": "What is a mini-dimension and why is it used?",
            "choices": json.dumps([
                "A dimension table with fewer than 100 rows",
                "A separate dimension that offloads rapidly changing attributes from a large, slowly changing dimension — e.g., moving customer demographics to a mini-dimension while keeping the core customer dimension small",
                "A dimension table stored entirely in memory",
                "A temporary dimension created for ad-hoc queries"
            ]),
            "correct_answer": "A separate dimension that offloads rapidly changing attributes from a large, slowly changing dimension — e.g., moving customer demographics to a mini-dimension while keeping the core customer dimension small",
            "explanation": "When a large customer dimension (millions of rows) has attributes that change frequently (income bracket, number of children, credit score tier), using SCD Type 2 would cause the dimension to explode in size. Instead, extract those volatile attributes into a separate 'mini-dimension' with far fewer rows (just the unique combinations), and reference it from the fact table alongside the main customer dimension key. This is also called an outrigger or profile dimension.",
            "hints": json.dumps(["If your customer dimension has 10M rows and income bracket changes often, how big does a Type 2 SCD become? Can you separate the volatile part?"]),
            "tags": json.dumps(["data-modeling", "schemas", "mini-dimension", "scd"]),
        },
        {
            "id": "q076",
            "category": "Data Modeling",
            "topic": "schemas",
            "difficulty": "hard",
            "prompt": "What does a Type 6 slowly changing dimension (SCD6) combine?",
            "choices": json.dumps([
                "SCD1 + SCD2: it keeps the current value in one column (overwrite) AND tracks history in another column via new rows with effective dates",
                "SCD2 + SCD3: it tracks full history with new rows AND stores both the current and previous values as separate columns on each row",
                "All six SCD types applied to the same dimension simultaneously",
                "SCD1 only, applied six times"
            ]),
            "correct_answer": "SCD2 + SCD3: it tracks full history with new rows AND stores both the current and previous values as separate columns on each row",
            "explanation": "SCD Type 6 is a hybrid: it inserts a new row for each change (like Type 2) AND includes both the current value and the previous/current historical value as columns on each row (like Type 3). This gives you full history (Type 2) plus the ability to see 'what was this attribute before/after this change' on a single row (Type 3). It's more complex to maintain but delivers both historical tracking and convenient before/after analysis.",
            "hints": json.dumps(["1 = overwrite, 2 = new row, 3 = previous value column. Combine 2 + 3 = 5, but the convention calls it Type 6."]),
            "tags": json.dumps(["data-modeling", "schemas", "scd", "type-6"]),
        },
        {
            "id": "q077",
            "category": "Data Modeling",
            "topic": "schemas",
            "difficulty": "hard",
            "prompt": "What is the purpose of aggregate fact tables (summary tables) in a dimensional model?",
            "choices": json.dumps([
                "They replace the original fact table entirely",
                "They pre-compute common aggregations at a coarser grain for query performance — e.g., rolling daily transaction data up to monthly summary rows, trading storage for speed",
                "They store raw, unaggregated data for auditing",
                "Aggregate fact tables are only used in OLTP systems"
            ]),
            "correct_answer": "They pre-compute common aggregations at a coarser grain for query performance — e.g., rolling daily transaction data up to monthly summary rows, trading storage for speed",
            "explanation": "Aggregate fact tables store pre-computed summaries at a higher grain than the base fact table. For example, a transactional fact at 'invoice line' grain might have an aggregate sibling at 'product by month' grain: SUM(sales), COUNT(transactions) pre-computed. When a dashboard queries monthly sales by product, the query hits the small aggregate table instead of scanning billions of transactional rows. This is a form of denormalization — the aggregate is logically redundant but dramatically faster for common query patterns.",
            "hints": json.dumps(["If a dashboard always shows monthly totals, should every query scan every transaction? Or should you pre-compute?"]),
            "tags": json.dumps(["data-modeling", "schemas", "aggregate-tables", "performance"]),
        },

        # ========== JOINS (10: 6 medium, 4 hard) ==========
        {
            "id": "q078",
            "category": "SQL Basics",
            "topic": "joins",
            "difficulty": "medium",
            "prompt": "What is a semi-join and how is it typically expressed in SQL?",
            "choices": json.dumps([
                "A join that returns half the columns from each table",
                "A join that returns rows from table A where a matching row exists in table B, without returning any columns from B — typically expressed via EXISTS or IN (SELECT ...)",
                "A join using only the first half of a composite key",
                "A join that automatically splits data into partitions"
            ]),
            "correct_answer": "A join that returns rows from table A where a matching row exists in table B, without returning any columns from B — typically expressed via EXISTS or IN (SELECT ...)",
            "explanation": "A semi-join checks for existence: 'give me customers who have placed orders' without returning order data. In SQL, it's written as WHERE EXISTS (SELECT 1 FROM orders WHERE orders.cust_id = customers.id) or WHERE id IN (SELECT cust_id FROM orders). Most databases recognize this pattern and apply a semi-join optimization internally. An anti-join is the opposite: rows from A where nothing matches in B.",
            "hints": json.dumps(["Think 'filter, don't duplicate.' A regular join can multiply rows if multiple matches exist. A semi-join never adds rows."]),
            "tags": json.dumps(["sql", "joins", "semi-join", "exists"]),
        },
        {
            "id": "q079",
            "category": "SQL Basics",
            "topic": "joins",
            "difficulty": "medium",
            "prompt": "What is an anti-join and how is it typically expressed in SQL?",
            "choices": json.dumps([
                "A join that reverses the column order of both tables",
                "A join that returns rows from table A where NO matching row exists in table B — typically expressed via NOT EXISTS or NOT IN (with careful NULL handling)",
                "A join that produces negative row counts",
                "A LEFT JOIN without an ON clause"
            ]),
            "correct_answer": "A join that returns rows from table A where NO matching row exists in table B — typically expressed via NOT EXISTS or NOT IN (with careful NULL handling)",
            "explanation": "An anti-join answers 'give me customers who have NOT placed any orders.' It returns only rows from A with no match in B. SQL patterns: NOT EXISTS (safest), NOT IN (dangerous if the subquery contains NULLs — a single NULL makes the entire NOT IN return zero rows), or LEFT JOIN ... WHERE b.id IS NULL (explicit and commonly used). Always prefer NOT EXISTS or LEFT JOIN/IS NULL over NOT IN to avoid NULL-related bugs.",
            "hints": json.dumps(["What's the opposite of 'find customers WITH orders'? Now think about NULLs in NOT IN."]),
            "tags": json.dumps(["sql", "joins", "anti-join", "not-exists"]),
        },
        {
            "id": "q080",
            "category": "SQL Basics",
            "topic": "joins",
            "difficulty": "medium",
            "prompt": "What is the difference between ON and USING in a JOIN clause?",
            "choices": json.dumps([
                "ON is for INNER JOINs; USING is for OUTER JOINs",
                "ON specifies arbitrary join conditions; USING (col) is a shorthand when both tables have identically named join columns — and USING coalesces the duplicate columns into one in the output",
                "USING is faster than ON in all cases",
                "ON can reference only one column; USING can reference multiple"
            ]),
            "correct_answer": "ON specifies arbitrary join conditions; USING (col) is a shorthand when both tables have identically named join columns — and USING coalesces the duplicate columns into one in the output",
            "explanation": "USING (dept_id) is equivalent to ON a.dept_id = b.dept_id but with two key differences: (1) the join column appears only once in SELECT * (the USING column is coalesced), and (2) you can reference the coalesced column without table qualification (dept_id instead of a.dept_id). USING requires identically named columns in both tables. ON is more flexible — it supports any boolean condition, including inequalities and composite conditions.",
            "hints": json.dumps(["Compare SELECT * FROM a JOIN b USING (x) vs SELECT * FROM a JOIN b ON a.x = b.x — how many 'x' columns in each?"]),
            "tags": json.dumps(["sql", "joins", "syntax"]),
        },
        {
            "id": "q081",
            "category": "SQL Basics",
            "topic": "joins",
            "difficulty": "medium",
            "prompt": "Why is the explicit JOIN ... ON syntax preferred over the old comma-style implicit join syntax (FROM a, b WHERE a.id = b.id)?",
            "choices": json.dumps([
                "The implicit syntax is slower — it generates different execution plans",
                "Explicit JOIN syntax separates join conditions from filter conditions, makes outer joins possible (comma-style can't express LEFT JOIN), and prevents accidental cross joins when a WHERE clause is forgotten",
                "Comma-style joins are deprecated and will be removed from SQL",
                "There is no difference — it's purely a matter of style"
            ]),
            "correct_answer": "Explicit JOIN syntax separates join conditions from filter conditions, makes outer joins possible (comma-style can't express LEFT JOIN), and prevents accidental cross joins when a WHERE clause is forgotten",
            "explanation": "Explicit JOIN syntax (introduced in SQL-92) keeps join logic in ON clauses and filter logic in WHERE. This makes queries more readable and maintainable. Critically, the comma-style FROM a, b LEFT JOIN c produces ambiguous results because the LEFT JOIN binds more tightly. Explicit syntax also forces you to state your intent: INNER, LEFT, CROSS — making accidental cross joins less likely. Modern SQL style guides universally prefer explicit JOINs.",
            "hints": json.dumps(["What happens if you forget the WHERE clause in a comma-style join? And can you write a LEFT JOIN with comma syntax?"]),
            "tags": json.dumps(["sql", "joins", "syntax", "best-practices"]),
        },
        {
            "id": "q082",
            "category": "SQL Basics",
            "topic": "joins",
            "difficulty": "hard",
            "prompt": "What are the risks of using NATURAL JOIN?",
            "choices": json.dumps([
                "NATURAL JOIN is slower than explicit JOIN",
                "NATURAL JOIN automatically matches on ALL identically named columns — if someone adds a column with the same name to both tables later (like 'comment' or 'created_at'), the join silently changes behavior or breaks, potentially returning incorrect results",
                "NATURAL JOIN does not support indexes",
                "NATURAL JOIN can only join two tables at a time"
            ]),
            "correct_answer": "NATURAL JOIN automatically matches on ALL identically named columns — if someone adds a column with the same name to both tables later (like 'comment' or 'created_at'), the join silently changes behavior or breaks, potentially returning incorrect results",
            "explanation": "NATURAL JOIN is fragile: it matches on every column with the same name in both tables. Today you have NATURAL JOIN on 'id' — tomorrow someone adds 'created_at' to both tables, and suddenly the join condition includes both id AND created_at, silently returning wrong results. It's also implicit — readers can't tell what columns are being joined without inspecting the schema. Most teams ban NATURAL JOIN in production code in favor of explicit ON or USING clauses.",
            "hints": json.dumps(["If you don't list the join columns, and a colleague adds a column with the same name to both tables, what happens to your query?"]),
            "tags": json.dumps(["sql", "joins", "natural-join", "pitfalls"]),
        },
        {
            "id": "q083",
            "category": "SQL Basics",
            "topic": "joins",
            "difficulty": "hard",
            "prompt": "What is a non-equi join and what problem does it solve?",
            "choices": json.dumps([
                "A join that returns unequal row counts from each table",
                "A join using inequality operators (>, <, >=, BETWEEN) instead of = — useful for range matching, date overlap detection, and cumulative comparisons",
                "A join between tables with different numbers of columns",
                "An anti-join with additional filtering"
            ]),
            "correct_answer": "A join using inequality operators (>, <, >=, BETWEEN) instead of = — useful for range matching, date overlap detection, and cumulative comparisons",
            "explanation": "Non-equi joins use conditions like ON a.date BETWEEN b.start_date AND b.end_date or ON a.salary < b.department_avg. Common uses: matching events to date ranges, finding overlapping time intervals (scheduling/booking conflicts), cumulative distributions (for each employee, count coworkers with lower salary), and price-band lookups. They can't use hash joins (hash joins only support =), so they typically use nested loop or merge joins — be mindful of performance on large tables.",
            "hints": json.dumps(["Not all joins are 'equals.' What if you need to find which price tier a value falls into: WHERE value BETWEEN min AND max?"]),
            "tags": json.dumps(["sql", "joins", "non-equi-join"]),
        },
        {
            "id": "q084",
            "category": "SQL Basics",
            "topic": "joins",
            "difficulty": "medium",
            "prompt": "Does a CROSS JOIN followed by a WHERE filter produce the same result as an INNER JOIN with the equivalent ON condition?",
            "choices": json.dumps([
                "No — CROSS JOIN always produces more rows",
                "Yes — logically they are equivalent and most query planners will generate the same execution plan for both",
                "No — CROSS JOIN cannot be filtered",
                "Yes, but only in PostgreSQL"
            ]),
            "correct_answer": "Yes — logically they are equivalent and most query planners will generate the same execution plan for both",
            "explanation": "Logically, SELECT * FROM a CROSS JOIN b WHERE a.id = b.id produces the same result as SELECT * FROM a INNER JOIN b ON a.id = b.id. Modern query planners don't literally build the full Cartesian product then filter — they recognize the pattern and use the same join algorithm. However, explicit INNER JOIN is FAR better for readability and intent — a reader shouldn't have to scan the WHERE clause to understand how tables are related.",
            "hints": json.dumps(["Mathematically: CROSS JOIN produces all pairs, then WHERE keeps matching ones. That's exactly what INNER JOIN does. But which is clearer?"]),
            "tags": json.dumps(["sql", "joins", "cross-join", "optimization"]),
        },
        {
            "id": "q085",
            "category": "SQL Basics",
            "topic": "joins",
            "difficulty": "hard",
            "prompt": "Why does join order matter for query performance even though SQL is declarative?",
            "choices": json.dumps([
                "Join order doesn't matter — the query planner always finds the optimal order",
                "The query planner chooses join order based on statistics, but with many joins the search space grows factorially — the planner uses heuristics and may not find the optimal order, especially with stale statistics or complex predicates",
                "SQL forces a specific join order based on the FROM clause",
                "Join order only matters in MySQL"
            ]),
            "correct_answer": "The query planner chooses join order based on statistics, but with many joins the search space grows factorially — the planner uses heuristics and may not find the optimal order, especially with stale statistics or complex predicates",
            "explanation": "With N tables, there are N! possible join orders — 10 tables = 3.6 million possibilities. Optimizers use dynamic programming and heuristics (GEQO in PostgreSQL for 12+ tables). But outdated statistics, skewed data, or complex predicates can lead the planner to pick a suboptimal order. A common mistake: joining large tables before filtering smaller ones increases intermediate row counts. Understanding this helps you restructure queries, use CTEs, or (as a last resort) apply join hints.",
            "hints": json.dumps(["If you join 5 large tables, there are 120 possible orders. Does the planner always pick the best one? What if statistics are stale?"]),
            "tags": json.dumps(["sql", "joins", "optimization", "join-order"]),
        },
        {
            "id": "q086",
            "category": "SQL Basics",
            "topic": "joins",
            "difficulty": "hard",
            "prompt": "What is join elimination and under what conditions can the query planner remove a join entirely?",
            "choices": json.dumps([
                "Join elimination removes any join that references fewer than 1000 rows",
                "The planner can remove a JOIN if the query doesn't reference any columns from that table AND the join won't change the row count (e.g., a foreign key join where every fact row has exactly one matching dimension row)",
                "Join elimination is a manual process — the planner never does it automatically",
                "Only LEFT JOINs can be eliminated"
            ]),
            "correct_answer": "The planner can remove a JOIN if the query doesn't reference any columns from that table AND the join won't change the row count (e.g., a foreign key join where every fact row has exactly one matching dimension row)",
            "explanation": "Join elimination occurs when the optimizer proves the join is semantically unnecessary: (1) no columns from the joined table appear in SELECT, WHERE, or ORDER BY; (2) the join is guaranteed not to duplicate or remove rows. This works best with foreign key relationships — if you JOIN to a dimension on its primary key but select nothing from it, the planner may eliminate the join because the FK constraint guarantees exactly one match per row. This is why selecting unnecessary joins still has a cost — the planner might not always be able to eliminate them, especially without proper constraints.",
            "hints": json.dumps(["If you join a table but never look at any of its columns, does the join actually need to happen?"]),
            "tags": json.dumps(["sql", "joins", "optimization", "join-elimination"]),
        },
        {
            "id": "q087",
            "category": "SQL Basics",
            "topic": "joins",
            "difficulty": "medium",
            "prompt": "When joining on multiple columns (composite join), what happens if one of the join columns is NULL?",
            "choices": json.dumps([
                "The join succeeds and matches only NULL with NULL",
                "The join fails with an error because NULLs can't be compared",
                "NULL = NULL evaluates to NULL (not TRUE), so rows with NULL in any join column will never match — they fall out of an INNER JOIN and become NULL-padded rows in an OUTER JOIN",
                "Only the non-NULL columns are used for matching"
            ]),
            "correct_answer": "NULL = NULL evaluates to NULL (not TRUE), so rows with NULL in any join column will never match — they fall out of an INNER JOIN and become NULL-padded rows in an OUTER JOIN",
            "explanation": "In SQL, NULL = anything (including NULL = NULL) returns NULL, which is not TRUE. So if your composite join is ON a.x = b.x AND a.y = b.y, and either x OR y is NULL on either side, that row pair does not match. This is a common source of subtle bugs — rows disappear from results because a nullable join column has NULLs. Solutions: use IS NOT DISTINCT FROM (PostgreSQL), COALESCE to a sentinel, or ensure join columns are NOT NULL.",
            "hints": json.dumps(["NULL = NULL doesn't return TRUE. What does that mean for a join condition like ON a.col = b.col when both sides are NULL?"]),
            "tags": json.dumps(["sql", "joins", "null", "composite-join"]),
        },

        # ========== JOIN-ALGORITHMS (5: 3 medium, 2 hard) ==========
        {
            "id": "q088",
            "category": "Query Optimization",
            "topic": "join-algorithms",
            "difficulty": "medium",
            "prompt": "What prerequisite must both inputs satisfy for a merge join to be used?",
            "choices": json.dumps([
                "Both tables must have the same number of rows",
                "Both inputs must be sorted on the join key — either because of an index or an explicit sort operation",
                "Both tables must fit entirely in memory",
                "Merge joins require both tables to be partitioned identically"
            ]),
            "correct_answer": "Both inputs must be sorted on the join key — either because of an index or an explicit sort operation",
            "explanation": "A merge join works like merging two sorted lists: it walks through both inputs simultaneously, advancing whichever side has the smaller current key. If both inputs are already sorted (via B-tree indexes on the join columns), the merge join requires no additional sorting — this is very efficient. If one or both inputs must be sorted first, the planner weighs the sort cost against hash join or nested loop alternatives. Merge joins excel for large, pre-sorted data and range-join conditions.",
            "hints": json.dumps(["Think of merging two alphabetized lists of names. If one list isn't sorted, can you still merge them efficiently?"]),
            "tags": json.dumps(["sql", "optimization", "join-algorithms", "merge-join"]),
        },
        {
            "id": "q089",
            "category": "Query Optimization",
            "topic": "join-algorithms",
            "difficulty": "hard",
            "prompt": "What happens when a hash join's hash table doesn't fit in the allocated memory (work_mem)?",
            "choices": json.dumps([
                "The query fails with an out-of-memory error",
                "The hash join 'spills' to disk: it partitions the data into batches that fit in memory, processing one batch at a time — dramatically slower but the query still completes",
                "The planner automatically switches to a nested loop join",
                "The database requests more memory from the operating system without limit"
            ]),
            "correct_answer": "The hash join 'spills' to disk: it partitions the data into batches that fit in memory, processing one batch at a time — dramatically slower but the query still completes",
            "explanation": "When the hash table exceeds work_mem (PostgreSQL) or equivalent settings, the hash join uses 'grace hash join' or 'hybrid hash join': it partitions both inputs into N batches using a hash function. It then processes one batch at a time — building the hash table for batch 1 of the inner, probing with batch 1 of the outer, writing the rest to temp files. Multiple passes over the same data can be very I/O heavy. Increasing work_mem can dramatically speed up large hash joins by avoiding spilling.",
            "hints": json.dumps(["Can you store 10 GB of hash table data in 256 MB of memory? What has to happen to the excess?"]),
            "tags": json.dumps(["sql", "optimization", "join-algorithms", "hash-join", "memory"]),
        },
        {
            "id": "q090",
            "category": "Query Optimization",
            "topic": "join-algorithms",
            "difficulty": "medium",
            "prompt": "How does an index nested loop join differ from a basic nested loop join?",
            "choices": json.dumps([
                "Index nested loops use an index on the inner table's join column to look up matching rows in O(log n) instead of scanning the entire inner table for each outer row",
                "Index nested loops skip every other row for faster processing",
                "They are the same — 'index' just means it's faster",
                "Index nested loops only work with primary keys"
            ]),
            "correct_answer": "Index nested loops use an index on the inner table's join column to look up matching rows in O(log n) instead of scanning the entire inner table for each outer row",
            "explanation": "A basic nested loop scans the entire inner table for every outer row — O(n×m), disastrous on large tables. With an index on the inner table's join column, each outer row triggers an index lookup (typically O(log n) for a B-tree), making the join O(n × log m). This is great when: the outer set is small (OLTP queries), and there's an index on the inner join key. Without an index, the planner will avoid nested loops on large tables.",
            "hints": json.dumps(["For each customer (outer), you need to find their orders (inner). What makes that lookup fast? An index on orders.customer_id."]),
            "tags": json.dumps(["sql", "optimization", "join-algorithms", "nested-loop", "index"]),
        },
        {
            "id": "q091",
            "category": "Query Optimization",
            "topic": "join-algorithms",
            "difficulty": "hard",
            "prompt": "What is an adaptive join and how does it differ from a traditional static join strategy?",
            "choices": json.dumps([
                "An adaptive join uses machine learning to predict join conditions",
                "An adaptive join starts with one strategy and can switch to another mid-execution based on observed row counts — e.g., starting as a hash join but switching to nested loops if the actual row count is much smaller than estimated",
                "Adaptive joins automatically create indexes before joining",
                "Adaptive joins only work in distributed databases"
            ]),
            "correct_answer": "An adaptive join starts with one strategy and can switch to another mid-execution based on observed row counts — e.g., starting as a hash join but switching to nested loops if the actual row count is much smaller than estimated",
            "explanation": "Traditional query planning is static: the planner picks a join strategy based on statistics, and if the estimates are wrong, performance suffers. Adaptive joins (SQL Server 2017+, Oracle 12c+ adaptive plans) defer the final join strategy decision until execution time. The engine starts buffering the build input for a hash join, but if it sees far fewer rows than expected, it can switch to a nested loop. This helps when statistics are stale or when parameter sniffing would mislead the static planner.",
            "hints": json.dumps(["Static plan = decide everything before reading any data. Adaptive = start executing, observe real row counts, adjust strategy mid-query."]),
            "tags": json.dumps(["sql", "optimization", "join-algorithms", "adaptive-join"]),
        },
        {
            "id": "q092",
            "category": "Query Optimization",
            "topic": "join-algorithms",
            "difficulty": "medium",
            "prompt": "What is a block nested loop join and when is it used?",
            "choices": json.dumps([
                "A join that processes data in blockchain order",
                "A nested loop variant that reads the outer table in blocks (multiple rows at once) instead of row-by-row, reducing the number of full inner-table scans — used when the inner table has no index",
                "A join that only processes rows from specific database blocks",
                "A nested loop that skips over locked rows"
            ]),
            "correct_answer": "A nested loop variant that reads the outer table in blocks (multiple rows at once) instead of row-by-row, reducing the number of full inner-table scans — used when the inner table has no index",
            "explanation": "A naive nested loop: for each of N outer rows, scan M inner rows = N×M comparisons. Block nested loop: read a block of B outer rows at once, scan the inner table once for that block, comparing against all B outer rows simultaneously using an in-memory hash or search structure. This reduces the number of inner-table scans from N to N/B. It's used as a fallback when no index exists on the inner join column — better than row-by-row nested loop but still expensive on large tables.",
            "hints": json.dumps(["If you grab 100 outer rows at once, you only need to scan the inner table once for those 100. That's N/100 scans instead of N scans."]),
            "tags": json.dumps(["sql", "optimization", "join-algorithms", "block-nested-loop"]),
        },

        # ========== CTEs (10: 6 medium, 4 hard) ==========
        {
            "id": "q093",
            "category": "Query Design",
            "topic": "ctes",
            "difficulty": "medium",
            "prompt": "Can a single WITH clause define multiple CTEs, and can a later CTE reference an earlier one?",
            "choices": json.dumps([
                "No — each WITH clause can only define one CTE",
                "Yes — multiple CTEs are separated by commas, and each CTE can reference any CTE defined before it in the list",
                "Yes, but each CTE must be in a separate WITH clause",
                "Multiple CTEs are only supported in PostgreSQL"
            ]),
            "correct_answer": "Yes — multiple CTEs are separated by commas, and each CTE can reference any CTE defined before it in the list",
            "explanation": "Syntax: WITH cte1 AS (...), cte2 AS (SELECT ... FROM cte1 ...), cte3 AS (SELECT ... FROM cte2 ...) SELECT ... FROM cte3. Earlier CTEs are visible to later ones; later CTEs cannot be referenced by earlier ones. This is great for building multi-step transformations: each CTE handles one logical step, making the query easier to read and debug than deeply nested subqueries.",
            "hints": json.dumps(["Think of CTEs like variable assignments: each one can use everything defined above it."]),
            "tags": json.dumps(["sql", "ctes", "query-design"]),
        },
        {
            "id": "q094",
            "category": "Query Design",
            "topic": "ctes",
            "difficulty": "hard",
            "prompt": "How do you prevent infinite loops in a recursive CTE, and what happens if one occurs?",
            "choices": json.dumps([
                "Recursive CTEs cannot loop infinitely — the database detects cycles automatically",
                "You must include a termination condition in the recursive member (typically a WHERE clause that eventually excludes all rows), and most databases have a MAXRECURSION/cte_max_recursion_depth limit that throws an error when exceeded",
                "The database kills the query after 60 seconds automatically",
                "Infinite recursion is silently capped at 1000 rows"
            ]),
            "correct_answer": "You must include a termination condition in the recursive member (typically a WHERE clause that eventually excludes all rows), and most databases have a MAXRECURSION/cte_max_recursion_depth limit that throws an error when exceeded",
            "explanation": "A recursive CTE has: anchor (base case, non-recursive) UNION ALL recursive (references the CTE, must eventually return zero rows). The termination condition is implicit in the recursive member's logic — when no new rows are produced, recursion stops. For safety, SQL Server defaults to 100 max recursions (configurable with OPTION MAXRECURSION), PostgreSQL has max_recursion_depth (default 200 or unlimited). If the recursion exceeds the limit, the query errors. Always test recursive CTEs with a LIMIT or level counter during development.",
            "hints": json.dumps(["Think of it like a while loop: you need a condition that eventually becomes false. What's the SQL equivalent of a loop counter?"]),
            "tags": json.dumps(["sql", "ctes", "recursive-ctes", "safety"]),
        },
        {
            "id": "q095",
            "category": "Query Design",
            "topic": "ctes",
            "difficulty": "medium",
            "prompt": "Can CTEs be used in INSERT, UPDATE, or DELETE statements?",
            "choices": json.dumps([
                "No — CTEs are read-only and can only be used with SELECT",
                "Yes — you can define CTEs at the start of DML statements, allowing complex data transformations before inserting, updating, or deleting",
                "CTEs work with INSERT but not UPDATE or DELETE",
                "Only in PostgreSQL"
            ]),
            "correct_answer": "Yes — you can define CTEs at the start of DML statements, allowing complex data transformations before inserting, updating, or deleting",
            "explanation": "WITH cte AS (SELECT ... ) INSERT INTO target SELECT * FROM cte works in most modern databases. PostgreSQL goes further with writable CTEs: WITH deleted AS (DELETE FROM old WHERE ... RETURNING *) INSERT INTO archive SELECT * FROM deleted — multiple DML operations chained in one statement, all-or-nothing. This is powerful for archiving, upsert patterns, and multi-step data mutations in a single atomic transaction.",
            "hints": json.dumps(["Can you prep a SELECT result and immediately feed it into an INSERT in one statement? WITH ... INSERT ... SELECT."]),
            "tags": json.dumps(["sql", "ctes", "dml", "query-design"]),
        },
        {
            "id": "q096",
            "category": "Query Design",
            "topic": "ctes",
            "difficulty": "hard",
            "prompt": "How would you use a recursive CTE to find all descendants (children, grandchildren, etc.) of a given node in an adjacency-list hierarchy?",
            "choices": json.dumps([
                "You can't — recursion requires a nested set model",
                "The anchor selects the starting node; the recursive member JOINs back to the CTE on parent_id = cte.id, accumulating all descendants",
                "Use a window function with PARTITION BY parent_id",
                "A simple self-join with INNER JOIN handles arbitrary depth"
            ]),
            "correct_answer": "The anchor selects the starting node; the recursive member JOINs back to the CTE on parent_id = cte.id, accumulating all descendants",
            "explanation": "Pattern: WITH RECURSIVE descendants AS (SELECT * FROM nodes WHERE id = :start_id UNION ALL SELECT n.* FROM nodes n JOIN descendants d ON n.parent_id = d.id) SELECT * FROM descendants. The anchor grabs the root; each recursion adds direct children of rows found in the previous step. This handles arbitrary depth. Add a depth counter column (depth + 1) and a cycle detection column to handle graphs with cycles. Self-joins only handle a fixed number of levels.",
            "hints": json.dumps(["Start at the root (anchor), then for each found node, find its children. Repeat until no new children appear."]),
            "tags": json.dumps(["sql", "ctes", "recursive-ctes", "hierarchy"]),
        },
        {
            "id": "q097",
            "category": "Query Design",
            "topic": "ctes",
            "difficulty": "medium",
            "prompt": "When multiple CTEs are chained (each building on the previous), how does the query planner handle them?",
            "choices": json.dumps([
                "Each CTE is always materialized separately as a temporary table",
                "In most modern databases, chained CTEs are inlined — the planner sees through the entire chain and optimizes it as a single query, potentially merging or reordering operations",
                "Chained CTEs are executed in strict order with no optimization across CTE boundaries",
                "Chained CTEs are automatically parallelized across different CPU cores"
            ]),
            "correct_answer": "In most modern databases, chained CTEs are inlined — the planner sees through the entire chain and optimizes it as a single query, potentially merging or reordering operations",
            "explanation": "Unless MATERIALIZED is explicitly specified (or the DB defaults to materialization), CTEs are inlined — the planner sees the full query tree and can push predicates down, merge CTEs, or eliminate unnecessary steps. This means chained CTEs don't force intermediate materialization; they're primarily for code organization. However, if a CTE is referenced multiple times in the final query, materialization may be chosen to avoid recomputing it.",
            "hints": json.dumps(["If CTE A filters, CTE B aggregates, and CTE C re-filters, could the planner push C's filter all the way into A?"]),
            "tags": json.dumps(["sql", "ctes", "optimization", "inlining"]),
        },
        {
            "id": "q098",
            "category": "Query Design",
            "topic": "ctes",
            "difficulty": "hard",
            "prompt": "When should you use a CTE versus a temporary table for a complex multi-step query?",
            "choices": json.dumps([
                "CTEs are always better — temp tables are obsolete",
                "Use a CTE for readability and when the intermediate result is referenced once or twice; use a temp table when the intermediate result is large and referenced many times, benefits from its own indexes, or needs statistics for the planner",
                "Temp tables are always faster than CTEs",
                "The choice doesn't matter — they perform identically"
            ]),
            "correct_answer": "Use a CTE for readability and when the intermediate result is referenced once or twice; use a temp table when the intermediate result is large and referenced many times, benefits from its own indexes, or needs statistics for the planner",
            "explanation": "CTEs are ephemeral — they exist only for the query's duration, don't have their own statistics, and (unless materialized) are inlined. They're ideal for breaking down complex logic. Temp tables are physical: you can CREATE INDEX on them, they have statistics for the planner, and they persist across multiple queries within a session. The downside: temp tables have write overhead (logging, I/O). Use temp tables when: the intermediate result is large (millions of rows), referenced 3+ times, or needs indexes for efficient joining downstream.",
            "hints": json.dumps(["CTE = short-lived, no stats, no indexes. Temp table = you pay to write it, but you get stats and can index it. Which matters for your use case?"]),
            "tags": json.dumps(["sql", "ctes", "temporary-tables", "performance"]),
        },
        {
            "id": "q099",
            "category": "Query Design",
            "topic": "ctes",
            "difficulty": "medium",
            "prompt": "How can a CTE help simplify a query that needs to find the latest row per group (e.g., most recent order per customer)?",
            "choices": json.dumps([
                "CTEs can't help with 'latest per group' queries",
                "Use a CTE to first calculate ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC), then filter WHERE rn = 1 in the outer query — separating the window function from the filter",
                "Use a recursive CTE that loops through each customer",
                "CTEs automatically detect and return the latest row per group"
            ]),
            "correct_answer": "Use a CTE to first calculate ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC), then filter WHERE rn = 1 in the outer query — separating the window function from the filter",
            "explanation": "Window functions can't be referenced directly in WHERE (due to logical processing order). The standard pattern: WITH ranked AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC) AS rn FROM orders) SELECT * FROM ranked WHERE rn = 1. The CTE provides a clean way to calculate the ranking first, then filter on it. This pattern works for deduplication, top-N-per-group, and 'latest snapshot' queries.",
            "hints": json.dumps(["ROW_NUMBER() can't go in WHERE. So where do you calculate it, and where do you filter on it?"]),
            "tags": json.dumps(["sql", "ctes", "window-functions", "deduplication"]),
        },
        {
            "id": "q100",
            "category": "Query Design",
            "topic": "ctes",
            "difficulty": "hard",
            "prompt": "How can a recursive CTE generate a date series or number sequence without a pre-existing numbers table?",
            "choices": json.dumps([
                "Recursive CTEs cannot generate data — they can only query existing tables",
                "The anchor provides the starting value; the recursive member adds 1 (or 1 day) and UNION ALL accumulates until a WHERE condition stops recursion",
                "Use a CROSS JOIN between two existing tables",
                "Only generate_series() functions can create sequences"
            ]),
            "correct_answer": "The anchor provides the starting value; the recursive member adds 1 (or 1 day) and UNION ALL accumulates until a WHERE condition stops recursion",
            "explanation": "Pattern: WITH RECURSIVE numbers(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM numbers WHERE n < 100). For dates: WITH RECURSIVE dates(d) AS (SELECT '2024-01-01'::date UNION ALL SELECT d + 1 FROM dates WHERE d < '2024-12-31'). The anchor gives the first value, the recursive step generates the next, and the WHERE clause ensures termination. This is useful for filling gaps in sparse data (generating a date spine) or when generate_series isn't available. Warning: large ranges are slow compared to built-in generators.",
            "hints": json.dumps(["Start at 1. Then 'current value + 1' until you hit the max. SQL can do this with a self-referencing CTE."]),
            "tags": json.dumps(["sql", "ctes", "recursive-ctes", "series-generation"]),
        },
        {
            "id": "q101",
            "category": "Query Design",
            "topic": "ctes",
            "difficulty": "hard",
            "prompt": "How do you track the path from root to each node in a recursive CTE tree traversal?",
            "choices": json.dumps([
                "You can't — recursive CTEs only return the current level",
                "Maintain a path column: start with the root's name/id in the anchor, and concatenate the child's name/id with a separator in each recursive step — e.g., path || '/' || child.name",
                "Use a separate window function to compute the path after the recursion",
                "Paths are automatically tracked by the RECURSIVE keyword"
            ]),
            "correct_answer": "Maintain a path column: start with the root's name/id in the anchor, and concatenate the child's name/id with a separator in each recursive step — e.g., path || '/' || child.name",
            "explanation": "Pattern: WITH RECURSIVE tree AS (SELECT id, name, parent_id, name::text AS path, 1 AS depth FROM categories WHERE parent_id IS NULL UNION ALL SELECT c.id, c.name, c.parent_id, t.path || ' → ' || c.name, t.depth + 1 FROM categories c JOIN tree t ON c.parent_id = t.id) SELECT * FROM tree ORDER BY path. This builds a breadcrumb trail from root to each node. For cycle detection, also track an array of visited IDs and check that the next node's ID isn't already in the path array.",
            "hints": json.dumps(["You're building a path step by step. The anchor has the root path. Each recursion appends one more segment."]),
            "tags": json.dumps(["sql", "ctes", "recursive-ctes", "path-tracking"]),
        },
        {
            "id": "q102",
            "category": "Query Design",
            "topic": "ctes",
            "difficulty": "medium",
            "prompt": "What is the primary readability benefit of using CTEs over deeply nested subqueries for multi-step transformations?",
            "choices": json.dumps([
                "CTEs are always shorter than subqueries",
                "CTEs allow you to name intermediate results and read the query top-to-bottom in logical order, whereas nested subqueries force you to read inside-out",
                "CTEs require fewer characters to type",
                "There is no readability difference — it's purely a preference"
            ]),
            "correct_answer": "CTEs allow you to name intermediate results and read the query top-to-bottom in logical order, whereas nested subqueries force you to read inside-out",
            "explanation": "With nested subqueries, the innermost query executes first, forcing a reader to start from the deepest nesting level and work outward. CTEs define steps in execution order: first step at the top, each subsequent step builds on previous ones, final SELECT at the bottom. Named CTEs also serve as documentation — WITH active_customers AS (...) is more self-describing than an anonymous subquery. This is the single strongest argument for CTEs, even when they're functionally identical to subqueries.",
            "hints": json.dumps(["Which is easier to follow: reading top-to-bottom (CTEs), or reading from the deepest nesting level outward (subqueries)?"]),
            "tags": json.dumps(["sql", "ctes", "query-design", "readability"]),
        },

        {
            "id": "q065",
            "category": "ETL Concepts",
            "topic": "data-lineage",
            "difficulty": "hard",
            "prompt": "Why is data lineage important in a data pipeline with dozens of transformations?",
            "choices": json.dumps([
                "It makes queries run faster",
                "It lets you trace any field in a report back to its source system and transformations, enabling impact analysis, debugging, and regulatory compliance",
                "Data lineage is only needed for machine learning models",
                "It automatically fixes data quality issues"
            ]),
            "correct_answer": "It lets you trace any field in a report back to its source system and transformations, enabling impact analysis, debugging, and regulatory compliance",
            "explanation": "Data lineage tracks data from origin to destination — every transformation, join, filter, and aggregation. When a report shows a suspicious number, lineage lets you trace backwards to find where it went wrong. For GDPR/CCPA: lineage identifies which source tables feed into PII-bearing columns. Tools: dbt docs (column-level lineage), OpenLineage, data catalogs (Alation, Collibra), and cloud-native tools (Dataplex, Glue).",
            "hints": json.dumps(["If the CFO's revenue dashboard shows 2x the expected number, how do you find where the error came from without lineage?"]),
            "tags": json.dumps(["etl", "data-lineage", "data-governance"]),
        },
    ]

    conn.executemany("""
        INSERT OR IGNORE INTO questions
            (id, category, topic, difficulty, type, prompt, choices, correct_answer, explanation, hints, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        (q["id"], q["category"], q["topic"], q["difficulty"], "multiple_choice",
         q["prompt"], q["choices"], q["correct_answer"], q["explanation"],
         q.get("hints", "[]"), q.get("tags", "[]"))
        for q in questions
    ])

    conn.commit()
    conn.close()
    print(f"Seeded {len(questions)} questions.")


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
