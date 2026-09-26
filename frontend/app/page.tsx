"use client";

import { HeroHeadline } from "@/components/home/HeroHeadline";
import { RepoInputForm } from "@/components/home/RepoInputForm";
import { AnalysisProgress } from "@/components/loading/AnalysisProgress";
import { useAnalysis } from "@/hooks/useAnalysis";

export default function HomePage() {
  const { state, submit, reset } = useAnalysis();

  // Show full-page loading when analysis is in progress
  if (state.status === "loading") {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <AnalysisProgress />
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-2xl flex flex-col items-center gap-10">
        <HeroHeadline />
        <RepoInputForm state={state} onSubmit={submit} onReset={reset} />
      </div>

      {/* Footer */}
      <footer className="mt-16 text-center text-xs text-gray-400">
        DevPilot AI — Powered by GitHub API
      </footer>
    </main>
  );
}
