import { useCallback, useEffect, useState } from "react";
import type { CSSProperties } from "react";
import { Link, useNavigate } from "react-router-dom";
import { fetchStats, setToken } from "../api";
import type { TaskStats, TaskStatus } from "../types";

const STATUS_META: { key: TaskStatus; label: string; color: string }[] = [
  { key: "todo", label: "To Do", color: "#6b7280" },
  { key: "in_progress", label: "In Progress", color: "#3b82f6" },
  { key: "done", label: "Done", color: "#16a34a" },
];

const card: CSSProperties = {
  background: "#f4f5f7",
  borderRadius: 8,
  padding: 16,
};

// Completion rate ring: a circle whose stroke is dashed with an arc of
// length rate * circumference, rotated so the arc starts at 12 o'clock.
function CompletionRing({ rate }: { rate: number }) {
  const r = 54;
  const circumference = 2 * Math.PI * r;
  const pct = Math.round(rate * 100);
  return (
    <div style={{ ...card, textAlign: "center" }}>
      <h2 style={{ fontSize: 16, marginTop: 0 }}>Completion rate</h2>
      <svg width={140} height={140} viewBox="0 0 140 140">
        <circle cx={70} cy={70} r={r} fill="none" stroke="#e5e7eb" strokeWidth={14} />
        <circle
          cx={70}
          cy={70}
          r={r}
          fill="none"
          stroke="#16a34a"
          strokeWidth={14}
          strokeLinecap="round"
          strokeDasharray={`${rate * circumference} ${circumference}`}
          transform="rotate(-90 70 70)"
        />
        <text x={70} y={76} textAnchor="middle" fontSize={24} fontWeight="bold">
          {pct}%
        </text>
      </svg>
    </div>
  );
}

// Horizontal bar per status, widths relative to the largest count.
function StatusBars({ stats }: { stats: TaskStats }) {
  const max = Math.max(1, ...STATUS_META.map((s) => stats.by_status[s.key] ?? 0));
  return (
    <div style={card}>
      <h2 style={{ fontSize: 16, marginTop: 0 }}>By status</h2>
      {STATUS_META.map((s) => {
        const count = stats.by_status[s.key] ?? 0;
        return (
          <div
            key={s.key}
            style={{ display: "flex", alignItems: "center", gap: 8, margin: "8px 0" }}
          >
            <span style={{ width: 90, fontSize: 13 }}>{s.label}</span>
            <div style={{ flex: 1, background: "#e5e7eb", borderRadius: 4 }}>
              <div
                style={{
                  width: `${(count / max) * 100}%`,
                  minWidth: count > 0 ? 4 : 0,
                  height: 14,
                  background: s.color,
                  borderRadius: 4,
                }}
              />
            </div>
            <span style={{ width: 24, fontSize: 13, textAlign: "right" }}>{count}</span>
          </div>
        );
      })}
    </div>
  );
}

// Bar chart of tasks completed per day over the last 7 days.
function TrendChart({ days }: { days: TaskStats["completed_last_7_days"] }) {
  const max = Math.max(1, ...days.map((d) => d.count));
  return (
    <div style={card}>
      <h2 style={{ fontSize: 16, marginTop: 0 }}>Completed last 7 days</h2>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 8, height: 120 }}>
        {days.map((d) => (
          <div
            key={d.date}
            style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}
            title={`${d.date}: ${d.count}`}
          >
            <span style={{ fontSize: 12, color: "#6b7280" }}>{d.count}</span>
            <div
              style={{
                width: "100%",
                height: `${(d.count / max) * 80}%`,
                minHeight: d.count > 0 ? 4 : 0,
                background: "#3b82f6",
                borderRadius: "4px 4px 0 0",
              }}
            />
            <span style={{ fontSize: 11, color: "#6b7280" }}>{d.date.slice(5)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Stats dashboard with hand-rolled SVG/CSS charts (no chart library).
export default function Dashboard() {
  const [stats, setStats] = useState<TaskStats | null>(null);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const load = useCallback(async () => {
    try {
      setStats(await fetchStats());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load stats");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function logout() {
    setToken(null);
    navigate("/login");
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
          <Link to="/board">
            <button>← Board</button>
          </Link>
          <button onClick={logout}>Log out</button>
        </div>
      </header>

      <h2 style={{ fontSize: 18 }}>Dashboard</h2>

      {error && <p style={{ color: "crimson" }}>{error}</p>}
      {!stats && !error && <p style={{ color: "#6b7280" }}>Loading…</p>}

      {stats && (
        <>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "stretch" }}>
            <CompletionRing rate={stats.completion_rate} />
            <div style={{ ...card, flex: 1, minWidth: 240 }}>
              <h2 style={{ fontSize: 16, marginTop: 0 }}>Overview</h2>
              <p style={{ fontSize: 14, margin: "8px 0" }}>
                Total tasks: <strong>{stats.total}</strong>
              </p>
              <p style={{ fontSize: 14, margin: "8px 0" }}>
                Overdue:{" "}
                <strong style={{ color: stats.overdue > 0 ? "crimson" : "#16a34a" }}>
                  {stats.overdue}
                </strong>
              </p>
            </div>
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
              gap: 16,
              marginTop: 16,
            }}
          >
            <StatusBars stats={stats} />
            <TrendChart days={stats.completed_last_7_days} />
          </div>
        </>
      )}
    </div>
  );
}
