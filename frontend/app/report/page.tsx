"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { OnboardingReport, SectionTitle } from "@/types/api";
import { getStoredReport } from "@/hooks/useAnalysis";
import { ReportHeader } from "@/components/report/ReportHeader";
import { SectionNav } from "@/components/report/SectionNav";
import { SectionGrid } from "@/components/report/SectionGrid";
import { SECTION_TITLES } from "@/constants/sections";

export default function ReportPage() {
  const router = useRouter();
  // Lazy initializer runs only on the client — avoids setState-in-effect
  const [report] = useState<OnboardingReport | null>(() => {
    const stored = getStoredReport();
    return stored ? (stored as OnboardingReport) : null;
  });

  useEffect(() => {
    // Only handle the redirect — no setState call inside the effect
    if (!report) {
      router.replace("/");
    }
  }, [report, router]);

  const handleNewAnalysis = useCallback(() => {
    sessionStorage.removeItem("devpilot_report");
    router.push("/");
  }, [router]);

  // Avoid flash of empty content during SSR hydration
  if (!report) {
    return (
      <div className="min-h-screen bg-[#ECE9E7] flex items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#3A0714] border-t-transparent" />
      </div>
    );
  }

  const sectionTitles = report.sections
    .map((s) => s.title)
    .filter((t): t is SectionTitle =>
      SECTION_TITLES.includes(t as SectionTitle)
    );

  return (
    <div className="min-h-screen bg-[#ECE9E7]">
      {/* Sticky top header */}
      <div className="sticky top-0 z-10 shadow-sm">
        <ReportHeader report={report} onNewAnalysis={handleNewAnalysis} />
      </div>

      {/* Content area */}
      <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <div className="flex gap-6 items-start">
          {/* Sidebar nav — hidden on small screens */}
          <aside className="hidden lg:block w-52 flex-shrink-0 sticky top-24">
            <div className="rounded-xl bg-white border border-[#E2DEDC] p-3 shadow-[0_1px_6px_rgba(58,7,20,0.05)]">
              <SectionNav titles={sectionTitles} />
            </div>
          </aside>

          {/* Mobile section tabs */}
          <div className="lg:hidden w-full mb-4 overflow-x-auto">
            <div className="flex gap-2 pb-1">
              {sectionTitles.map((title) => (
                <a
                  key={title}
                  href={`#section-${title.toLowerCase().replace(/\s+/g, "-")}`}
                  className="flex-shrink-0 rounded-full border border-[#E2DEDC] bg-white px-3 py-1 text-xs font-medium text-[#766A6D] hover:bg-[#F7F2EF] hover:text-[#3A0714] hover:border-[#B85C6E]/40 transition-all duration-150 whitespace-nowrap"
                >
                  {title}
                </a>
              ))}
            </div>
          </div>

          {/* Main report content */}
          <main className="flex-1 min-w-0">
            <SectionGrid report={report} />
          </main>
        </div>
      </div>
    </div>
  );
}
