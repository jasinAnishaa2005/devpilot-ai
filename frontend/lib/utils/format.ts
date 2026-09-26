/**
 * Formatting utilities for display values.
 */

/**
 * Converts a backend repo_url ("owner/repo") into a full GitHub URL.
 * The backend always returns the short form — we reconstruct the full URL here.
 */
export function repoUrlToFullUrl(repoUrl: string): string {
  // If it already looks like a full URL, return as-is
  if (repoUrl.startsWith("http")) return repoUrl;
  return `https://github.com/${repoUrl}`;
}

/**
 * Formats an ISO-8601 UTC string into a human-readable local date/time.
 * e.g. "2026-09-25T17:51:19.207432+00:00" → "Sep 25, 2026, 5:51 PM"
 */
export function formatGeneratedAt(isoString: string): string {
  try {
    return new Date(isoString).toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return isoString;
  }
}
