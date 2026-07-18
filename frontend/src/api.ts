// Thin fetch wrapper that automatically attaches the JWT access token.
import type { Task, TaskPage, TaskStatus, Token } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "devboard_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> | undefined),
  };
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (options.body) {
    headers["Content-Type"] = "application/json";
  }

  const resp = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (resp.status === 401) {
    // Token expired or invalid: force re-login.
    setToken(null);
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (!resp.ok) {
    const detail = await resp.text().catch(() => "");
    throw new Error(`Request failed (${resp.status}): ${detail}`);
  }
  if (resp.status === 204) {
    return undefined as T;
  }
  return (await resp.json()) as T;
}

export async function register(email: string, password: string): Promise<void> {
  await request("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function login(email: string, password: string): Promise<Token> {
  // OAuth2 password flow expects form-encoded data.
  const body = new URLSearchParams({ username: email, password });
  const resp = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!resp.ok) {
    throw new Error("Login failed: incorrect email or password");
  }
  const token = (await resp.json()) as Token;
  setToken(token.access_token);
  return token;
}

export function fetchTasks(status?: TaskStatus): Promise<TaskPage> {
  const query = status ? `?status=${status}` : "";
  return request<TaskPage>(`/tasks${query}`);
}

export function createTask(title: string, description: string): Promise<Task> {
  return request<Task>("/tasks", {
    method: "POST",
    body: JSON.stringify({ title, description }),
  });
}

export function updateTaskStatus(id: number, status: TaskStatus): Promise<Task> {
  return request<Task>(`/tasks/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export function deleteTask(id: number): Promise<void> {
  return request<void>(`/tasks/${id}`, { method: "DELETE" });
}
