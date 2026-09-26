import { InputHTMLAttributes, forwardRef } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, hint, id, className = "", ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label
            htmlFor={id}
            className="text-sm font-medium text-[#241A1D]"
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={id}
          className={[
            "w-full rounded-md border px-3 py-2.5 text-sm text-[#241A1D]",
            "placeholder:text-[#766A6D]",
            "transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[#B85C6E]/40 focus:border-[#7A1830]",
            error
              ? "border-[#B85C6E] bg-[#F7F2EF] focus:ring-[#B85C6E]/40"
              : "border-[#E2DEDC] bg-white hover:border-[#B85C6E]/50",
            className,
          ].join(" ")}
          {...props}
        />
        {error && (
          <p className="text-xs text-[#B85C6E]">{error}</p>
        )}
        {hint && !error && (
          <p className="text-xs text-[#766A6D]">{hint}</p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";
export { Input };
