import { useAuth } from '../context/AuthContext'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api'

export function useApiClient() {
  const { accessToken, refreshToken, login, logout } = useAuth()

  async function refreshAccessToken(): Promise<string | null> {
    if (!refreshToken) return null
    try {
      const response = await fetch(`${API_BASE}/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: refreshToken }),
      })
      if (!response.ok) return null
      const data = await response.json()
      login(data.access, refreshToken)
      return data.access
    } catch {
      return null
    }
  }

  async function apiFetch(path: string, options: RequestInit = {}) {
    async function doFetch(token: string | null) {
      return fetch(`${API_BASE}${path}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...options.headers,
        },
      })
    }

    let response = await doFetch(accessToken)

    if (response.status === 401) {
      const newAccessToken = await refreshAccessToken()
      if (newAccessToken) {
        response = await doFetch(newAccessToken)
      } else {
        logout()
      }
    }

    return response
  }

  return apiFetch
}