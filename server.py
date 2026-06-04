import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

import database

PORT = 8420
FRONTEND_DIR = Path(__file__).parent / "frontend"

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}

class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, path):
        file_path = FRONTEND_DIR / path
        if not file_path.is_file() or not file_path.resolve().is_relative_to(FRONTEND_DIR.resolve()):
            self.send_error(404)
            return
        ext = file_path.suffix
        content_type = MIME_TYPES.get(ext, "application/octet-stream")
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def _parse_qs(self):
        parsed = urllib.parse.urlparse(self.path)
        return dict(urllib.parse.parse_qs(parsed.query))

    # ── Routing ────────────────────────────────────────────────

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        # Static files
        if path == "/" or path == "/index.html":
            self._send_static("index.html")
        elif path.startswith("/frontend/"):
            self._send_static(path[len("/frontend/"):])
        elif path == "/style.css" or path == "/app.js":
            self._send_static(path.lstrip("/"))

        # API
        elif path == "/api/questions":
            params = self._parse_qs()
            qs = database.get_questions(
                category=params.get("category", [None])[0],
                topic=params.get("topic", [None])[0],
                difficulty=params.get("difficulty", [None])[0],
                question_type=params.get("type", [None])[0],
            )
            self._send_json(qs)

        elif path.startswith("/api/questions/"):
            question_id = path.split("/api/questions/")[1]
            q = database.get_question(question_id)
            if q:
                self._send_json(q)
            else:
                self._send_json({"error": "not found"}, 404)

        elif path.startswith("/api/code/questions/"):
            question_id = path.split("/api/code/questions/")[1]
            q = database.get_question(question_id)
            if not q:
                self._send_json({"error": "not found"}, 404)
                return
            dataset = database.get_dataset(q.get("dataset_reference", "")) if q.get("dataset_reference") else None
            q["dataset_schema"] = dataset["ddl"] if dataset else None
            q["dataset_description"] = dataset["description"] if dataset else None
            self._send_json(q)

        elif path == "/api/progress/stats":
            self._send_json(database.get_stats())

        elif path == "/api/progress/weak-topics":
            threshold = int(self._parse_qs().get("threshold", [60])[0])
            self._send_json(database.get_weak_topics(threshold))

        elif path == "/api/topics":
            questions = database.get_questions()
            topics = sorted(set(q["topic"] for q in questions))
            categories = sorted(set(q["category"] for q in questions))
            self._send_json({"topics": topics, "categories": categories})

        else:
            self.send_error(404)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path

        if path == "/api/progress":
            data = self._read_body()
            database.save_progress(
                question_id=data["question_id"],
                correct=data["correct"],
                user_answer=data["user_answer"],
                response_time_ms=data.get("response_time_ms"),
                confidence=data.get("confidence"),
            )
            self._send_json({"status": "ok"}, 201)

        elif path == "/api/code/execute":
            data = self._read_body()
            question = database.get_question(data.get("question_id", ""))
            if not question:
                self._send_json({"error": "question not found"}, 404)
                return
            dataset_name = question.get("dataset_reference")
            if not dataset_name:
                self._send_json({"error": "question has no dataset"}, 400)
                return
            result = database.execute_query(dataset_name, data.get("query", ""))
            self._send_json(result, 200 if "error" not in result else 400)

        elif path == "/api/code/submit":
            data = self._read_body()
            question = database.get_question(data.get("question_id", ""))
            if not question:
                self._send_json({"error": "question not found"}, 404)
                return
            dataset_name = question.get("dataset_reference")
            if not dataset_name:
                self._send_json({"error": "question has no dataset"}, 400)
                return

            result = database.validate_query(
                dataset_name,
                data.get("query", ""),
                question["correct_answer"],
            )

            # Save progress — reuse existing function
            database.save_progress(
                question_id=data["question_id"],
                correct=1 if result.get("match") else 0,
                user_answer=data.get("query", ""),
            )

            self._send_json(result)

        else:
            self.send_error(404)


def main():
    database.init_db()
    server = ReusableHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Serving on http://0.0.0.0:{PORT}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server gracefully...")
    finally:
        server.server_close()
        print("Server stopped.")


if __name__ == "__main__":
    main()
