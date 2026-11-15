"use client";

import { useEffect, useState } from "react";

export function errorMessage(error: unknown) {
  return error && typeof error === "object" && "message" in error ? String(error.message) : String(error);
}

export function useScienceRequest<T>(request: ((signal: AbortSignal) => Promise<T>) | null, revision = 0) {
  const [result, setResult] = useState<{ request: typeof request; revision: number; data: T | null; error: string | null }>({
    request: null, revision: 0, data: null, error: null,
  });
  useEffect(() => {
    if (!request) return;
    const controller = new AbortController();
    void request(controller.signal).then(
      (data) => { if (!controller.signal.aborted) setResult({ request, revision, data, error: null }); },
      (error) => { if (!controller.signal.aborted) setResult({ request, revision, data: null, error: errorMessage(error) }); },
    );
    return () => controller.abort();
  }, [request, revision]);
  if (!request) return { data: null, error: null, loading: false };
  return result.request === request && result.revision === revision
    ? { ...result, loading: false } : { data: null, error: null, loading: true };
}
