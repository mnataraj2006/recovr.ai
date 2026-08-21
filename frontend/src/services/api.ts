/**
 * Resolves the backend API base URL.
 * In dev (Vite port 5173 / CRA port 3000) we talk directly to localhost:8000.
 * In production the frontend is served from the same origin as the API.
 */
export const API_BASE =
  window.location.port === '5173' || window.location.port === '3000'
    ? 'http://localhost:8000'
    : '';
