# AiRelay

AI-powered task relay — submit Python scripts to any PC you own via HTTP. Single process, zero dependencies.

## Setup

```bash
cd worker
pip install -r requirements.txt

export TASKRUNNER_API_KEY=<your-secret>
export TASKRUNNER_PORT=3200        # optional, default 3200
export TASK_TIMEOUT=600            # optional, default 600s

python airelay.py
```

## API

All requests require `x-api-key` header.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /tasks | Submit `{ "script": "print('hi')" }` — runs immediately |
| GET | /tasks | List recent tasks |
| GET | /tasks/:id | Get task + result (stdout, stderr, exitCode) |
| GET | /health | Health check |

## Multi-PC Setup

Run the same script on each PC. Talk to each one by IP:

```
PC 1:  http://192.168.1.10:3200
PC 2:  http://192.168.1.11:3200
```

Use the same API_KEY across all machines.
