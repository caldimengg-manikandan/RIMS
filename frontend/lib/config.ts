/**
 * Client-side configuration for the Automated Recruitment System
 */

// Centralized API Base URL with fallback to Render's default port (10000)
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:10000';

// Safeguard: warn in production if API base URL is missing (fallback remains localhost).
if (typeof window !== 'undefined') {
  const isProd = process.env.NODE_ENV === 'production'
  if (isProd && !process.env.NEXT_PUBLIC_API_BASE_URL) {
    // eslint-disable-next-line no-console
    console.warn('[config] NEXT_PUBLIC_API_BASE_URL is not set in production; falling back to localhost')
  }
}

// Other global constants can go here
export const APP_NAME = 'Automated Recruitment System';
