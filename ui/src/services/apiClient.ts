import type { Recommendation } from "../types";

type Priority = "high" | "medium" | "low";

export interface AnalyzeServicePayload {
  configuration: {
    service_name: string;
    region: string;
    capacity: {
      pricing_model: "dedicated" | "serverless";
      sku: string;
      replica_count: number;
      partition_count: number;
      zone_redundancy_enabled: boolean;
    };
    features: {
      semantic_ranker_enabled: boolean;
      vector_search_enabled: boolean;
      ai_enrichment_enabled: boolean;
      knowledge_store_enabled: boolean;
    };
    index_topology: {
      index_count: number;
      indexer_count: number;
      skillset_count: number;
      total_document_count: number;
      total_index_size_gb: number;
      vector_index_size_gb: number;
    };
    security: {
      api_keys_enabled: boolean;
      managed_identity_enabled: boolean;
      private_endpoint_enabled: boolean;
      customer_managed_keys_enabled: boolean;
    };
    notes: string[];
  };
  metrics: {
    observation_window_days: number;
    query: {
      average_queries_per_second: number;
      peak_queries_per_second: number;
      monthly_query_volume: number;
      p95_query_latency_ms: number;
      cache_hit_ratio: number;
    };
    indexing: {
      daily_document_updates: number;
      full_rebuilds_per_month: number;
      average_indexing_latency_minutes: number;
    };
    utilization: {
      replica_utilization_percent: number;
      partition_utilization_percent: number;
      storage_utilization_percent: number;
      semantic_queries_per_day: number;
      vector_queries_per_day: number;
    };
  };
  include_cost_signals?: boolean;
  include_feature_assessment?: boolean;
}

export interface AnalysisFinding {
  finding_id: string;
  category: string;
  severity: Priority | "critical";
  title: string;
  description: string;
  recommendation_hint?: string | null;
  potential_monthly_cost_impact_usd?: number | null;
}

export interface AnalyzeResponsePayload {
  request_id: string;
  status: string;
  generated_at: string;
  summary: {
    finding_count: number;
    highest_severity: string;
    optimization_themes: string[];
    overall_assessment: string;
  };
  findings: AnalysisFinding[];
  notes: string[];
}

export interface RecommendPayload {
  analysis?: AnalyzeResponsePayload;
  configuration?: AnalyzeServicePayload["configuration"];
  metrics?: AnalyzeServicePayload["metrics"];
  preferences?: {
    max_recommendations?: number;
    prioritize_for?: Array<"cost" | "performance" | "availability" | "operability">;
    include_remediation_steps?: boolean;
  };
}

export interface RecommendationItem {
  recommendation_id: string;
  priority: Priority;
  title: string;
  summary: string;
  rationale: string;
  tradeoffs: string[];
}

export interface RecommendResponsePayload {
  request_id: string;
  status: string;
  generated_at: string;
  source: string;
  summary: string;
  recommendations: RecommendationItem[];
  notes: string[];
}

export interface SimulatePayload {
  current_configuration?: AnalyzeServicePayload["configuration"];
  current_metrics?: AnalyzeServicePayload["metrics"];
  proposed_changes?: Array<{
    change_id: string;
    target: string;
    attribute: string;
    current_value?: unknown;
    proposed_value: unknown;
    rationale: string;
  }>;
  cost_model_request?: {
    dedicated_search?: {
      tier: string;
      replicas: number;
      partitions: number;
      months: number;
    };
    serverless_search?: {
      monthly_queries: number;
      average_billable_compute_units_per_query: number;
      months: number;
    };
    feature_costs?: {
      semantic_queries_per_month?: number;
      enrichment_transactions_per_month?: number;
      vector_index_storage_gb?: number;
      months?: number;
    };
  };
  assumptions?: {
    pricing_horizon_days?: number;
    currency?: string;
    notes?: string[];
  };
}

export interface SimulateResponsePayload {
  request_id: string;
  status: string;
  generated_at: string;
  comparison: {
    current_estimate: {
      currency: string;
      monthly_total: number;
    };
    proposed_estimate: {
      currency: string;
      monthly_total: number;
    };
    monthly_delta: number;
    monthly_savings_percent?: number | null;
  };
  projected_impact: {
    capacity_risk: string;
    latency_expectation: string;
    operational_notes: string[];
  };
  notes: string[];
}

export interface HealthResponsePayload {
  status: string;
  service: string;
  version: string;
  checked_at: string;
  notes: string[];
}

const DEFAULT_API_URL = "http://localhost:8000";

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/+$/, "");
}

