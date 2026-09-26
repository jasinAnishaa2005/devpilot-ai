import { HTMLAttributes } from "react";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  label: string;
}

export function Badge({ label, className = "", ...props }: BadgeProps) {
  return (
    <span
      className={[
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        className,
      ].join(" ")}
      {...props}
    >
      {label}
    </span>
  );
}
