const TOKEN_KEY = 'perseus_access_token'
const REFRESH_TOKEN_KEY = 'perseus_refresh_token'

export class ApiClient {
  private baseUrl: string
  private refreshPromise: Promise<boolean> | null = null

  constructor(baseUrl: string = '/api/v1') {
    this.baseUrl = baseUrl.replace(/\/+$/, '')
  }

  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY)
  }

  setTokens(access: string, refresh: string): void {
    localStorage.setItem(TOKEN_KEY, access)
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh)
  }

  clearTokens(): void {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
    options?: { skipAuth?: boolean }
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }

    if (!options?.skipAuth) {
      const token = this.getToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
    }

    const res = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    })

    if (res.status === 401 && !options?.skipAuth) {
      const refreshed = await this.tryRefresh()
      if (refreshed) {
        return this.request<T>(method, path, body, options)
      }
      this.clearTokens()
      window.location.href = '/auth'
      throw new Error('Session expired')
    }

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }))
      throw new ApiClientError(res.status, error.detail || 'Request failed', error)
       }

    if (res.status === 204) {
      return undefined as T
    }

    return res.json()
  }

  private async tryRefresh(): Promise<boolean> {
    if (this.refreshPromise) {
      return this.refreshPromise
    }

    this.refreshPromise = this.doRefresh()
    try {
      return await this.refreshPromise
    } finally {
      this.refreshPromise = null
    }
  }

  private async doRefresh(): Promise<boolean> {
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
    if (!refreshToken) return false

    try {
      const res = await fetch(`${this.baseUrl}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })

      if (!res.ok) return false

      const data = await res.json()
      this.setTokens(data.access_token, data.refresh_token)
      return true
    } catch {
      return false
    }
  }

  get<T>(path: string, skipAuth?: boolean): Promise<T> {
    return this.request<T>('GET', path, undefined, { skipAuth })
  }

  post<T>(path: string, body?: unknown, skipAuth?: boolean): Promise<T> {
    return this.request<T>('POST', path, body, { skipAuth })
  }

  put<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>('PUT', path, body)
  }

  patch<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>('PATCH', path, body)
  }

  delete<T>(path: string): Promise<T> {
    return this.request<T>('DELETE', path)
  }
}

export class ApiClientError extends Error {
  constructor(
    public status: number,
    message: string,
    public data?: unknown
  ) {
    super(message)
    this.name = 'ApiClientError'
  }
}

export const api = new ApiClient(import.meta.env.VITE_API_BASE_URL || '/api/v1')
