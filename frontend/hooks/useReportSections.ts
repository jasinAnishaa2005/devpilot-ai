import { useMemo } from "react";
import { SectionTitle } from "@/types/api";
import { SECTION_META, SectionMeta } from "@/constants/sections";

/**
 * Returns display metadata (icon, colors, anchor id) for a given section title.
 */
export function useReportSections(
  titles: SectionTitle[]
): SectionMeta[] {
  return useMemo(
    () => titles.map((t) => SECTION_META[t]).filter(Boolean),
    [titles]
  );
}
