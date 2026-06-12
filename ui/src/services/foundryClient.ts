import { ensureStaticWebAppsLogin, getAccessToken, getAuthMode } from "./auth";
import type { ChatMessage, ChatResponse, Recommendation } from "../types";

const DEFAULT_AGENT_NAME = "advisor-agent";

function normalizeEndpoint(endpoint: string): string {
  return endpoint.replace(/\/+$/, "");
}

function isAbsoluteUrl(value: string): boolean {
  return /^https?:\/\//i.test(value);
}

function resolveConfiguredEndpoint(): string {
  const configuredEndpoint = import.meta.env.VITE_FOUNDRY_ENDPOINT?.trim();
  if (!configuredEndpoint) {
    throw new Error("Missing VITE_FOUNDRY_ENDPOINT. Point it at your Microsoft Foundry project endpoint.");
  }

  return normalizeEndpoint(configuredEndpoint);
}

function buildChatUrl(): string {
  const configuredEndpoint = resolveConfiguredEndpoint();

  if (getAuthMode() === "static-web-apps") {
    return isAbsoluteUrl(configuredEndpoint) ? "/api/foundry/chat" : `${configuredEndpoint}/chat`;
  }

  return `${configuredEndpoint}/agents/${DEFAULT_AGENT_NAME}/chat/completions`;
}

function normalizeContent(content: unknown): string {
  if (typeof content === "string") {
    return content;
  }

  if (Array.isArray(content)) {
    return content
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }

        if (item && typeof item === "object" && "text" in item && typeof item.text === "string") {
          return item.text;
        }

        return "";
      })
      .filter(Boolean)
      .join("\n");
  }

  return "";
}

function extractRecommendations(payload: any): Recommendation[] {
  const rawRecommendations = payload?.recommendations ?? payload?.findings ?? payload?.data?.recommendations ?? [];
  if (!Array.isArray(rawRecommendations)) {
    return [];
  }

  return rawRecommendations.map((item: unknown, index: number) => {
    if (typeof item === "string") {
      return {
        id: `recommendation-${index + 1}`,
        title: `Recommendation ${index + 1}`,
        detail: item,
      };
    }

    if (item && typeof item === "object") {
      const record = item as Record<string, unknown>;
      return {
        id: String(record.id ?? `recommendation-${index + 1}`),
        title: String(record.title ?? record.name ?? `Recommendation ${index + 1}`),
        detail: String(record.detail ?? record.description ?? record.summary ?? "No detail provided."),
        category: typeof record.category === "string" ? record.category : undefined,
        priority: typeof record.priority === "string" ? record.priority : undefined,
      };
    }

    return {
      id: `recommendation-${index + 1}`,
      title: `Recommendation ${index + 1}`,
      detail: "No detail provided.",
    };
  });
}

function extractAssistantMessage(payload: any): string {
  const choiceMessage = payload?.choices?.[0]?.message?.content;
  const directText = normalizeContent(choiceMessage);
  if (directText) {
    return directText;
  }

  const outputText = normalizeContent(payload?.output_text ?? payload?.response ?? payload?.message ?? payload?.content);
  if (outputText) {
    return outputText;
  }

  return "The advisor returned successfully, but no assistant message was included in the response.";
}

export async function sendChatMessage(messages: ChatMessage[]): Promise<ChatResponse> {
  if (getAuthMode() === "static-web-apps") {
    await ensureStaticWebAppsLogin();
  }

  const accessToken = await getAccessToken();
  const response = await fetch(buildChatUrl(), {
    method: "POST",
    credentials: getAuthMode() === "static-web-apps" ? "include" : "omit",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
    body: JSON.stringify({
      messages: messages.map((message) => ({
        role: message.role,
        content: message.content,
      })),
      stream: false,
    }),
  });

  if (!response.ok) {
    const details = await response.text();
    throw new Error(`Foundry request failed (${response.status}): ${details || response.statusText}`);
  }

  const payload = await response.json();
  return {
    message: extractAssistantMessage(payload),
    recommendations: extractRecommendations(payload),
    raw: payload,
  };
}
