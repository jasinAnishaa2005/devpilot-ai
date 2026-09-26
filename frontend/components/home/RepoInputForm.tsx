"use client";

import { useState, FormEvent, KeyboardEvent } from "react";
import { ChevronDown, ChevronUp, Search } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { AnalysisState } from "@/types/api";

interface RepoInputFormProps {
  state: AnalysisState;
  onSubmit: (url: string, branch?: string) => Promise<void>;
  onReset: () => void;
}

export function RepoInputForm({ state, onSubmit, onReset }: RepoInputFormProps) {
  const [url, setUrl] = useState("");
  const [branch, setBranch] = useState("");
  const [showBranch, setShowBranch] = useState(false);

  const isLoading = state.status === "loading";
  const error = state.status === "error" ? state.message : null;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    onSubmit(url, branch || undefined);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      onSubmit(url, branch || undefined);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="w-full max-w-2xl mx-auto"
      noValidate
    >
      <div className="rounded-2xl border border-[#B85C6E]/20 bg-white shadow-[0_4px_32px_rgba(58,7,20,0.18)] p-6 flex flex-col gap-4">
        {/* GitHub icon header */}
        <div className="flex items-center gap-2 mb-1">
          <svg className="h-5 w-5 text-[#3A0714]" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
          </svg>
          <span className="text-xs font-semibold text-[#3A0714] tracking-wide uppercase">GitHub Repository</span>
        </div>

        <Input
          id="repo-url"
          label="Repository URL"
          type="url"
          placeholder="https://github.com/owner/repository"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          autoFocus
          autoComplete="off"
          spellCheck={false}
        />

        {/* Optional branch toggle */}
        <div>
          <button
            type="button"
            onClick={() => setShowBranch((v) => !v)}
            className="inline-flex items-center gap-1 text-xs text-[#766A6D] hover:text-[#3A0714] transition-colors duration-150"
          >
            {showBranch ? (
              <ChevronUp className="h-3.5 w-3.5" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5" />
            )}
            {showBranch ? "Hide branch options" : "Specify a branch (optional)"}
          </button>

          {showBranch && (
            <div className="mt-3">
              <Input
                id="branch"
                label="Branch"
                type="text"
                placeholder="main (auto-detected when empty)"
                value={branch}
                onChange={(e) => setBranch(e.target.value)}
                disabled={isLoading}
                hint="Leave empty to use the repository's default branch."
                autoComplete="off"
                spellCheck={false}
              />
            </div>
          )}
        </div>

        {error && (
          <ErrorBanner message={error} onDismiss={onReset} />
        )}

        <Button
          type="submit"
          size="lg"
          loading={isLoading}
          disabled={isLoading || !url.trim()}
          className="w-full"
        >
          <Search className="h-4 w-4" />
          {isLoading ? "Analyzing…" : "Analyze Repository"}
        </Button>
      </div>

      <p className="mt-3 text-center text-xs text-[#F7F2EF]/50">
        Works with any public GitHub repository. Analysis may take up to 20
        seconds for large repos.
      </p>
    </form>
  );
}
