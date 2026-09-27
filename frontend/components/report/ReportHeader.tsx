import { ExternalLink, GitBranch, Clock } from "lucide-react";
import { OnboardingReport } from "@/types/api";
import { repoUrlToFullUrl, formatGeneratedAt } from "@/lib/utils/format";
import { Button } from "@/components/ui/Button";

interface ReportHeaderProps {
  report: OnboardingReport;
  onNewAnalysis: () => void;
}

export function ReportHeader({ report, onNewAnalysis }: ReportHeaderProps) {
  const fullUrl = repoUrlToFullUrl(report.repo_url);

  return (
    <div className="border-b border-[#E2DEDC] bg-white px-6 py-4">
      <div className="max-w-7xl mx-auto flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-1 min-w-0">
          {/* Logo + breadcrumb */}
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-md bg-[#3A0714] flex items-center justify-center flex-shrink-0">
              <svg className="h-3.5 w-3.5 text-[#F7F2EF]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5" />
              </svg>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-[#766A6D]">
              <span className="font-semibold text-[#3A0714]">DevPilot</span>
              <span>/</span>
              <span>Onboarding Report</span>
            </div>
          </div>

          {/* Repo name */}
          <h1 className="text-lg font-bold text-[#241A1D] truncate">
            {report.repo_name}
          </h1>

          {/* Metadata row */}
          <div className="flex flex-wrap items-center gap-3 text-xs text-[#766A6D]">
            <a
              href={fullUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 hover:text-[#3A0714] transition-colors duration-150"
            >
              <GitBranch className="h-3.5 w-3.5" />
              {report.repo_url}
              <ExternalLink className="h-3 w-3" />
            </a>
            <span className="inline-flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              Generated {formatGeneratedAt(report.generated_at)}
            </span>
          </div>
        </div>

        <div className="flex-shrink-0">
          <Button variant="secondary" size="sm" onClick={onNewAnalysis}>
            ← Analyze another repo
          </Button>
        </div>
      </div>
    </div>
  );
}
