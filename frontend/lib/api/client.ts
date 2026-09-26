/**
 * Core fetch wrapper for the DevPilot AI backend.
 * Base URL is read from NEXT_PUBLIC_API_URL at build/runtime.
 * Never hardcode localhost in application logic.
 */

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ??
  "http://127.0.0.1:8000";

export class ApiClientError extends Error {
  constructor(
    message: string,
    public readonly status: number
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
    ...options,
  });

  if (!res.ok) {
    let detail = `Request failed with status ${res.status}`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string" && body.detail) {
        detail = body.detail;
      }
    } catch {
      // ignore JSON parse errors — use the default message
    }
    throw new ApiClientError(detail, res.status);
  }

  return res.json() as Promise<T>;
}
