/**
 * Resolves the backend API base URL.
 * In dev (Vite port 5173 / CRA port 3000) we talk directly to localhost:8000.
 * In production the frontend is served from the same origin as the API.
 */
export const API_BASE =
  window.location.port === '5173' || window.location.port === '3000'
    ? 'http://localhost:8000'
    : '';

export async function authFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const token = localStorage.getItem('recovr_token');
  const headers = new Headers(init.headers || {});
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  if (!headers.has('Content-Type') && init.body && typeof init.body === 'string') {
    headers.set('Content-Type', 'application/json');
  }
  const fullUrl = input.startsWith('http') ? input : `${API_BASE}${input}`;
  return fetch(fullUrl, { ...init, headers });
}
