/**
 * ProfFinder — API Service
 */

const API_BASE = '/api';

export async function startSearch(formData) {
  const response = await fetch(`${API_BASE}/search`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    throw new Error(`Search failed: ${response.statusText}`);
  }
  return response;
}

export async function draftEmail(request) {
  const response = await fetch(`${API_BASE}/draft-email`, {
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
  const response = await fetch(`${API_BASE}/health`);
  return response.json();
}
