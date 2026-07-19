export type TaskStatus = "todo" | "in_progress" | "done";

export interface Task {
  id: number;
  title: string;
  description: string;
  status: TaskStatus;
  owner_id: number;
  due_date: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface TaskPage {
  items: Task[];
  total: number;
  page: number;
  size: number;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface AIParseResult {
  title: string;
  description: string;
  due_date: string | null;
  source: "ai" | "fallback";
}

export interface DayCount {
  date: string;
  count: number;
}

export interface TaskStats {
  total: number;
  by_status: Record<string, number>;
  completion_rate: number;
  overdue: number;
  completed_last_7_days: DayCount[];
}
