/**
 * API Configuration
 * In development: Vite proxy handles /api → localhost:8000
 * In production: Uses the VITE_API_URL environment variable (your Render URL)
 */
export const API_BASE = import.meta.env.VITE_API_URL || '';

export function apiUrl(path) {
  return `${API_BASE}${path}`;
}
