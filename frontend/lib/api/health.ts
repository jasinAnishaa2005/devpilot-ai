import { apiFetch } from "./client";
import { HealthResponse } from "@/types/api";

/**
 * GET /health
 * Quick liveness check for the backend.
 */
export async function checkHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}
