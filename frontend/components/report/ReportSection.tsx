import {
  BookOpen,
  Layers,
  FileCode,
  Terminal,
  Package,
  AlertTriangle,
  CheckSquare,
  LucideIcon,
} from "lucide-react";
import { ReportSection as ReportSectionType } from "@/types/api";
import { SECTION_META } from "@/constants/sections";
import { MarkdownContent } from "./MarkdownContent";
import { SectionTitle } from "@/types/api";

const ICON_MAP: Record<string, LucideIcon> = {
  BookOpen,
  Layers,
  FileCode,
  Terminal,
  Package,
  AlertTriangle,
  CheckSquare,
};

interface ReportSectionProps {
  section: ReportSectionType;
}

export function ReportSection({ section }: ReportSectionProps) {
  const meta = SECTION_META[section.title as SectionTitle];
  const Icon = meta ? (ICON_MAP[meta.icon] ?? BookOpen) : BookOpen;
  const accentClass = meta?.accentClass ?? "bg-gray-50 text-gray-700";
  const borderClass = meta?.borderClass ?? "border-l-gray-300";
  const anchorId = meta?.id ?? section.title.toLowerCase().replace(/\s+/g, "-");

  return (
    <section
      id={anchorId}
      className={[
        "rounded-xl border border-gray-200 bg-white border-l-4 overflow-hidden",
        borderClass,
      ].join(" ")}
      aria-labelledby={`${anchorId}-title`}
    >
      {/* Section header */}
      <div className={["flex items-center gap-3 px-5 py-4 border-b border-gray-100", accentClass].join(" ")}>
        <Icon className="h-5 w-5 flex-shrink-0" />
        <h2 id={`${anchorId}-title`} className="text-sm font-semibold">
          {section.title}
        </h2>
      </div>

      {/* Markdown content */}
      <div className="px-5 py-4">
        <MarkdownContent content={section.content} />
      </div>
    </section>
  );
}
