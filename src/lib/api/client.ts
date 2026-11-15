import type { ApiError } from "./types";

/**
 * Thin, typed HTTP client for the FastAPI backend.
 *
 * - Base URL comes from `NEXT_PUBLIC_API_URL` (see `.env.local.example`).
 * - All functions return typed promises and throw normalized `ApiError`s.
 * - The consumer (`useObservatoryData`) falls back to mock data on failure.
 */

export const API_BASE_URL: string =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

export const REQUEST_TIMEOUT_MS = 4000;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...init?.headers,
      },
      signal: controller.signal,
    });
  } catch (cause) {
    const message = cause instanceof Error ? cause.message : String(cause);
    throw {
      message: `Cannot reach backend (${API_BASE_URL}): ${message}`,
      cause,
    } satisfies ApiError;
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) {
    throw {
      status: response.status,
      message: `Backend returned error: ${response.status} ${response.statusText}`,
    } satisfies ApiError;
  }

  return (await response.json()) as T;
}

export const apiClient = {
  get<T>(path: string): Promise<T> {
    return request<T>(path);
  },

  post<T>(path: string, body: unknown): Promise<T> {
    return request<T>(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  },
};
