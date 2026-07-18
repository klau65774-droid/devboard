export type TaskStatus = "todo" | "in_progress" | "done";

export interface Task {
  id: number;
  title: string;
  description: string;
  status: TaskStatus;
  owner_id: number;
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
