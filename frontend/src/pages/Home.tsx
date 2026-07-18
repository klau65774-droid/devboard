import { CSSProperties } from "react";
import { Link } from "react-router-dom";

const FEATURES: { icon: string; title: string; description: string }[] = [
  {
    icon: "🔐",
    title: "JWT Authentication",
    description:
      "Secure register/login with hashed passwords and signed JWT access tokens.",
  },
  {
    icon: "🧩",
    title: "Drag-and-Drop Kanban",
    description:
      "Move tasks between To Do, In Progress and Done with native HTML5 drag & drop.",
  },
  {
    icon: "⚡",
    title: "REST API with FastAPI",
    description:
      "Typed, validated endpoints with automatic Swagger docs and per-user isolation.",
  },
  {
    icon: "✅",
    title: "pytest Coverage",
    description:
      "Backend test suite covering auth, CRUD, pagination and authorization boundaries.",
  },
  {
    icon: "🔄",
    title: "CI/CD with GitHub Actions",
    description:
      "Every push runs the backend tests and a strict frontend typecheck + build.",
  },
  {
    icon: "🐳",
    title: "Docker Compose",
    description:
      "One command spins up the full stack: API, database volume and nginx-served UI.",
  },
];

const styles: Record<string, CSSProperties> = {
  page: {
    fontFamily: "system-ui, sans-serif",
    minHeight: "100vh",
    background: "#0f172a",
    color: "#e2e8f0",
  },
  hero: {
    maxWidth: 800,
    margin: "0 auto",
    padding: "120px 24px 80px",
    textAlign: "center",
  },
  title: {
    fontSize: 56,
    margin: 0,
    background: "linear-gradient(90deg, #60a5fa, #a78bfa)",
    WebkitBackgroundClip: "text",
    backgroundClip: "text",
    color: "transparent",
  },
  slogan: {
    fontSize: 20,
    color: "#94a3b8",
    margin: "16px 0 40px",
  },
  ctaRow: {
    display: "flex",
    gap: 16,
    justifyContent: "center",
  },
  primaryBtn: {
    padding: "12px 28px",
    fontSize: 16,
    fontWeight: 600,
    color: "#fff",
    background: "#3b82f6",
    border: "none",
    borderRadius: 8,
    cursor: "pointer",
    textDecoration: "none",
  },
  secondaryBtn: {
    padding: "12px 28px",
    fontSize: 16,
    fontWeight: 600,
    color: "#e2e8f0",
    background: "transparent",
    border: "1px solid #475569",
    borderRadius: 8,
    cursor: "pointer",
    textDecoration: "none",
  },
  features: {
    maxWidth: 1000,
    margin: "0 auto",
    padding: "0 24px 96px",
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
    gap: 20,
  },
  card: {
    background: "#1e293b",
    border: "1px solid #334155",
    borderRadius: 12,
    padding: 24,
  },
  cardTitle: { fontSize: 17, margin: "8px 0" },
  cardText: { fontSize: 14, color: "#94a3b8", margin: 0, lineHeight: 1.6 },
};

// Public landing page: hero + feature grid.
export default function Home() {
  return (
    <div style={styles.page}>
      <section style={styles.hero}>
        <h1 style={styles.title}>DevBoard</h1>
        <p style={styles.slogan}>
          A full-stack task management platform — FastAPI, React, and a
          drag-and-drop kanban board, shipped with tests, CI and Docker.
        </p>
        <div style={styles.ctaRow}>
          <Link to="/login" style={styles.primaryBtn}>
            Get Started
          </Link>
          <a
            href="https://github.com/klau65774-droid/devboard"
            target="_blank"
            rel="noreferrer"
            style={styles.secondaryBtn}
          >
            View on GitHub
          </a>
        </div>
      </section>

      <section style={styles.features}>
        {FEATURES.map((f) => (
          <article key={f.title} style={styles.card}>
            <span style={{ fontSize: 28 }}>{f.icon}</span>
            <h3 style={styles.cardTitle}>{f.title}</h3>
            <p style={styles.cardText}>{f.description}</p>
          </article>
        ))}
      </section>
    </div>
  );
}
