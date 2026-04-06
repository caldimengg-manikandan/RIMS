import { APIClient } from './api-client'

export const fetcher = <T>(url: string): Promise<T> => APIClient.get<T>(url)
