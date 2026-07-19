"""Task CRUD routes with per-user isolation, pagination and status filter."""

import json
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..ai_parser import parse_task
from ..config import settings
from ..deps import get_current_user, get_db
from ..models import Task, User
from ..schemas import (
    AIParseRequest,
    AIParseResponse,
    DayCount,
    TaskCreate,
    TaskOut,
    TaskPage,
    TaskStats,
    TaskStatus,
    TaskUpdate,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _as_utc(dt: datetime) -> datetime:
    """Treat naive datetimes from SQLite DATETIME columns as UTC."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _get_owned_task(task_id: int, db: Session, user: User) -> Task:
    """Fetch a task by id and enforce ownership."""
    task = db.get(Task, task_id)
    if task is None or task.owner_id != user.id:
        # Return 404 (not 403) to avoid leaking the existence of other users' tasks.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    return task


@router.get("", response_model=TaskPage)
def list_tasks(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskPage:
    stmt = select(Task).where(Task.owner_id == current_user.id)
    count_stmt = (
        select(func.count()).select_from(Task).where(Task.owner_id == current_user.id)
    )
    if status_filter is not None:
        stmt = stmt.where(Task.status == status_filter.value)
        count_stmt = count_stmt.where(Task.status == status_filter.value)

    total = db.scalar(count_stmt) or 0
    items = db.scalars(
        stmt.order_by(Task.created_at.desc(), Task.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return TaskPage(
        items=[TaskOut.model_validate(t) for t in items],
        total=total,
        page=page,
        size=size,
    )


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Task:
    task = Task(
        title=payload.title,
        description=payload.description,
        status=payload.status.value,
        due_date=payload.due_date,
        completed_at=(
            datetime.now(timezone.utc)
            if payload.status == TaskStatus.done
            else None
        ),
        owner_id=current_user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


# ---------- AI task parsing ----------

_AI_SYSTEM_PROMPT = (
    "You extract a task from a short user sentence (Chinese or English). "
    "Today is {today}. Reply with ONLY a JSON object, no markdown: "
    '{{"title": string, "description": string, '
    '"due_date": "YYYY-MM-DD" or null}}. '
    "title is the short task name, description may add context or be empty, "
    "due_date is the resolved calendar date or null when none is mentioned."
)


def _parse_with_ai(text: str) -> AIParseResponse | None:
    """Call an OpenAI-compatible chat API; return None on any failure."""
    if not settings.AI_API_KEY:
        return None
    payload = {
        "model": settings.AI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": _AI_SYSTEM_PROMPT.format(
                    today=datetime.now().date().isoformat()
                ),
            },
            {"role": "user", "content": text},
        ],
        "temperature": 0,
    }
    try:
        resp = httpx.post(
            f"{settings.AI_BASE_URL.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.AI_API_KEY}"},
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        # Tolerate models wrapping the JSON in markdown code fences.
        content = content.strip().removeprefix("```json").removeprefix("```")
        content = content.removesuffix("```").strip()
        data = json.loads(content)
        title = str(data["title"]).strip()
        if not title:
            return None
        raw_due = data.get("due_date")
        due_date = (
            datetime.fromisoformat(str(raw_due).strip()) if raw_due else None
        )
        return AIParseResponse(
            title=title[:200],
            description=str(data.get("description") or ""),
            due_date=due_date,
            source="ai",
        )
    except Exception:
        # Timeout, network error, bad JSON, unexpected shape -> fall back.
        return None


@router.post("/ai-parse", response_model=AIParseResponse)
def ai_parse_task(
    payload: AIParseRequest,
    current_user: User = Depends(get_current_user),
) -> AIParseResponse:
    """Parse a natural-language sentence into a structured task.

    Uses the configured AI provider when available, otherwise falls back to
    the built-in rule-based parser (and also on any AI failure).
    """
    result = _parse_with_ai(payload.text)
    if result is not None:
        return result
    parsed = parse_task(payload.text, datetime.now())
    return AIParseResponse(
        title=parsed.title[:200],
        description=parsed.description,
        due_date=parsed.due_date,
        source="fallback",
    )


@router.get("/stats", response_model=TaskStats)
def task_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskStats:
    """Aggregate statistics over the current user's tasks."""
    tasks = db.scalars(select(Task).where(Task.owner_id == current_user.id)).all()

    total = len(tasks)
    by_status = {s.value: 0 for s in TaskStatus}
    for task in tasks:
        if task.status in by_status:
            by_status[task.status] += 1

    now = datetime.now(timezone.utc)
    overdue = sum(
        1
        for task in tasks
        if task.due_date is not None
        and task.status != TaskStatus.done.value
        and _as_utc(task.due_date) < now
    )

    # Daily completion counts for the last 7 calendar days, oldest first;
    # days without completions stay at 0 so trend charts get a full series.
    today = now.date()
    days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
    per_day = dict.fromkeys(days, 0)
    for task in tasks:
        if task.completed_at is not None:
            day = _as_utc(task.completed_at).date()
            if day in per_day:
                per_day[day] += 1

    return TaskStats(
        total=total,
        by_status=by_status,
        completion_rate=by_status["done"] / total if total else 0.0,
        overdue=overdue,
        completed_last_7_days=[
            DayCount(date=day.isoformat(), count=per_day[day]) for day in days
        ],
    )


@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Task:
    return _get_owned_task(task_id, db, current_user)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Task:
    task = _get_owned_task(task_id, db, current_user)
    update_data = payload.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"] is not None:
        new_status = update_data["status"].value
        update_data["status"] = new_status
        # Track completion time: stamp when entering "done", clear when leaving.
        if new_status == TaskStatus.done.value and task.status != TaskStatus.done.value:
            update_data["completed_at"] = datetime.now(timezone.utc)
        elif new_status != TaskStatus.done.value and task.status == TaskStatus.done.value:
            update_data["completed_at"] = None
    for field, value in update_data.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    task = _get_owned_task(task_id, db, current_user)
    db.delete(task)
    db.commit()
