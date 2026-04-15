import os
import sys
import uuid
import threading
import tempfile
import subprocess
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

API_KEY = os.environ.get("TASKRUNNER_API_KEY", "")
PORT = int(os.environ.get("TASKRUNNER_PORT", "3200"))
TIMEOUT = int(os.environ.get("TASK_TIMEOUT", "600"))
ALLOWED_IPS = [ip.strip() for ip in os.environ.get("ALLOWED_IPS", "").split(",") if ip.strip()]

tasks: dict[str, dict] = {}
lock = threading.Lock()


def execute_task(task_id: str):
    with lock:
        task = tasks[task_id]
        task["status"] = "running"

    print(f"\n{'='*50}")
    print(f"[TASK {task_id[:8]}] Started")
    print(f"{'='*50}")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(task["script"])
        tmp = f.name

    stdout_lines = []
    stderr_lines = []
    try:
        proc = subprocess.Popen(
            [sys.executable, "-u", tmp],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )

        def read_stream(stream, buf, prefix):
            for line in stream:
                buf.append(line)
                print(f"  [{task_id[:8]}] {prefix} {line}", end="")

        t_out = threading.Thread(target=read_stream, args=(proc.stdout, stdout_lines, "│"))
        t_err = threading.Thread(target=read_stream, args=(proc.stderr, stderr_lines, "ERR│"))
        t_out.start()
        t_err.start()

        proc.wait(timeout=TIMEOUT)
        t_out.join()
        t_err.join()
        code = proc.returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout_lines.append("")
        stderr_lines.append(f"Timeout ({TIMEOUT}s)")
        code = 1
    except Exception as e:
        stderr_lines.append(str(e))
        code = 1
    finally:
        os.unlink(tmp)

    stdout = "".join(stdout_lines)
    stderr = "".join(stderr_lines)
    status = "done" if code == 0 else "failed"

    print(f"[TASK {task_id[:8]}] {status.upper()} (exit {code})")
    print(f"{'='*50}\n")

    with lock:
        tasks[task_id].update(
            status=status,
            stdout=stdout[-10000:],
            stderr=stderr[-10000:],
            exitCode=code,
            finishedAt=datetime.utcnow().isoformat() + "Z",
        )


class Handler(BaseHTTPRequestHandler):
    def _auth(self):
        if ALLOWED_IPS and self.client_address[0] not in ALLOWED_IPS:
            self._respond(403, {"error": "Forbidden"})
            return False
        if self.headers.get("x-api-key") != API_KEY:
            self._respond(401, {"error": "Unauthorized"})
            return False
        return True

    def _respond(self, code, data):
        body = json.dumps(data, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def do_POST(self):
        if not self._auth():
            return
        if self.path == "/tasks":
            body = self._read_body()
            script = body.get("script")
            if not script:
                return self._respond(400, {"error": "script required"})
            task_id = str(uuid.uuid4())
            task = {
                "id": task_id,
                "script": script,
                "status": "pending",
                "stdout": "",
                "stderr": "",
                "exitCode": None,
                "createdAt": datetime.utcnow().isoformat() + "Z",
                "finishedAt": None,
            }
            with lock:
                tasks[task_id] = task
            threading.Thread(target=execute_task, args=(task_id,), daemon=True).start()
            self._respond(201, task)
        else:
            self._respond(404, {"error": "Not found"})

    def do_GET(self):
        if not self._auth():
            return
        if self.path == "/tasks":
            with lock:
                result = sorted(tasks.values(), key=lambda t: t["createdAt"], reverse=True)[:50]
            self._respond(200, result)
        elif self.path.startswith("/tasks/"):
            task_id = self.path.split("/tasks/")[1]
            with lock:
                task = tasks.get(task_id)
            if not task:
                return self._respond(404, {"error": "Not found"})
            self._respond(200, task)
        elif self.path == "/health":
            self._respond(200, {"status": "ok"})
        else:
            self._respond(404, {"error": "Not found"})

    def log_message(self, fmt, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {self.client_address[0]} {args[0]}")


import socket

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "unknown"

def main():
    if not API_KEY:
        print("Set TASKRUNNER_API_KEY env var")
        sys.exit(1)
    local_ip = get_local_ip()
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"AiRelay listening on http://0.0.0.0:{PORT}")
    print(f"Local IP: {local_ip} — use http://{local_ip}:{PORT} from other machines")
    server.serve_forever()


if __name__ == "__main__":
    main()
