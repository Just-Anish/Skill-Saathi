/**
 * Lightweight, type-safe API client for SkillSaathi
 * Designed for clean transition from local mocks to real backend services
 */

export class ApiError extends Error {
  public status: number;
  public details?: unknown;

  constructor(status: number, message: string, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
    Object.setPrototypeOf(this, ApiError.prototype);
  }
}

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  params?: Record<string, string | number | boolean | undefined>;
  body?: unknown;
}

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    // Default to /api which proxies to FastAPI backend (http://127.0.0.1:8000)
    this.baseUrl = baseUrl ?? (import.meta.env.VITE_API_BASE_URL || '/api');
  }

  private buildUrl(
    endpoint: string,
    params?: Record<string, string | number | boolean | undefined>,
  ): string {
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const base = this.baseUrl.replace(/\/+$/, '');
    const urlString = base ? `${base}${cleanEndpoint}` : cleanEndpoint;

    // Use current origin if base is relative
    const url = new URL(urlString, typeof window !== 'undefined' ? window.location.origin : 'http://localhost');

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value));
        }
      });
    }

    return url.toString();
  }

  async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { params, headers, body, method = 'GET', ...restOptions } = options;
    const url = this.buildUrl(endpoint, params);

    const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;

    const requestHeaders: Record<string, string> = {
      Accept: 'application/json',
      ...(!isFormData && body ? { 'Content-Type': 'application/json' } : {}),
      ...(headers as Record<string, string>),
    };

    const config: RequestInit = {
      ...restOptions,
      method,
      headers: requestHeaders,
      body: body ? (isFormData ? (body as FormData) : JSON.stringify(body)) : undefined,
    };

    try {
      const response = await fetch(url, config);

      let responseData: unknown;
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        responseData = await response.json();
      } else {
        responseData = await response.text();
      }

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;

        if (
          typeof responseData === 'object' &&
          responseData !== null &&
          'message' in responseData &&
          typeof (responseData as { message: unknown }).message === 'string'
        ) {
          errorMessage = (responseData as { message: string }).message;
        }

        throw new ApiError(response.status, errorMessage, responseData);
      }

      return responseData as T;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }

      const message = error instanceof Error ? error.message : 'Unknown network request error';
      throw new ApiError(0, message);
    }
  }

  get<T>(endpoint: string, options?: Omit<RequestOptions, 'method' | 'body'>): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'GET' });
  }

  post<T>(endpoint: string, body?: unknown, options?: Omit<RequestOptions, 'method' | 'body'>): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'POST', body });
  }

  put<T>(endpoint: string, body?: unknown, options?: Omit<RequestOptions, 'method' | 'body'>): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'PUT', body });
  }

  patch<T>(endpoint: string, body?: unknown, options?: Omit<RequestOptions, 'method' | 'body'>): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'PATCH', body });
  }

  delete<T>(endpoint: string, options?: Omit<RequestOptions, 'method' | 'body'>): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' });
  }
}

export const apiClient = new ApiClient();
