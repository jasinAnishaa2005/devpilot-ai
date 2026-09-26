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
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm p-6 flex flex-col gap-4">
        <Input
          id="repo-url"
          label="GitHub Repository URL"
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
            className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 transition-colors"
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

      <p className="mt-3 text-center text-xs text-gray-400">
        Works with any public GitHub repository. Analysis may take up to 20
        seconds for large repos.
      </p>
    </form>
  );
}
