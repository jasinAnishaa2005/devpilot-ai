"use client";

import { useEffect, useState } from "react";
import { ProgressMessages } from "./ProgressMessages";

// Indeterminate progress: fills to ~90% over ~18s then stalls
const FILL_DURATION_MS = 18000;
const MAX_FILL = 90;

export function AnalysisProgress() {
  const [width, setWidth] = useState(0);

  useEffect(() => {
    const start = Date.now();
    const tick = () => {
      const elapsed = Date.now() - start;
      const progress = Math.min((elapsed / FILL_DURATION_MS) * MAX_FILL, MAX_FILL);
      setWidth(progress);
      if (progress < MAX_FILL) {
        requestAnimationFrame(tick);
      }
    };
    const raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center min-h-[320px] gap-6 w-full max-w-md mx-auto text-center">
      {/* Animated icon */}
      <div className="relative">
        <div className="h-16 w-16 rounded-2xl bg-blue-50 flex items-center justify-center">
          <svg
            className="h-8 w-8 text-blue-600 animate-pulse"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5"
            />
          </svg>
        </div>
        {/* Orbit ring */}
        <div className="absolute inset-0 h-16 w-16 rounded-full border-2 border-blue-200 animate-spin [animation-duration:3s]" />
      </div>

      <div className="flex flex-col gap-1">
        <p className="text-base font-semibold text-gray-800">
          Analyzing repository…
        </p>
        <ProgressMessages />
      </div>

      {/* Progress bar */}
      <div className="w-full h-1.5 rounded-full bg-gray-100 overflow-hidden">
        <div
          className="h-full rounded-full bg-blue-500 transition-[width] duration-500 ease-linear"
          style={{ width: `${width}%` }}
        />
      </div>

      <p className="text-xs text-gray-400">
        This may take up to 20 seconds for large repositories.
      </p>
    </div>
  );
}
