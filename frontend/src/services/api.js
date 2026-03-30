/**
 * API Configuration
 * In development: Vite proxy handles /api → localhost:8000
 * In production: Uses the VITE_API_URL environment variable (your Render URL)
 */
export const API_BASE = import.meta.env.VITE_API_URL || '';

export function apiUrl(path) {
  return `${API_BASE}${path}`;
}

export async function startSearch(formData) {
  const response = await fetch(apiUrl('/api/search'), {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    throw new Error(`Search failed: ${response.statusText}`);
  }
  return response;
}

export async function draftEmail(request) {
  const response = await fetch(apiUrl('/api/draft-email'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`Email draft failed: ${response.statusText}`);
  }
  return response.json();
}

export async function healthCheck() {
  const response = await fetch(apiUrl('/api/health'));
  return response.json();
}
