import { ButtonHTMLAttributes, forwardRef } from "react";

type Variant = "primary" | "secondary" | "ghost";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

const variantClasses: Record<Variant, string> = {
  primary:
    "bg-[#3A0714] text-white hover:bg-[#520B1B] active:bg-[#2A0710] disabled:bg-[#7A1830]/50 disabled:text-white/60 focus:ring-[#B85C6E]",
  secondary:
    "bg-white text-[#241A1D] border border-[#E2DEDC] hover:bg-[#F7F2EF] hover:border-[#B85C6E]/40 active:bg-[#ECE9E7] disabled:opacity-50 focus:ring-[#B85C6E]",
  ghost:
    "text-[#766A6D] hover:text-[#241A1D] hover:bg-[#F7F2EF] active:bg-[#ECE9E7] disabled:opacity-40 focus:ring-[#B85C6E]",
};

const sizeClasses: Record<Size, string> = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-sm",
  lg: "px-6 py-3 text-base",
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      loading = false,
      disabled,
      children,
      className = "",
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={[
          "inline-flex items-center justify-center gap-2 rounded-md font-medium",
          "transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2",
          "cursor-pointer disabled:cursor-not-allowed",
          variantClasses[variant],
          sizeClasses[size],
          className,
        ].join(" ")}
        {...props}
      >
        {loading && (
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
        )}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
export { Button };
