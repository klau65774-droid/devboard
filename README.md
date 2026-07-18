# DevBoard

A full-stack task management platform — FastAPI + SQLAlchemy backend, React + TypeScript kanban frontend, with JWT auth, per-user data isolation, a full test suite, CI and Docker support.

一个小型全栈任务看板项目，用于演示分层架构、测试、CI/CD 与容器化等工程实践。

[![CI](https://github.com/klau65774-droid/devboard/actions/workflows/ci.yml/badge.svg)](https://github.com/klau65774-droid/devboard/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Features

- User registration & login with JWT access tokens
- Passwords hashed with PBKDF2-SHA256 (passlib)
- Task CRUD with statuses `todo` / `in_progress` / `done`
- Strict per-user isolation: users can only see and modify their own tasks
- Pagination and status filtering on the task list endpoint
- Three-column kanban board UI (React, no UI framework)
- Drag & drop cards between columns (native HTML5 DnD, optimistic update with rollback; click-to-move buttons as fallback)
- Landing page with hero and feature overview
- Interactive onboarding tour on the board (hand-rolled spotlight overlay, no dependencies)
- Interactive API docs via Swagger UI
- Pytest suite covering auth, CRUD, pagination and authorization boundaries
- GitHub Actions CI: backend tests + frontend typecheck/build
- Fully containerized with Docker and docker-compose

## Tech Stack

| Layer     | Technology                                                        |
| --------- | ----------------------------------------------------------------- |
| Backend   | FastAPI, SQLAlchemy 2.0, Pydantic v2, python-jose (JWT), passlib  |
| Frontend  | React 18, TypeScript, Vite, React Router                          |
| Database  | SQLite (swap `DATABASE_URL` for PostgreSQL in production)         |
| Testing   | pytest, FastAPI TestClient, `tsc --noEmit`                        |
| DevOps    | Docker, docker-compose, GitHub Actions                            |

## Architecture

```
React SPA (Vite)  --HTTP/JSON + Bearer JWT-->  FastAPI app
                                                    │
                    ┌───────────────────────────────┼─────────────────────┐
                    │ routers/  (HTTP layer: auth, tasks)                 │
                    │ deps.py   (dependency injection: DB session,        │
                    │            current user from JWT)                   │
                    │ schemas.py(Pydantic request/response validation)    │
                    │ security.py (password hashing, JWT encode/decode)   │
                    │ models.py / database.py (SQLAlchemy ORM + session)  │
                    └───────────────────────────────┬─────────────────────┘
                                                    │
                                                SQLite DB
```

The backend follows a layered style: routers only handle HTTP, dependencies handle
auth/session wiring, and SQLAlchemy models handle persistence. Every `/tasks`
endpoint is scoped to the authenticated user (`owner_id`), so cross-user access
returns `404`.

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- (optional) Docker + docker-compose

### Backend

```bash
cd backend
python -m venv .venv
# Windows (Git Bash):
source .venv/Scripts/activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

API runs at <http://localhost:8000>.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

UI runs at <http://localhost:5173>.

### Docker (everything at once)

```bash
docker compose up --build
```

- Frontend: <http://localhost>
- Backend: <http://localhost:8000>

## API Documentation

Once the backend is running, interactive docs are available at:

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

Main endpoints:

| Method   | Path             | Description                              |
| -------- | ---------------- | ---------------------------------------- |
| `POST`   | `/auth/register` | Create a user                            |
| `POST`   | `/auth/login`    | OAuth2 password login, returns JWT       |
| `GET`    | `/tasks`         | List own tasks (`page`, `size`, `status`)|
| `POST`   | `/tasks`         | Create a task                            |
| `GET`    | `/tasks/{id}`    | Get one of your tasks                    |
| `PATCH`  | `/tasks/{id}`    | Update title/description/status          |
| `DELETE` | `/tasks/{id}`    | Delete a task                            |

## Running Tests

```bash
cd backend
pytest -v            # backend test suite (SQLite in-memory)

cd frontend
npm run typecheck    # TypeScript strict type check
npm run build        # production build
```

## Configuration

Backend settings are read from environment variables (see `backend/app/config.py`):

| Variable            | Default                               | Notes                                   |
| ------------------- | ------------------------------------- | --------------------------------------- |
| `SECRET_KEY`        | dev-only placeholder                  | **Must be overridden in production**    |
| `DATABASE_URL`      | `sqlite:///./devboard.db`             | Any SQLAlchemy URL                      |
| `CORS_ORIGINS`      | `http://localhost:5173`               | Comma-separated allowed origins         |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440`                      | JWT lifetime                            |

The frontend reads `VITE_API_URL` (default `http://localhost:8000`).

## Project Structure

```
devboard/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI entry: routers + CORS
│   │   ├── config.py        # pydantic-settings configuration
│   │   ├── database.py      # SQLAlchemy engine/session
│   │   ├── models.py        # User, Task ORM models
│   │   ├── schemas.py       # Pydantic request/response models
│   │   ├── security.py      # JWT + password hashing
│   │   ├── deps.py          # Dependency injection
│   │   └── routers/         # auth, tasks
│   ├── tests/               # pytest suite
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api.ts           # fetch wrapper with JWT
│   │   ├── App.tsx          # routes + auth guard
│   │   └── pages/           # Login, Board (kanban)
│   ├── package.json
│   └── Dockerfile           # node build + nginx serve
├── .github/workflows/ci.yml # pytest + tsc build
├── docker-compose.yml
└── LICENSE                  # MIT
```

## License

[MIT](LICENSE)
