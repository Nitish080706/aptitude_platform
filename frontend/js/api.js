/**
 * api.js — Fetch wrapper that attaches the Firebase Bearer token.
 * All API calls go through here so auth is handled centrally.
 *
 * CONFIGURATION: Set API_BASE_URL to point to your FastAPI server.
 */

import { RENDER_BACKEND_URL } from './config.js';

export const API_BASE_URL = window.API_BASE_URL || (
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000'
    : RENDER_BACKEND_URL
);

/**
 * Get a fresh Firebase ID token from the current user.
 * auth.js must set window.__getIdToken before this is called.
 */
async function getToken() {
  if (typeof window.__getIdToken === 'function') {
    return await window.__getIdToken();
  }
  return null;
}

/**
 * Core fetch wrapper.
 */
async function apiFetch(path, options = {}) {
  const token = await getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let errMsg = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (Array.isArray(body.detail)) {
        // FastAPI 422 Pydantic errors: [{loc: [...], msg: "...", type: "..."}]
        errMsg = body.detail
          .map(e => `${(e.loc || []).slice(1).join(' → ')}: ${e.msg}`)
          .join('\n');
      } else {
        errMsg = body.detail || body.message || errMsg;
      }
    } catch (_) {}
    throw new Error(errMsg);
  }

  // Handle 204 No Content
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  get:    (path, opts = {}) => apiFetch(path, { method: 'GET', ...opts }),
  post:   (path, body, opts = {}) => apiFetch(path, { method: 'POST',   body: JSON.stringify(body), ...opts }),
  put:    (path, body, opts = {}) => apiFetch(path, { method: 'PUT',    body: JSON.stringify(body), ...opts }),
  patch:  (path, body, opts = {}) => apiFetch(path, { method: 'PATCH',  body: JSON.stringify(body), ...opts }),
  delete: (path, opts = {}) => apiFetch(path, { method: 'DELETE', ...opts }),
};
