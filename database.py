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
