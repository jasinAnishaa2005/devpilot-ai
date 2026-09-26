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
  const [report, setReport] = useState<OnboardingReport | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const stored = getStoredReport();
    if (!stored) {
      // No report in storage — user navigated directly or refreshed
      router.replace("/");
    } else {
      setReport(stored as OnboardingReport);
    }
  }, [router]);

  const handleNewAnalysis = useCallback(() => {
    sessionStorage.removeItem("devpilot_report");
    router.push("/");
  }, [router]);

  // Avoid flash of empty content during SSR hydration
  if (!mounted || !report) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
      </div>
    );
  }

  const sectionTitles = report.sections
    .map((s) => s.title)
    .filter((t): t is SectionTitle =>
      SECTION_TITLES.includes(t as SectionTitle)
    );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sticky top header */}
      <div className="sticky top-0 z-10 shadow-sm">
        <ReportHeader report={report} onNewAnalysis={handleNewAnalysis} />
      </div>

      {/* Content area */}
      <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <div className="flex gap-6 items-start">
          {/* Sidebar nav — hidden on small screens */}
          <aside className="hidden lg:block w-52 flex-shrink-0 sticky top-24">
            <SectionNav titles={sectionTitles} />
          </aside>

          {/* Mobile section tabs */}
          <div className="lg:hidden w-full mb-4 overflow-x-auto">
            <div className="flex gap-2 pb-1">
              {sectionTitles.map((title) => (
                <a
                  key={title}
                  href={`#section-${title.toLowerCase().replace(/\s+/g, "-")}`}
                  className="flex-shrink-0 rounded-full border border-gray-200 bg-white px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors whitespace-nowrap"
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
