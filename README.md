<div align="center">

# 🛰️ AiRelay

**Let AI control any PC you own.**

Submit Python scripts to remote machines via HTTP. One process, zero dependencies, cross-platform.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/ProgramIsFun/airelay/pulls)

[Getting Started](#-getting-started) · [Dashboard](#-dashboard) · [API Reference](#-api-reference) · [Multi-PC Setup](#-multi-pc-setup) · [How It Works](#-how-it-works)

</div>

---

## ✨ Features

- 🚀 **Single file, zero config** — one Python script, no database, no Docker
- 🖥️ **Cross-platform** — runs on Windows, macOS, and Linux
- 🌐 **Web dashboard** — real-time task monitoring with system stats
- 🔄 **Self-updating** — pull latest code and restart with one API call
- 📝 **Task persistence** — history survives restarts via JSON storage
- 🔒 **API key auth** — optional IP whitelist for extra security
- ⚡ **Parallel execution** — tasks run in separate processes, server stays responsive
- 🛑 **Kill switch** — terminate running tasks via API or dashboard

## 🚀 Getting Started

### 1. Clone

```bash
git clone https://github.com/ProgramIsFun/airelay.git
cd airelay/worker
```

### 2. (Optional) Install psutil for system stats

```bash
pip install psutil
```

### 3. Run

```bash
# Linux / macOS
export TASKRUNNER_API_KEY=your-secret-key
python3 airelay.py

# Windows
set TASKRUNNER_API_KEY=your-secret-key
python airelay.py
```

```
AiRelay v0.9.0 listening on http://0.0.0.0:3200
Local IP: 192.168.1.10 — use http://192.168.1.10:3200 from other machines
Log file: /path/to/airelay.log
```

### 4. Submit a task

```bash
curl -X POST http://localhost:3200/tasks \
  -H "x-api-key: your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"script": "print(\"Hello from AiRelay!\")"}'
```

## 📊 Dashboard

Open `http://<your-ip>:3200` in a browser to access the web dashboard.

- **System specs** — CPU, RAM, disk usage (requires psutil)
- **Task sections** — Running, Pending, Failed, Completed
- **Live updates** — auto-refreshes every 3 seconds
- **Kill button** — stop running tasks from the browser
- **Script viewer** — click "script" to see the submitted code

## 📡 API Reference

All endpoints except `GET /` and `GET /about` require the `x-api-key` header.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Web dashboard (no auth) |
| `GET` | `/about` | Human-readable API description (no auth) |
| `GET` | `/health` | System specs, version, running task count |
| `POST` | `/tasks` | Submit a task: `{ "script": "<python code>" }` |
| `GET` | `/tasks` | List recent tasks (newest first, max 50) |
| `GET` | `/tasks/:id` | Get task with result |
| `DELETE` | `/tasks/:id` | Kill a running task |
| `POST` | `/update` | Self-update: git pull + restart |

### Task Object

```json
{
  "id": "uuid",
  "script": "print('hello')",
  "status": "done",
  "stdout": "hello\n",
  "stderr": "",
  "exitCode": 0,
  "createdAt": "2026-04-15T09:00:00.000Z",
  "finishedAt": "2026-04-15T09:00:01.000Z"
}
```

**Status values:** `pending` → `running` → `done` | `failed`

## 🌍 Multi-PC Setup

Run the same script on each machine. Talk to each one by IP:

```
Gaming PC:    http://192.168.1.10:3200
Mac Mini:     http://192.168.1.11:3200
Home Server:  http://192.168.1.12:3200
```

Use the same `TASKRUNNER_API_KEY` across all machines. Each PC operates independently — no central server needed.

## ⚙️ Configuration

All configuration via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `TASKRUNNER_API_KEY` | *(required)* | Secret key for API authentication |
| `TASKRUNNER_PORT` | `3200` | Port to listen on |
| `TASK_TIMEOUT` | `600` | Max task runtime in seconds |
| `ALLOWED_IPS` | *(empty)* | Comma-separated IP whitelist (e.g. `192.168.1.5,192.168.1.6`) |

## 🔄 Self-Update

Push changes to the repo, then:

```bash
curl -X POST http://<host>:3200/update -H "x-api-key: <key>"
```

The server pulls the latest code and restarts automatically. No SSH needed.

## 🏗️ How It Works

```
┌──────────┐         HTTP          ┌──────────────┐
│ AI Agent │ ───────────────────▶  │   AiRelay    │
│ (Kiro)   │ ◀─────────────────── │  (Python)    │
└──────────┘    task result        │              │
                                   │  ┌────────┐  │
                                   │  │ Task 1 │  │  ← separate process
                                   │  └────────┘  │
                                   │  ┌────────┐  │
                                   │  │ Task 2 │  │  ← separate process
                                   │  └────────┘  │
                                   └──────────────┘
```

1. AI submits a Python script via `POST /tasks`
2. AiRelay spawns a subprocess to execute it
3. stdout/stderr stream live to console + log file
4. AI polls `GET /tasks/:id` for the result
5. Task history persists to `tasks.json`

## 🔒 Security

- **API key** — all mutating endpoints require authentication
- **IP whitelist** — optionally restrict to specific source IPs
- **No inbound ports needed on controller** — workers connect outbound only
- **Process isolation** — each task runs in its own Python process

> ⚠️ AiRelay executes arbitrary Python code by design. Only run it on trusted networks with a strong API key.

## 🗺️ Roadmap

- [ ] MCP server integration for native AI tool support
- [ ] MongoDB storage backend
- [ ] Task scheduling (cron-like)
- [ ] File upload/download between machines
- [ ] Task dependencies and chaining
- [ ] Multi-machine task broadcasting

## 📄 License

[MIT](LICENSE) — use it however you want.

---

<div align="center">
  <sub>Built for humans who let AI do the heavy lifting.</sub>
</div>
