"""Pydantic v2 request/response schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


# ---------- Auth ----------

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Tasks ----------

class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    status: TaskStatus = TaskStatus.todo
    due_date: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: TaskStatus | None = None
    due_date: datetime | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: TaskStatus
    owner_id: int
    due_date: datetime | None
    completed_at: datetime | None
    created_at: datetime


class TaskPage(BaseModel):
    """Paginated list of tasks."""

    items: list[TaskOut]
    total: int
    page: int
    size: int


# ---------- AI task parsing ----------

class AIParseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)


class AIParseResponse(BaseModel):
    title: str
    description: str
    due_date: datetime | None
    source: str  # "ai" or "fallback"


# ---------- Stats ----------

class DayCount(BaseModel):
    """Tasks completed on a single calendar day (ISO date)."""

    date: str
    count: int


class TaskStats(BaseModel):
    """Aggregate statistics for the current user's tasks."""

    total: int
    by_status: dict[str, int]
    completion_rate: float
    overdue: int
    completed_last_7_days: list[DayCount]
