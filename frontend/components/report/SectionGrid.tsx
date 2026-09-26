import { OnboardingReport } from "@/types/api";
import { ReportSection } from "./ReportSection";

interface SectionGridProps {
  report: OnboardingReport;
}

export function SectionGrid({ report }: SectionGridProps) {
  return (
    <div className="flex flex-col gap-4">
      {report.sections.map((section) => (
        <ReportSection key={section.title} section={section} />
      ))}
    </div>
  );
}
