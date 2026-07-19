import { DragEvent, FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  createTask,
  deleteTask,
  fetchTasks,
  parseTaskWithAI,
  setToken,
  updateTaskStatus,
} from "../api";
import type { Task, TaskStatus } from "../types";
import Tour, { TourStep } from "../components/Tour";

const COLUMNS: { key: TaskStatus; label: string }[] = [
  { key: "todo", label: "To Do" },
  { key: "in_progress", label: "In Progress" },
  { key: "done", label: "Done" },
];

// localStorage flag so the onboarding tour only auto-plays once.
const TOUR_KEY = "devboard_tour_seen";

// Due date shown on a card, e.g. "Due Jul 22". Rendered in red when the
// due day has fully passed and the task is not done yet (overdue highlight).
function DueDate({ task }: { task: Task }) {
  if (!task.due_date) return null;
  // Parse the ISO date ("2026-07-22" or "2026-07-22T00:00:00") as a local
  // calendar date to avoid UTC-offset day shifts.
  const [y, m, d] = task.due_date.slice(0, 10).split("-").map(Number);
  const due = new Date(y, m - 1, d, 23, 59, 59, 999);
  const overdue = task.status !== "done" && due.getTime() < Date.now();
  const label = due.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
  return (
    <p
      style={{
        margin: "4px 0",
        fontSize: 12,
        color: overdue ? "crimson" : "#6b7280",
      }}
    >
      Due {label}
    </p>
  );
}

const TOUR_STEPS: TourStep[] = [
  {
    selector: '[data-tour="new-task"]',
    title: "Create a task",
    description:
      "Type a title (and an optional description) here, then press Add to create your first task.",
  },
  {
    selector: '[data-tour="columns"]',
    title: "Drag & drop between columns",
    description:
      "Grab any card and drop it into To Do, In Progress or Done. The new status is saved automatically.",
  },
  {
    selector: '[data-tour="task-card"]',
    title: "Move or delete with buttons",
    description:
      "Prefer clicking? Every card has buttons to move it to another column or delete it entirely.",
  },
];

