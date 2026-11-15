import type { ApiError } from "./types";

/**
 * Thin, typed HTTP client for the FastAPI backend.
 *
 * - Base URL comes from `NEXT_PUBLIC_API_URL` (see `.env.local.example`).
 * - All functions return typed promises and throw normalized `ApiError`s.
 * - The consumer (`useObservatoryData`) falls back to mock data on failure.
 */

export const API_BASE_URL = "/science";

export const REQUEST_TIMEOUT_MS = 4000;

interface RequestOptions {
  timeout?: number;
  signal?: AbortSignal;
}

async function request<T>(path: string, init?: RequestInit, options: RequestOptions = {}): Promise<T> {
  const controller = new AbortController();
  const abort = () => controller.abort();
  options.signal?.addEventListener("abort", abort, { once: true });
  if (options.signal?.aborted) abort();
  const timer = setTimeout(abort, options.timeout ?? REQUEST_TIMEOUT_MS);

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
    options.signal?.removeEventListener("abort", abort);
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { error?: { code?: string; message?: string } } | null;
    throw {
      status: response.status,
      code: payload?.error?.code,
      message: payload?.error?.message ?? `Backend returned error: ${response.status} ${response.statusText}`,
    } satisfies ApiError;
  }

  try {
    return (await response.json()) as T;
  } catch (cause) {
    throw { status: 502, message: "The backend returned an unreadable response.", cause } satisfies ApiError;
  }
}

export const apiClient = {
  get<T>(path: string, options?: RequestOptions): Promise<T> {
    return request<T>(path, undefined, options);
  },

  post<T>(path: string, body: unknown, options?: RequestOptions): Promise<T> {
    return request<T>(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }, options);
  },
};
