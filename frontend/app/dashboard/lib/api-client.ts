import { API_BASE_URL } from '@/lib/config'
import { toast } from 'sonner'

const MUTATION_REVALIDATION_PREFIXES = [
  '/api/auth/pending-approvals',
  '/api/analytics/dashboard',
  '/api/applications',
  '/api/applications/pending-count',
  '/api/decisions',
  '/api/jobs',
  '/api/notifications',
  '/api/tickets',
] as const

export function revalidateDashboardData() {
  if (typeof window === 'undefined') {
    return
  }

  window.dispatchEvent(
    new CustomEvent('rims:data-mutated', {
      detail: { keys: [...MUTATION_REVALIDATION_PREFIXES] },
    }),
  )
}

export class APIClient {
  private static createRequestId(): string {
    if (typeof window !== 'undefined' && typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
      return crypto.randomUUID()
    }
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`
  }
  private static isPublicEndpoint(endpoint: string): boolean {
    const normalized = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
    return (
      normalized.startsWith('/api/jobs/public') ||
      normalized === '/api/applications/apply' ||
      normalized === '/api/applications/extract-basic-info'
    )
  }

  private static getHeaders(isMultipart = false, endpoint?: string): Record<string, string> {
    const headers: Record<string, string> = {}

    if (!isMultipart) {
      headers['Content-Type'] = 'application/json'
    }

    // Auth model:
    // - Most app endpoints: HttpOnly cookie `access_token` only (no Authorization header).
    // - Interview endpoints: Authorization header with `interview_token` only.
    if (typeof window !== 'undefined' && !(endpoint && this.isPublicEndpoint(endpoint))) {
      const isInterviewRoute = window.location.pathname.startsWith('/interview')
      if (isInterviewRoute) {
        const interviewToken = localStorage.getItem('interview_token')
        if (interviewToken) {
          headers['Authorization'] = `Bearer ${interviewToken}`
        }
      }
    }

    headers['Cache-Control'] = 'no-store'

    return headers
  }

  static async get<T>(endpoint: string): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const response = await fetch(url, {
      method: 'GET',
      headers: this.getHeaders(false, endpoint),
      credentials: 'include',
      cache: 'no-store',
    })

    return this.handleResponse<T>(response)
  }

  /**
   * Use a stable X-Request-ID for logical retries (e.g. same interview question submit)
   * so the backend idempotency guard dedupes network duplicates without blocking legitimate new submits.
   */
  static async postWithRequestId<T>(endpoint: string, data: any, requestId: string): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`
    const headers = this.getHeaders(false, endpoint)
    headers['X-Request-ID'] = requestId
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
      credentials: 'include',
    })
    return this.handleResponse<T>(response)
  }

  static async post<T>(endpoint: string, data: any): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = this.getHeaders(false, endpoint)
    headers['X-Request-ID'] = this.createRequestId()
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
      credentials: 'include',
    })
    return this.handleResponse<T>(response)
  }

  static async postMultipart<T>(endpoint: string, formData: FormData, requestId?: string): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = this.getHeaders(true, endpoint)
    headers['X-Request-ID'] = requestId ?? this.createRequestId()
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
      credentials: 'include',
    })
    return this.handleResponse<T>(response)
  }

  static async handleResponse<T>(response: Response): Promise<T> {
    if (response.status === 204) {
      return {} as T
    }

    if (!response.ok) {
      // Try to get error detail from JSON body
      const errorData = await response.json().catch(() => ({ detail: response.statusText }))
      const detail = errorData.detail || `Error ${response.status}: ${response.statusText}`

      if (typeof window !== 'undefined' && [401, 403, 500].includes(response.status)) {
        toast.error(detail)
      }

      // Handle 401/403: Clear token and redirect
      if ((response.status === 401 || response.status === 403) && typeof window !== 'undefined') {
        const isInterviewPath = window.location.pathname.startsWith('/interview')
        if (isInterviewPath && !window.location.pathname.includes('/access')) {
          // We do NOT redirect automatically to /interview/access anymore to allow the page to show an error
          // and prevent "flash" redirects during load.
          // localStorage.removeItem('auth_token') // Optional: Keep for retry if user manually refreshes
          throw new Error(`${detail}. Please check your credentials and try again.`)
        } else if (response.status === 401) {
          localStorage.removeItem('auth_token')
          window.location.href = '/'
          throw new Error(`Unauthorized: ${detail}. Redirecting...`)
        }
      }

      throw new Error(detail)
    }

    return response.json()
  }

  static async put<T>(endpoint: string, data: any): Promise<T> {
    const headers = this.getHeaders(false, endpoint)
    headers['X-Request-ID'] = this.createRequestId()
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'PUT',
      headers,
      body: JSON.stringify(data),
      credentials: 'include',
    })

    return this.handleResponse<T>(response)
  }

  static async delete(endpoint: string): Promise<void> {
    const headers = this.getHeaders(false, endpoint)
    headers['X-Request-ID'] = this.createRequestId()
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'DELETE',
      headers,
      credentials: 'include',
    })

    await this.handleResponse(response)
  }

  static async postFormData<T>(endpoint: string, formData: FormData): Promise<T> {
    const headers = this.getHeaders(true, endpoint)
    delete headers['Content-Type'] // Let browser set this for FormData
    headers['X-Request-ID'] = this.createRequestId()

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers,
      body: formData,
      credentials: 'include',
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }))
      const detail = error.detail || `API error: ${response.statusText}`
      if (typeof window !== 'undefined' && [401, 403, 500].includes(response.status)) {
        toast.error(detail)
      }
      throw new Error(detail)
    }

    return response.json()
  }
}