// Three-column kanban board. Cards can be moved between columns either by
// drag & drop (native HTML5 API, optimistic UI with rollback) or via the
// click-to-move buttons as a fallback.
export default function Board() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [error, setError] = useState("");
  // AI quick-create input state.
  const [aiText, setAiText] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState("");
  // Id of the card currently being dragged; used for the semi-transparent
  // dragging style.
  const [draggingId, setDraggingId] = useState<number | null>(null);
  // Column the dragged card is currently hovering over; used for highlight.
  const [dropTarget, setDropTarget] = useState<TaskStatus | null>(null);
  // Auto-play the onboarding tour on the first visit to the board.
  const [showTour, setShowTour] = useState(
    () => localStorage.getItem(TOUR_KEY) !== "1"
  );
  const navigate = useNavigate();

  function closeTour() {
    localStorage.setItem(TOUR_KEY, "1");
    setShowTour(false);
  }

  const load = useCallback(async () => {
    try {
      const page = await fetchTasks();
      setTasks(page.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load tasks");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    await createTask(title.trim(), description.trim(), dueDate || undefined);
    setTitle("");
    setDescription("");
    setDueDate("");
    await load();
  }

  // Parse one natural-language sentence via /tasks/ai-parse and create the
  // task directly from the parsed result (reusing the normal create flow).
  async function handleAiCreate(e: FormEvent) {
    e.preventDefault();
    const sentence = aiText.trim();
    if (!sentence || aiLoading) return;
    setAiLoading(true);
    setAiError("");
    try {
      const parsed = await parseTaskWithAI(sentence);
      if (!parsed.title) {
        throw new Error("Could not extract a task title");
      }
      // createTask expects a plain "YYYY-MM-DD" date string.
      const parsedDue = parsed.due_date
        ? parsed.due_date.slice(0, 10)
        : undefined;
      await createTask(parsed.title, parsed.description, parsedDue);
      setAiText("");
      await load();
    } catch (err) {
      setAiError(
        err instanceof Error ? err.message : "Failed to create task with AI"
      );
    } finally {
      setAiLoading(false);
    }
  }

  async function move(task: Task, status: TaskStatus) {
    await updateTaskStatus(task.id, status);
    await load();
  }

  async function remove(task: Task) {
    await deleteTask(task.id);
    await load();
  }

  function logout() {
    setToken(null);
    navigate("/login");
  }

  // ---------- Drag & drop ----------

  function handleDragStart(e: DragEvent<HTMLElement>, task: Task) {
    e.dataTransfer.setData("text/plain", String(task.id));
    e.dataTransfer.effectAllowed = "move";
    setDraggingId(task.id);
  }

  function handleDragEnd() {
    setDraggingId(null);
    setDropTarget(null);
  }

  function handleDragOver(e: DragEvent<HTMLElement>, status: TaskStatus) {
    // preventDefault is required to allow dropping here.
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setDropTarget(status);
  }

  async function handleDrop(e: DragEvent<HTMLElement>, status: TaskStatus) {
    e.preventDefault();
    setDropTarget(null);
    setDraggingId(null);

    const id = Number(e.dataTransfer.getData("text/plain"));
    const task = tasks.find((t) => t.id === id);
    if (!task || task.status === status) return;

    // Optimistic update: render the new status immediately...
    const previous = task.status;
    setTasks((prev) =>
      prev.map((t) => (t.id === id ? { ...t, status } : t))
    );
    setError("");
    try {
      await updateTaskStatus(id, status);
    } catch (err) {
      // ...and roll back if persistence fails.
      setTasks((prev) =>
        prev.map((t) => (t.id === id ? { ...t, status: previous } : t))
      );
      setError(
        err instanceof Error
          ? `Failed to move task: ${err.message}`
          : "Failed to move task"
      );
    }
  }

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: 24 }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <h1 style={{ fontSize: 22 }}>DevBoard</h1>
        <div style={{ display: "flex", gap: 8 }}>
          <Link to="/dashboard">
            <button>Dashboard</button>
          </Link>
          <button onClick={() => setShowTour(true)} title="Replay the tour">
            ? Tour
          </button>
          <button onClick={logout}>Log out</button>
        </div>
      </header>

      <form
        onSubmit={handleAiCreate}
        style={{
          display: "flex",
          gap: 8,
          margin: "16px 0 8px",
          padding: 10,
          background: "#eef2ff",
          border: "1px solid #c7d2fe",
          borderRadius: 8,
        }}
      >
        <input
          placeholder='✨ AI quick create — e.g. "下周三前把简历改完" or "finish report by Friday"'
          value={aiText}
          onChange={(e) => setAiText(e.target.value)}
          disabled={aiLoading}
          style={{ padding: 8, flex: 1, border: "none", background: "transparent", outline: "none" }}
        />
        <button
          type="submit"
          disabled={aiLoading || !aiText.trim()}
          style={{ padding: "8px 16px" }}
        >
          {aiLoading ? "Creating…" : "✨ AI Create"}
        </button>
      </form>
      {aiError && <p style={{ color: "crimson", margin: "4px 0" }}>{aiError}</p>}

      <form
        onSubmit={handleCreate}
        data-tour="new-task"
        style={{ display: "flex", gap: 8, margin: "16px 0" }}
      >
        <input
          placeholder="Task title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          style={{ padding: 8, flex: 1 }}
        />
        <input
          placeholder="Description (optional)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          style={{ padding: 8, flex: 2 }}
        />
        <input
          type="date"
          title="Due date (optional)"
          value={dueDate}
          onChange={(e) => setDueDate(e.target.value)}
          style={{ padding: 8 }}
        />
        <button type="submit" style={{ padding: "8px 16px" }}>
          Add
        </button>
      </form>

      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <div
        data-tour="columns"
        style={{ display: "flex", gap: 16, alignItems: "flex-start" }}
      >
        {COLUMNS.map((col) => (
          <section
            key={col.key}
            onDragOver={(e) => handleDragOver(e, col.key)}
            onDragLeave={() =>
              setDropTarget((cur) => (cur === col.key ? null : cur))
            }
            onDrop={(e) => handleDrop(e, col.key)}
            style={{
              flex: 1,
              // Highlight the column while a card is dragged over it.
              background: dropTarget === col.key ? "#dbeafe" : "#f4f5f7",
              outline:
                dropTarget === col.key ? "2px dashed #3b82f6" : "none",
              outlineOffset: -2,
              borderRadius: 8,
              padding: 12,
              minHeight: 200,
              transition: "background 0.15s ease",
            }}
          >
            <h2 style={{ fontSize: 16, marginTop: 0 }}>{col.label}</h2>
            {tasks
              .filter((t) => t.status === col.key)
              .map((task) => (
                <article
                  key={task.id}
                  data-tour="task-card"
                  draggable
                  onDragStart={(e) => handleDragStart(e, task)}
                  onDragEnd={handleDragEnd}
                  style={{
                    background: "#fff",
                    borderRadius: 6,
                    padding: 10,
                    marginBottom: 8,
                    boxShadow: "0 1px 2px rgba(0,0,0,0.1)",
                    cursor: "grab",
                    // The card being dragged is rendered semi-transparent.
                    opacity: draggingId === task.id ? 0.4 : 1,
                  }}
                >
                  <strong>{task.title}</strong>
                  {task.description && (
                    <p style={{ margin: "4px 0", fontSize: 14 }}>
                      {task.description}
                    </p>
                  )}
                  <DueDate task={task} />
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    {COLUMNS.filter((c) => c.key !== task.status).map((c) => (
                      <button
                        key={c.key}
                        onClick={() => move(task, c.key)}
                        style={{ fontSize: 12 }}
                      >
                        → {c.label}
                      </button>
                    ))}
                    <button
                      onClick={() => remove(task)}
                      style={{ fontSize: 12, color: "crimson" }}
                    >
                      Delete
                    </button>
                  </div>
                </article>
              ))}
          </section>
        ))}
      </div>

      {showTour && <Tour steps={TOUR_STEPS} onClose={closeTour} />}
    </div>
  );
}
