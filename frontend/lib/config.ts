/**
 * Client-side configuration for the Automated Recruitment System
 */

// Centralized API Base URL with fallback to Render's default port (10000)
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:10000';

// Other global constants can go here
export const APP_NAME = 'Automated Recruitment System';
