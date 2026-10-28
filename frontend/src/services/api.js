/**
 * The only file that talks to the backend. Every API call is listed here,
 * so the base URL and the error handling are in one place.
 *
 * VITE_API_BASE_URL is read at build time (see .env.example at the
 * frontend root). Defaults to the local FastAPI dev server.
 */
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message)
    this.status = status
    this.detail = detail
  }
}

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: options.body instanceof FormData ? undefined : { 'Content-Type': 'application/json' },
    ...options,
  })

  if (!res.ok) {
    let detail = null
    try {
      detail = (await res.json()).detail
    } catch {
      /* response wasn't JSON */
    }
    throw new ApiError(detail || `Request failed (${res.status})`, res.status, detail)
  }

  const contentType = res.headers.get('content-type') || ''
  if (contentType.includes('application/json')) return res.json()
  return res.blob()
}

function qs(params = {}) {
  const usp = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    if (Array.isArray(value)) {
      value.forEach((v) => usp.append(key, v))
    } else {
      usp.append(key, value)
    }
  })
  const str = usp.toString()
  return str ? `?${str}` : ''
}

export const api = {
  // ---- Cities ----
  listCities: () => request('/cities'),
  getCitySummary: (cityId) => request(`/cities/${cityId}/summary`),

  // ---- Problems ----
  listProblems: (params) => request(`/problems${qs(params)}`),
  getProblem: (id) => request(`/problems/${id}`),
  updateProblemStatus: (id, status) =>
    request(`/problems/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status }) }),

  // ---- Map ----
  getMapProblems: (params) => request(`/map/problems${qs(params)}`),

  // ---- Report Problem ----
  analyzeImage: (file) => {
    const form = new FormData()
    form.append('file', file)
    return request('/analyze/image', { method: 'POST', body: form })
  },
  verifyDetection: (detectionId, payload) =>
    request(`/detections/${detectionId}/verify`, { method: 'POST', body: JSON.stringify(payload) }),
  // A region the user drew on the photo themselves (box values are fractions from 0 to 1).
  createUserRegion: (payload) => request('/detections/user-region', { method: 'POST', body: JSON.stringify(payload) }),
  createManualProblem: (payload) => request('/problems/manual', { method: 'POST', body: JSON.stringify(payload) }),

  // ---- Priority List ----
  getPriorities: (cityId, limit = 20, unresolvedOnly = true) =>
    request(`/priorities${qs({ city_id: cityId, limit, unresolved_only: unresolvedOnly })}`),

  // ---- Other ----
  uploadsUrl: (path) => `${BASE_URL.replace(/\/api\/v1$/, '')}${path}`,
  getMlStatus: () => request('/ml/status'),
}
