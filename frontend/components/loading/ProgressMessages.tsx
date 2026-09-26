"use client";

import { useEffect, useState } from "react";

const MESSAGES = [
  "Fetching repository tree…",
  "Detecting languages and frameworks…",
  "Reading dependency files…",
  "Identifying entry points and API routes…",
  "Scanning key source files…",
  "Generating onboarding report…",
  "Almost there…",
];

const INTERVAL_MS = 3000;

export function ProgressMessages() {
  const [index, setIndex] = useState(0);
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const interval = setInterval(() => {
      setVisible(false);
      setTimeout(() => {
        setIndex((i) => Math.min(i + 1, MESSAGES.length - 1));
        setVisible(true);
      }, 300);
    }, INTERVAL_MS);

    return () => clearInterval(interval);
  }, []);

  return (
    <p
      className={[
        "text-sm text-[#F7F2EF]/55 transition-opacity duration-300",
        visible ? "opacity-100" : "opacity-0",
      ].join(" ")}
    >
      {MESSAGES[index]}
    </p>
  );
}
