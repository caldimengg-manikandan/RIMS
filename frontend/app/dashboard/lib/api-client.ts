import { API_BASE_URL } from '@/lib/config'

export class APIClient {
  private static getToken(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('auth_token')
    }
    return null
  }

  private static getHeaders(isMultipart = false): Record<string, string> {
    const token = this.getToken()
    const headers: Record<string, string> = {}

    if (!isMultipart) {
      headers['Content-Type'] = 'application/json'
    }

    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    return headers
  }

  static async get<T>(endpoint: string): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    console.log(`[APIClient] GET ${url}`);
    const response = await fetch(url, {
      method: 'GET',
      headers: this.getHeaders()
    })

    return this.handleResponse<T>(response)
  }

  static async post<T>(endpoint: string, data: any): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    console.log(`[APIClient] POST ${url}`);
    const response = await fetch(url, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(data),
    })
    return this.handleResponse<T>(response)
  }

  static async postMultipart<T>(endpoint: string, formData: FormData): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    console.log(`[APIClient] POST (Multipart) ${url}`);
    const response = await fetch(url, {
      method: 'POST',
      headers: this.getHeaders(true),
      body: formData,
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

      // Handle 401/403: Clear token and redirect
      if ((response.status === 401 || response.status === 403) && typeof window !== 'undefined') {
        const isInterviewPath = window.location.pathname.startsWith('/interview')
        if (isInterviewPath && !window.location.pathname.includes('/access')) {
          localStorage.removeItem('auth_token')
          // Optional: we can delay redirect or let the caller handle it, 
          // but keeping current auto-redirect logic with better message
          setTimeout(() => { window.location.href = '/interview/access' }, 3000)
          throw new Error(`${detail} (Redirecting in 3s...)`)
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
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'PUT',
      headers: this.getHeaders(),
      body: JSON.stringify(data)
    })

    return this.handleResponse<T>(response)
  }

  static async delete(endpoint: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'DELETE',
      headers: this.getHeaders()
    })

    await this.handleResponse(response)
  }

  static async postFormData<T>(endpoint: string, formData: FormData): Promise<T> {
    const headers = this.getHeaders(true)
    delete headers['Content-Type'] // Let browser set this for FormData

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers,
      body: formData
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(error.detail || `API error: ${response.statusText}`)
    }

    return response.json()
  }
}
