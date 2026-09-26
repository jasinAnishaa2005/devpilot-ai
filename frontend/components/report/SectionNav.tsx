"use client";

import { useEffect, useState } from "react";
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
import { SectionTitle } from "@/types/api";
import { SECTION_META } from "@/constants/sections";

const ICON_MAP: Record<string, LucideIcon> = {
  BookOpen,
  Layers,
  FileCode,
  Terminal,
  Package,
  AlertTriangle,
  CheckSquare,
};

interface SectionNavProps {
  titles: SectionTitle[];
}

export function SectionNav({ titles }: SectionNavProps) {
  const [activeId, setActiveId] = useState<string>("");

  useEffect(() => {
    const ids = titles.map((t) => SECTION_META[t].id);

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
            break;
          }
        }
      },
      { rootMargin: "-20% 0px -70% 0px", threshold: 0 }
    );

    ids.forEach((id) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [titles]);

  return (
    <nav aria-label="Report sections">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-400 px-2">
        Sections
      </p>
      <ul className="flex flex-col gap-0.5">
        {titles.map((title) => {
          const meta = SECTION_META[title];
          const Icon = ICON_MAP[meta.icon] ?? BookOpen;
          const isActive = activeId === meta.id;
          return (
            <li key={title}>
              <a
                href={`#${meta.id}`}
                className={[
                  "flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors",
                  isActive
                    ? "bg-blue-50 text-blue-700 font-medium"
                    : "text-gray-600 hover:bg-gray-100 hover:text-gray-900",
                ].join(" ")}
              >
                <Icon className="h-4 w-4 flex-shrink-0" />
                <span className="truncate">{title}</span>
              </a>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
