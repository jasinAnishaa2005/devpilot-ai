import { apiFetch } from "./client";
import { AnalyzeRequest, OnboardingReport } from "@/types/api";

/**
 * POST /analyze
 * Submits a GitHub repository URL (and optional branch) for analysis.
 * Returns a structured OnboardingReport on success.
 * Throws ApiClientError on 4xx/5xx with the backend's detail message.
 */
export async function analyzeRepo(
  req: AnalyzeRequest
): Promise<OnboardingReport> {
  return apiFetch<OnboardingReport>("/analyze", {
    method: "POST",
    body: JSON.stringify(req),
  });
}
