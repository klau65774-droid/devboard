"""Task CRUD routes with per-user isolation, pagination and status filter."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import Task, User
from ..schemas import TaskCreate, TaskOut, TaskPage, TaskStatus, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


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
        owner_id=current_user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


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
        update_data["status"] = update_data["status"].value
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
