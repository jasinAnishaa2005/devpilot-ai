import { SectionTitle } from "@/types/api";

export const SECTION_TITLES: SectionTitle[] = [
  "Project Overview",
  "Architecture",
  "Important Files",
  "Setup Instructions",
  "Dependencies",
  "Potential Risks",
  "Recommended First Tasks",
];

export interface SectionMeta {
  title: SectionTitle;
  icon: string;       // lucide-react icon name
  accentClass: string; // Tailwind bg+text classes for the section badge/header
  borderClass: string; // Tailwind left-border class for the card
  id: string;         // anchor id for jump navigation
}

export const SECTION_META: Record<SectionTitle, SectionMeta> = {
  "Project Overview": {
    title: "Project Overview",
    icon: "BookOpen",
    accentClass: "bg-blue-50 text-blue-700",
    borderClass: "border-l-blue-500",
    id: "section-project-overview",
  },
  Architecture: {
    title: "Architecture",
    icon: "Layers",
    accentClass: "bg-indigo-50 text-indigo-700",
    borderClass: "border-l-indigo-500",
    id: "section-architecture",
  },
  "Important Files": {
    title: "Important Files",
    icon: "FileCode",
    accentClass: "bg-cyan-50 text-cyan-700",
    borderClass: "border-l-cyan-500",
    id: "section-important-files",
  },
  "Setup Instructions": {
    title: "Setup Instructions",
    icon: "Terminal",
    accentClass: "bg-green-50 text-green-700",
    borderClass: "border-l-green-500",
    id: "section-setup-instructions",
  },
  Dependencies: {
    title: "Dependencies",
    icon: "Package",
    accentClass: "bg-amber-50 text-amber-700",
    borderClass: "border-l-amber-500",
    id: "section-dependencies",
  },
  "Potential Risks": {
    title: "Potential Risks",
    icon: "AlertTriangle",
    accentClass: "bg-red-50 text-red-700",
    borderClass: "border-l-red-500",
    id: "section-potential-risks",
  },
  "Recommended First Tasks": {
    title: "Recommended First Tasks",
    icon: "CheckSquare",
    accentClass: "bg-emerald-50 text-emerald-700",
    borderClass: "border-l-emerald-500",
    id: "section-recommended-first-tasks",
  },
};
