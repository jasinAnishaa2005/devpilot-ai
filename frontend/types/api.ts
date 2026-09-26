// ── Request ────────────────────────────────────────────────────────────────────

export interface AnalyzeRequest {
  repo_url: string;
  branch?: string; // optional — backend auto-detects default branch when omitted
}

// ── Response ───────────────────────────────────────────────────────────────────

export type SectionTitle =
  | "Project Overview"
  | "Architecture"
  | "Important Files"
  | "Setup Instructions"
  | "Dependencies"
  | "Potential Risks"
  | "Recommended First Tasks";

export interface ReportSection {
  title: SectionTitle;
  content: string; // Markdown string — must be rendered, not displayed as plain text
}

export interface OnboardingReport {
  repo_url: string;    // "owner/repo" format (NOT a full URL)
  repo_name: string;
  sections: ReportSection[]; // always exactly 7 sections in order
  generated_at: string;      // ISO-8601 UTC
}

// ── Error ──────────────────────────────────────────────────────────────────────

export interface ApiError {
  detail: string; // human-readable — show directly to the user
}

// ── Application state machine ──────────────────────────────────────────────────

export type AnalysisState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; report: OnboardingReport }
  | { status: "error"; message: string };

// ── Health ─────────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: "healthy" | string;
}
