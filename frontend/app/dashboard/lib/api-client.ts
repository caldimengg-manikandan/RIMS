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
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'GET',
      headers: this.getHeaders()
    })

    return this.handleResponse<T>(response)
  }

  static async post<T>(endpoint: string, data: any): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(data),
    })
    return this.handleResponse<T>(response)
  }

  static async postMultipart<T>(endpoint: string, formData: FormData): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
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
      // Handle 401: Clear token and redirect to login
      if (response.status === 401 && typeof window !== 'undefined') {
        localStorage.removeItem('auth_token')
        window.location.href = '/'
      }

      const error = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(error.detail || `API error: ${response.statusText}`)
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
