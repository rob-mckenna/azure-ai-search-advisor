export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export interface Recommendation {
  id: string;
  title: string;
  detail: string;
  category?: string;
  priority?: string;
}

export interface ChatResponse {
  message: string;
  recommendations: Recommendation[];
  raw?: unknown;
}
