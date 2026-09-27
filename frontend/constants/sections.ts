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
    accentClass: "bg-[#F7F2EF] text-[#3A0714]",
    borderClass: "border-l-[#3A0714]",
    id: "section-project-overview",
  },
  Architecture: {
    title: "Architecture",
    icon: "Layers",
    accentClass: "bg-[#F7F2EF] text-[#520B1B]",
    borderClass: "border-l-[#520B1B]",
    id: "section-architecture",
  },
  "Important Files": {
    title: "Important Files",
    icon: "FileCode",
    accentClass: "bg-[#F7F2EF] text-[#7A1830]",
    borderClass: "border-l-[#7A1830]",
    id: "section-important-files",
  },
  "Setup Instructions": {
    title: "Setup Instructions",
    icon: "Terminal",
    accentClass: "bg-[#F7F2EF] text-[#3A0714]",
    borderClass: "border-l-[#3A0714]",
    id: "section-setup-instructions",
  },
  Dependencies: {
    title: "Dependencies",
    icon: "Package",
    accentClass: "bg-[#F7F2EF] text-[#7A1830]",
    borderClass: "border-l-[#7A1830]",
    id: "section-dependencies",
  },
  "Potential Risks": {
    title: "Potential Risks",
    icon: "AlertTriangle",
    accentClass: "bg-[#B85C6E]/10 text-[#3A0714]",
    borderClass: "border-l-[#B85C6E]",
    id: "section-potential-risks",
  },
  "Recommended First Tasks": {
    title: "Recommended First Tasks",
    icon: "CheckSquare",
    accentClass: "bg-[#F7F2EF] text-[#3A0714]",
    borderClass: "border-l-[#3A0714]",
    id: "section-recommended-first-tasks",
  },
};
