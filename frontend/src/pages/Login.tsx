import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, register } from "../api";

// Combined login / register page.
export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      if (mode === "register") {
        await register(email, password);
      }
      await login(email, password);
      navigate("/board");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    }
  }

  return (
    <div
      style={{
        maxWidth: 360,
        margin: "80px auto",
        padding: 24,
        fontFamily: "system-ui, sans-serif",
        border: "1px solid #ddd",
        borderRadius: 8,
      }}
    >
      <h1 style={{ fontSize: 22, marginTop: 0 }}>DevBoard</h1>
      <form onSubmit={handleSubmit} style={{ display: "grid", gap: 12 }}>
        <input
          type="email"
          placeholder="Email"
          value={email}
          required
          onChange={(e) => setEmail(e.target.value)}
          style={{ padding: 8 }}
        />
        <input
          type="password"
          placeholder="Password (min 6 chars)"
          value={password}
          required
          minLength={6}
          onChange={(e) => setPassword(e.target.value)}
          style={{ padding: 8 }}
        />
        <button type="submit" style={{ padding: 8, cursor: "pointer" }}>
          {mode === "login" ? "Log in" : "Sign up"}
        </button>
      </form>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      <p style={{ fontSize: 14 }}>
        {mode === "login" ? "No account yet?" : "Already have an account?"}{" "}
        <a
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setMode(mode === "login" ? "register" : "login");
          }}
        >
          {mode === "login" ? "Sign up" : "Log in"}
        </a>
      </p>
    </div>
  );
}
