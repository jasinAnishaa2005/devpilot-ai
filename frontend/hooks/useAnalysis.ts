"use client";

import { useReducer, useCallback } from "react";
import { useRouter } from "next/navigation";
import { AnalysisState } from "@/types/api";
import { analyzeRepo } from "@/lib/api/analyze";
import { ApiClientError } from "@/lib/api/client";
import { validateRepoForm } from "@/lib/utils/validate";

// ── State machine ──────────────────────────────────────────────────────────────

type Action =
  | { type: "LOADING" }
  | { type: "ERROR"; message: string }
  | { type: "RESET" };

function reducer(_state: AnalysisState, action: Action): AnalysisState {
  switch (action.type) {
    case "LOADING":
      return { status: "loading" };
    case "ERROR":
      return { status: "error", message: action.message };
    case "RESET":
      return { status: "idle" };
    default:
      return { status: "idle" };
  }
}

// ── Hook ───────────────────────────────────────────────────────────────────────

export interface UseAnalysisReturn {
  state: AnalysisState;
  submit: (url: string, branch?: string) => Promise<void>;
  reset: () => void;
}

const STORAGE_KEY = "devpilot_report";

export function useAnalysis(): UseAnalysisReturn {
  const [state, dispatch] = useReducer(reducer, { status: "idle" });
  const router = useRouter();

  const submit = useCallback(
    async (url: string, branch?: string) => {
      // Client-side validation first
      const validationError = validateRepoForm(url);
      if (validationError) {
        dispatch({ type: "ERROR", message: validationError });
        return;
      }

      dispatch({ type: "LOADING" });

      try {
        const report = await analyzeRepo({
          repo_url: url,
          // Only include branch when the user actually provided one
          ...(branch?.trim() ? { branch: branch.trim() } : {}),
        });

        // Persist to sessionStorage so /report can read it across navigation
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(report));
        router.push("/report");
      } catch (err) {
        const message =
          err instanceof ApiClientError
            ? err.message
            : "An unexpected error occurred. Please try again.";
        dispatch({ type: "ERROR", message });
      }
    },
    [router]
  );

  const reset = useCallback(() => dispatch({ type: "RESET" }), []);

  return { state, submit, reset };
}

/**
 * Reads the cached OnboardingReport from sessionStorage.
 * Returns null if not present (e.g., direct navigation or page refresh).
 */
export function getStoredReport() {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}