function getApiBaseUrl(): string {
  return normalizeBaseUrl(import.meta.env.VITE_API_URL?.trim() || DEFAULT_API_URL);
}

async function parseResponse<T>(response: Response): Promise<T> {
  const rawBody = await response.text();
  let payload: T | null = null;

  if (rawBody) {
    try {
      payload = JSON.parse(rawBody) as T;
    } catch {
      payload = null;
    }
  }

  if (response.ok) {
    return payload as T;
  }

  const errorMessage =
    typeof payload === "object" && payload !== null && "message" in payload && typeof payload.message === "string"
      ? payload.message
      : rawBody || response.statusText;

  throw new Error(`API request failed (${response.status}): ${errorMessage}`);
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });

  return parseResponse<T>(response);
}

export async function analyzeService(payload: AnalyzeServicePayload): Promise<AnalyzeResponsePayload> {
  return requestJson<AnalyzeResponsePayload>("/analyze", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getRecommendations(payload: RecommendPayload): Promise<RecommendResponsePayload> {
  return requestJson<RecommendResponsePayload>("/recommend", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function simulateCost(payload: SimulatePayload): Promise<SimulateResponsePayload> {
  return requestJson<SimulateResponsePayload>("/simulate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function checkHealth(): Promise<HealthResponsePayload> {
  return requestJson<HealthResponsePayload>("/health", {
    method: "GET",
  });
}

export const SAMPLE_ANALYZE_PAYLOAD: AnalyzeServicePayload = {
  configuration: {
    service_name: "contoso-product-search-prod",
    region: "eastus2",
    capacity: {
      pricing_model: "dedicated",
      sku: "s2",
      replica_count: 6,
      partition_count: 4,
      zone_redundancy_enabled: true,
    },
    features: {
      semantic_ranker_enabled: false,
      vector_search_enabled: false,
      ai_enrichment_enabled: false,
      knowledge_store_enabled: false,
    },
    index_topology: {
      index_count: 8,
      indexer_count: 2,
      skillset_count: 0,
      total_document_count: 12500000,
      total_index_size_gb: 48.6,
      vector_index_size_gb: 0,
    },
    security: {
      api_keys_enabled: true,
      managed_identity_enabled: true,
      private_endpoint_enabled: true,
      customer_managed_keys_enabled: false,
    },
    notes: [
      "Catalog search workload has strong uptime requirements but modest traffic.",
      "Replica and partition counts are materially higher than sustained demand requires.",
    ],
  },
  metrics: {
    observation_window_days: 30,
    query: {
      average_queries_per_second: 0.21,
      peak_queries_per_second: 0.37,
      monthly_query_volume: 540000,
      p95_query_latency_ms: 88,
      cache_hit_ratio: 0,
    },
    indexing: {
      daily_document_updates: 28000,
      full_rebuilds_per_month: 0,
      average_indexing_latency_minutes: 0,
    },
    utilization: {
      replica_utilization_percent: 11.4,
      partition_utilization_percent: 24.1,
      storage_utilization_percent: 24.1,
      semantic_queries_per_day: 0,
      vector_queries_per_day: 0,
    },
  },
  include_cost_signals: true,
  include_feature_assessment: true,
};

export const SAMPLE_RECOMMEND_PREFERENCES: NonNullable<RecommendPayload["preferences"]> = {
  max_recommendations: 5,
  prioritize_for: ["cost", "availability"],
  include_remediation_steps: true,
};

export const SAMPLE_SIMULATE_PAYLOAD: SimulatePayload = {
  current_configuration: SAMPLE_ANALYZE_PAYLOAD.configuration,
  current_metrics: SAMPLE_ANALYZE_PAYLOAD.metrics,
  proposed_changes: [
    {
      change_id: "reduce-replicas",
      target: "capacity",
      attribute: "replica_count",
      current_value: SAMPLE_ANALYZE_PAYLOAD.configuration.capacity.replica_count,
      proposed_value: SAMPLE_ANALYZE_PAYLOAD.configuration.capacity.replica_count - 1,
      rationale: "Observed load is low relative to the current replica footprint.",
    },
  ],
  assumptions: {
    pricing_horizon_days: 30,
    currency: "USD",
    notes: ["Local development scenario using the over_provisioned sample workload."],
  },
};

export function mapRecommendations(items: RecommendationItem[]): Recommendation[] {
  return items.map((item, index) => ({
    id: item.recommendation_id || `recommendation-${index + 1}`,
    title: item.title,
    detail: item.summary,
    priority: item.priority,
    category: item.tradeoffs.length > 0 ? "tradeoffs noted" : undefined,
  }));
}
