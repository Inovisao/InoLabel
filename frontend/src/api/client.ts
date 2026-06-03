const BASE = "/api";

async function request<T>(
  method: string,
  path: string,
  body?: unknown
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json() as Promise<T>;
}

export const api = {
  get:    <T>(path: string)                  => request<T>("GET",    path),
  post:   <T>(path: string, body?: unknown)  => request<T>("POST",   path, body),
  delete: <T>(path: string)                  => request<T>("DELETE", path),
};
