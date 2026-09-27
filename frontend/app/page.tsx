"use client";

import { HeroHeadline } from "@/components/home/HeroHeadline";
import { RepoInputForm } from "@/components/home/RepoInputForm";
import { AnalysisProgress } from "@/components/loading/AnalysisProgress";
import { useAnalysis } from "@/hooks/useAnalysis";
import { Code2, FileText, Users, GitBranch } from "lucide-react";

const FEATURES = [
  {
    icon: Code2,
    title: "AI Analysis",
    description: "Deep analysis of repository structure, tech stack, and patterns.",
  },
  {
    icon: FileText,
    title: "Clear Reports",
    description: "Structured markdown reports you can read in minutes, not hours.",
  },
  {
    icon: Users,
    title: "Developer Focused",
    description: "Built for engineers onboarding to new codebases fast.",
  },
  {
    icon: GitBranch,
    title: "Open Source Friendly",
    description: "Works with any public GitHub repository, no setup required.",
  },
];

export default function HomePage() {
  const { state, submit, reset } = useAnalysis();

  // Show full-page loading when analysis is in progress
  if (state.status === "loading") {
    return (
      <main className="wine-bg min-h-screen flex items-center justify-center p-6">
        <AnalysisProgress />
      </main>
    );
  }

  return (
    <main className="wine-bg min-h-screen flex flex-col items-center justify-center p-6 overflow-hidden">
      {/* Decorative orbital ring (top-left) */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute top-[-80px] left-[-80px] h-[320px] w-[320px] rounded-full border border-[#7A1830]/20 opacity-40"
      />
      {/* Decorative orbital ring (bottom-right) */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute bottom-[-60px] right-[-60px] h-[260px] w-[260px] rounded-full border border-[#B85C6E]/15 opacity-30"
      />

      <div className="relative z-10 w-full max-w-2xl flex flex-col items-center gap-10">
        {/* Logo / header */}
        <div className="flex items-center gap-3 mb-2">
          <div className="h-10 w-10 rounded-xl bg-[#520B1B] border border-[#7A1830]/60 flex items-center justify-center shadow-[0_0_16px_rgba(122,24,48,0.4)]">
            <svg className="h-5 w-5 text-[#F7F2EF]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5" />
            </svg>
          </div>
          <div className="flex flex-col leading-none">
            <span className="text-sm font-bold text-[#F7F2EF] tracking-wide">DevPilot AI</span>
            <span className="text-xs text-[#F7F2EF]/50 tracking-wider">AI Developer Assistant</span>
          </div>
        </div>

        <HeroHeadline />
        <RepoInputForm state={state} onSubmit={submit} onReset={reset} />

        {/* Feature cards */}
        <div className="w-full grid grid-cols-2 sm:grid-cols-4 gap-3 mt-2">
          {FEATURES.map(({ icon: Icon, title, description }) => (
            <div
              key={title}
              className="glass-card rounded-xl p-4 flex flex-col gap-2 transition-transform duration-200 hover:-translate-y-1 hover:shadow-[0_8px_24px_rgba(58,7,20,0.35)]"
            >
              <Icon className="h-5 w-5 text-[#B85C6E]" strokeWidth={1.6} />
              <span className="text-xs font-semibold text-[#F7F2EF]">{title}</span>
              <p className="text-xs text-[#F7F2EF]/55 leading-relaxed">{description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <footer className="relative z-10 mt-12 text-center text-xs text-[#F7F2EF]/30">
        DevPilot AI — Powered by GitHub API
      </footer>
    </main>
  );
}
