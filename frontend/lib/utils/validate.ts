/**
 * Client-side validation helpers.
 * These mirror the backend's AnalyzeRequest validation but run before the request
 * so the user gets instant feedback without a round-trip.
 */

/**
 * Returns true if the string looks like a valid GitHub repository URL.
 * Accepts:
 *   https://github.com/owner/repo
 *   https://github.com/owner/repo.git
 *   github.com/owner/repo
 */
export function isGitHubUrl(value: string): boolean {
  return /(?:^|[./])github\.com\/[^/\s]+\/[^/\s]+/.test(value.trim());
}

/**
 * Validates the repository form inputs.
 * Returns a human-readable error string, or null if valid.
 */
export function validateRepoForm(url: string): string | null {
  if (!url.trim()) {
    return "Repository URL is required.";
  }
  if (!isGitHubUrl(url)) {
    return "Must be a valid GitHub URL, e.g. https://github.com/owner/repo";
  }
  return null; // valid
}
