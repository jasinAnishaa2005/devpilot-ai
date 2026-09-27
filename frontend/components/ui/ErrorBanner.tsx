import { AlertCircle, X } from "lucide-react";

interface ErrorBannerProps {
  message: string;
  onDismiss?: () => void;
}

export function ErrorBanner({ message, onDismiss }: ErrorBannerProps) {
  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-lg border border-[#B85C6E]/40 bg-[#B85C6E]/10 px-4 py-3 text-sm text-[#3A0714]"
    >
      <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-[#B85C6E]" />
      <p className="flex-1 leading-relaxed">{message}</p>
      {onDismiss && (
        <button
          onClick={onDismiss}
          aria-label="Dismiss error"
          className="ml-2 flex-shrink-0 text-[#B85C6E]/70 hover:text-[#B85C6E] transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
