import os
import sys
import uuid
import socket
import threading
import tempfile
import subprocess
import logging
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from store import MemoryStore

# Logging setup
LOG_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(LOG_DIR, "airelay.log")
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("airelay")

API_KEY = os.environ.get("TASKRUNNER_API_KEY", "")
PORT = int(os.environ.get("TASKRUNNER_PORT", "3200"))
TIMEOUT = int(os.environ.get("TASK_TIMEOUT", "600"))
ALLOWED_IPS = [ip.strip() for ip in os.environ.get("ALLOWED_IPS", "").split(",") if ip.strip()]
VERSION = "0.4.0"

store = MemoryStore()


def execute_task(task_id: str):
    store.update(task_id, {"status": "running"})
    task = store.get(task_id)

    log.info(f"{'='*50}")
    log.info(f"[TASK {task_id[:8]}] Started")
    log.info(f"{'='*50}")

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
                log.info(f"  [{task_id[:8]}] {prefix} {line.rstrip()}")

        t_out = threading.Thread(target=read_stream, args=(proc.stdout, stdout_lines, "|"))
        t_err = threading.Thread(target=read_stream, args=(proc.stderr, stderr_lines, "ERR|"))
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

    status = "done" if code == 0 else "failed"
    store.update(task_id, {
        "status": status,
        "stdout": "".join(stdout_lines)[-10000:],
        "stderr": "".join(stderr_lines)[-10000:],
        "exitCode": code,
        "finishedAt": datetime.utcnow().isoformat() + "Z",
    })

    log.info(f"[TASK {task_id[:8]}] {status.upper()} (exit {code})")
    log.info(f"{'='*50}")


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
            task = store.create({
                "id": task_id,
                "script": script,
                "status": "pending",
                "stdout": "",
                "stderr": "",
                "exitCode": None,
                "createdAt": datetime.utcnow().isoformat() + "Z",
                "finishedAt": None,
            })
            threading.Thread(target=execute_task, args=(task_id,), daemon=True).start()
            self._respond(201, task)
        elif self.path == "/update":
            self._do_update()
        else:
            self._respond(404, {"error": "Not found"})

    def _do_update(self):
        server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        r = subprocess.run(["git", "-C", server_dir, "pull"], capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return self._respond(500, {"error": r.stderr.strip()})
        self._respond(200, {"message": r.stdout.strip(), "restarting": True})
        threading.Thread(target=self._restart, daemon=True).start()

    @staticmethod
    def _restart():
        import time
        time.sleep(1)
        log.info("Restarting...")
        os.execv(sys.executable, [sys.executable] + sys.argv)

    def do_GET(self):
        if not self._auth():
            return
        if self.path == "/tasks":
            self._respond(200, store.list())
        elif self.path.startswith("/tasks/"):
            task_id = self.path.split("/tasks/")[1]
            task = store.get(task_id)
            if not task:
                return self._respond(404, {"error": "Not found"})
            self._respond(200, task)
        elif self.path == "/health":
            self._respond(200, {"status": "ok", "version": VERSION})
        else:
            self._respond(404, {"error": "Not found"})

    def log_message(self, fmt, *args):
        log.info(f"{self.client_address[0]} {args[0]}")


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
        log.error("Set TASKRUNNER_API_KEY env var")
        sys.exit(1)
    local_ip = get_local_ip()
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    log.info(f"AiRelay v{VERSION} listening on http://0.0.0.0:{PORT}")
    log.info(f"Local IP: {local_ip} — use http://{local_ip}:{PORT} from other machines")
    log.info(f"Log file: {LOG_FILE}")
    server.serve_forever()


if __name__ == "__main__":
    main()
