import { ensureStaticWebAppsLogin, getAccessToken, getAuthMode } from "./auth";
import type { ChatMessage, ChatResponse, Recommendation } from "../types";
import {
  SAMPLE_ANALYZE_PAYLOAD,
  SAMPLE_RECOMMEND_PREFERENCES,
  SAMPLE_SIMULATE_PAYLOAD,
  analyzeService,
  checkHealth,
  getRecommendations,
  mapRecommendations,
  simulateCost,
  type AnalyzeResponsePayload,
  type RecommendPayload,
  type SimulatePayload,
} from "./apiClient";

const DEFAULT_AGENT_NAME = "advisor-agent";
const LOCAL_MODE = "local";
const FOUNDRY_MODE = "foundry";

export type AdvisorConnectionMode = typeof LOCAL_MODE | typeof FOUNDRY_MODE;

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

export function getAdvisorConnectionMode(): AdvisorConnectionMode {
  const configuredMode = import.meta.env.VITE_MODE?.trim().toLowerCase();
  if (configuredMode === LOCAL_MODE || Boolean(import.meta.env.VITE_API_URL?.trim())) {
    return LOCAL_MODE;
  }

  if (Boolean(import.meta.env.VITE_FOUNDRY_ENDPOINT?.trim())) {
    return FOUNDRY_MODE;
  }

  return FOUNDRY_MODE;
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
  if (getAdvisorConnectionMode() === LOCAL_MODE) {
    return sendLocalChatMessage(messages);
  }

  return sendFoundryChatMessage(messages);
}

async function sendFoundryChatMessage(messages: ChatMessage[]): Promise<ChatResponse> {
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

function getLatestUserMessage(messages: ChatMessage[]): ChatMessage {
  const latestMessage = [...messages].reverse().find((message) => message.role === "user");
  if (!latestMessage) {
    throw new Error("A user message is required before sending a chat request.");
  }

  return latestMessage;
}

function parseJsonFromMessage(content: string): Record<string, unknown> | null {
  const trimmed = content.trim();
  const fencedMatch = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i);
  const candidate = fencedMatch?.[1]?.trim() ?? trimmed;

  if (!candidate.startsWith("{")) {
    return null;
  }

  try {
    const parsed = JSON.parse(candidate) as unknown;
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

function detectLocalIntent(content: string): "analyze" | "recommend" | "simulate" | "health" {
  const normalized = content.toLowerCase();

  if (/\b(health|status|ping)\b/.test(normalized)) {
    return "health";
  }

  if (/\b(simulate|simulation|cost model|cost simulation|what if)\b/.test(normalized)) {
    return "simulate";
  }

  if (/\b(recommend|recommendation|optimi[sz]e|suggest)\b/.test(normalized)) {
    return "recommend";
  }

  return "analyze";
}

function isAnalysisResponsePayload(payload: unknown): payload is AnalyzeResponsePayload {
  return (
    typeof payload === "object" &&
    payload !== null &&
    "findings" in payload &&
    Array.isArray(payload.findings) &&
    "summary" in payload &&
    typeof payload.summary === "object" &&
    payload.summary !== null
  );
}

function formatCurrency(value: number, currency: string): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatAnalyzeResponse(response: AnalyzeResponsePayload): ChatResponse {
  const topFindings = response.findings
    .slice(0, 3)
    .map((finding) => `• ${finding.title} (${finding.severity})`)
    .join("\n");
  const notes = response.notes.length > 0 ? `\nNotes: ${response.notes.join(" ")}` : "";

  return {
    message: `${response.summary.overall_assessment}\n\nFindings: ${response.summary.finding_count} total.${topFindings ? `\n${topFindings}` : ""}${notes}`,
    recommendations: extractRecommendations(response),
    raw: response,
  };
}

function formatRecommendResponse(payload: Awaited<ReturnType<typeof getRecommendations>>): ChatResponse {
  const recommendationList = payload.recommendations
    .slice(0, 3)
    .map((recommendation) => `• ${recommendation.title} (${recommendation.priority})`)
    .join("\n");
  const notes = payload.notes.length > 0 ? `\nNotes: ${payload.notes.join(" ")}` : "";

  return {
    message: `${payload.summary}${recommendationList ? `\n\nTop recommendations:\n${recommendationList}` : ""}${notes}`,
    recommendations: mapRecommendations(payload.recommendations),
    raw: payload,
  };
}

function formatSimulationResponse(payload: Awaited<ReturnType<typeof simulateCost>>): ChatResponse {
  const currency = payload.comparison.current_estimate.currency;
  const savings = payload.comparison.monthly_savings_percent;
  const savingsText = typeof savings === "number" ? ` (${savings.toFixed(1)}% savings)` : "";

  return {
    message:
      `Current monthly cost: ${formatCurrency(payload.comparison.current_estimate.monthly_total, currency)}\n` +
      `Proposed monthly cost: ${formatCurrency(payload.comparison.proposed_estimate.monthly_total, currency)}\n` +
      `Delta: ${formatCurrency(payload.comparison.monthly_delta, currency)}${savingsText}\n\n` +
      `Capacity risk: ${payload.projected_impact.capacity_risk}\n` +
      `Latency expectation: ${payload.projected_impact.latency_expectation}`,
    recommendations: [],
    raw: payload,
  };
}

async function sendLocalChatMessage(messages: ChatMessage[]): Promise<ChatResponse> {
  const latestUserMessage = getLatestUserMessage(messages);
  const parsedPayload = parseJsonFromMessage(latestUserMessage.content);
  const intent = detectLocalIntent(latestUserMessage.content);

  switch (intent) {
    case "health": {
      const health = await checkHealth();
      return {
        message: `${health.service} is ${health.status} (v${health.version}). Checked at ${new Date(health.checked_at).toLocaleString()}.`,
        recommendations: [],
        raw: health,
      };
    }
    case "simulate": {
      const payload =
        parsedPayload &&
        ("current_configuration" in parsedPayload || "cost_model_request" in parsedPayload || "proposed_changes" in parsedPayload)
          ? (parsedPayload as unknown as SimulatePayload)
          : SAMPLE_SIMULATE_PAYLOAD;
      const simulation = await simulateCost(payload);
      return formatSimulationResponse(simulation);
    }
    case "recommend": {
      let payload: RecommendPayload;

      if (parsedPayload && ("analysis" in parsedPayload || "configuration" in parsedPayload)) {
        payload = parsedPayload as unknown as RecommendPayload;
      } else if (parsedPayload && isAnalysisResponsePayload(parsedPayload)) {
        payload = {
          analysis: parsedPayload,
          preferences: SAMPLE_RECOMMEND_PREFERENCES,
        };
      } else {
        const analysis = await analyzeService(SAMPLE_ANALYZE_PAYLOAD);
        payload = {
          analysis,
          preferences: SAMPLE_RECOMMEND_PREFERENCES,
        };
      }

      const recommendations = await getRecommendations(payload);
      return formatRecommendResponse(recommendations);
    }
    case "analyze":
    default: {
      const payload =
        parsedPayload && "configuration" in parsedPayload && "metrics" in parsedPayload
          ? (parsedPayload as unknown as typeof SAMPLE_ANALYZE_PAYLOAD)
          : SAMPLE_ANALYZE_PAYLOAD;
      const analysis = await analyzeService(payload);
      return formatAnalyzeResponse(analysis);
    }
  }
}
