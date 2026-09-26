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
    <div className="border-b border-gray-200 bg-white px-6 py-5">
      <div className="max-w-7xl mx-auto flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex flex-col gap-1.5 min-w-0">
          {/* Breadcrumb */}
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span className="font-medium text-blue-600">DevPilot</span>
            <span>/</span>
            <span>Onboarding Report</span>
          </div>

          {/* Repo name */}
          <h1 className="text-xl font-bold text-gray-900 truncate">
            {report.repo_name}
          </h1>

          {/* Metadata row */}
          <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500">
            <a
              href={fullUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 hover:text-blue-600 transition-colors"
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
