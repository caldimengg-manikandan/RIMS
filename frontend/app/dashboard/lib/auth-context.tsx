'use client'

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { API_BASE_URL } from '@/lib/config'

export interface User {
  id: number
  email: string
  full_name: string
  role: 'candidate' | 'hr'
  is_active: boolean
  created_at: string
}

interface AuthContextType {
  user: User | null
  token: string | null
  isLoading: boolean
  isAuthenticated: boolean
  register: (email: string, password: string, full_name: string) => Promise<void>
  verify: (email: string, otp: string) => Promise<void>
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Load token from localStorage on mount
  useEffect(() => {
    const savedToken = localStorage.getItem('auth_token')
    if (savedToken) {
      setToken(savedToken)
      // Verify token by fetching current user
      fetchCurrentUser(savedToken)
    } else {
      setIsLoading(false)
    }
  }, [])

  console.log("Current API_BASE_URL:", API_BASE_URL)


  const fetchCurrentUser = useCallback(async (authToken: string) => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 8000);

      const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        signal: controller.signal
      })

      clearTimeout(timeoutId);

      if (response.ok) {
        const userData = await response.json()
        setUser(userData)
        setToken(authToken)
      } else if (response.status === 401) {
        // Explicitly unauthorized - token is dead
        console.warn('Session expired (401). Redirecting to login.')
        localStorage.removeItem('auth_token')
        setToken(null)
        setUser(null)
        window.location.href = '/'
      } else {
        // Other server error (500, 502, 503, 504) - Keep token, don't logout
        console.error(`Server error (${response.status}) fetching user info. Retaining session.`)
      }
    } catch (error) {
      // Network error (fetch failed) - DO NOT logout. User might be offline or server transiently down.
      console.error('Network error fetching user info. Retaining session:', error)
    } finally {
      setIsLoading(false)
    }
  }, [API_BASE_URL])

  const register = useCallback(async (email: string, password: string, full_name: string) => {
    setIsLoading(true)
    try {
      console.log("[v0] Registering user:", { email, full_name })

      const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, full_name }),
        credentials: 'include'
      })

      console.log("[v0] Register response status:", response.status)

      if (!response.ok) {
        let errorMessage = 'Registration failed'
        try {
          const error = await response.json()
          errorMessage = error.detail || error.message || errorMessage
        } catch (e) {
          errorMessage = `Server error (${response.status}): ${response.statusText}`
        }
        throw new Error(errorMessage)
      }

      const userData = await response.json()
      console.log("[v0] User registered successfully, awaiting OTP verification:", userData)
      // Do not set user or token yet because they need to verify their email
    } catch (error) {
      // Don't log expected registration errors (email exists, etc.) to console
      if (error instanceof TypeError && error.message.includes('fetch')) {
        console.error("[v0] Registration error:", error)
        throw new Error(`Unable to connect to backend server at ${API_BASE_URL}. Please ensure the FastAPI server is running.`)
      }
      throw error
    } finally {
      setIsLoading(false)
    }
  }, [])

  const verify = useCallback(async (email: string, otp: string) => {
    setIsLoading(true)
    try {
      console.log("[v0] Verifying OTP for:", email)
      const response = await fetch(`${API_BASE_URL}/api/auth/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, otp }),
      })

      if (!response.ok) {
        let errorMessage = 'Verification failed'
        try {
          const error = await response.json()
          errorMessage = error.detail || error.message || errorMessage
        } catch (e) {
          errorMessage = `Server error (${response.status}): ${response.statusText}`
        }
        throw new Error(errorMessage)
      }

      console.log("[v0] OTP verified successfully")
    } catch (error) {
      console.error("[v0] Verify error:", error)
      throw error
    } finally {
      setIsLoading(false)
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    setIsLoading(true)
    try {
      if (!API_BASE_URL || API_BASE_URL === 'undefined') {
        throw new Error("API_BASE_URL is not defined. Please check your environment configuration.");
      }

      console.log("[v0] Logging in user:", { email, password: '***' })

      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
        credentials: 'include'
      })

      console.log("[v0] Login response status:", response.status)

      if (!response.ok) {
        let errorMessage = 'Login failed'
        try {
          const error = await response.json()
          errorMessage = error.detail || error.message || errorMessage
        } catch (e) {
          errorMessage = `Server error (${response.status}): ${response.statusText}`
        }
        console.warn(`Login fetch failed: ${errorMessage}`);
        throw new Error(errorMessage)
      }

      let data;
      try {
        data = await response.json()
        console.log("[v0] Login success. Data received.");
      } catch (e) {
        throw new Error("Failed to parse login response from the server.");
      }

      const authToken = data.access_token

      if (!authToken) {
        throw new Error("No access token provided by the server.");
      }

      // Save token and fetch user
      localStorage.setItem('auth_token', authToken)
      setToken(authToken)

      // Fetch user info
      await fetchCurrentUser(authToken)
    } catch (error) {
      console.error("Login fetch failed:", error);

      // Don't log expected authentication errors to console (wrong password, etc.)
      // as they're handled by the UI and would trigger Next.js error overlay
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error(`Unable to connect to backend server at ${API_BASE_URL}. Please ensure the FastAPI server is running.`)
      }
      throw error
    } finally {
      setIsLoading(false)
    }
  }, [fetchCurrentUser, API_BASE_URL])

  const logout = useCallback(() => {
    setUser(null)
    setToken(null)
    localStorage.removeItem('auth_token')
  }, [])

  const refreshUser = useCallback(async () => {
    if (token) {
      await fetchCurrentUser(token)
    }
  }, [token, fetchCurrentUser])

  const value: AuthContextType = {
    user,
    token,
    isLoading,
    isAuthenticated: !!user && !!token,
    register,
    verify,
    login,
    logout,
    refreshUser
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
