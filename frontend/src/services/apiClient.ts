const BASE_URL = '/api/v1';

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
    credentials: 'include',
  });

  if (response.status === 401) {
    sessionStorage.removeItem('token');
    localStorage.removeItem('user');
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
  }

  if (response.status === 204) {
    return {} as T;
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const errorMsg = data?.error?.message || data?.detail || `HTTP Error ${response.status}`;
    throw new ApiError(errorMsg, response.status, data);
  }

  return data as T;
}

export const apiClient = {
  get: <T>(endpoint: string) => request<T>(endpoint, { method: 'GET' }),
  post: <T>(endpoint: string, body?: any) =>
    request<T>(endpoint, { method: 'POST', body: JSON.stringify(body) }),
  put: <T>(endpoint: string, body?: any) =>
    request<T>(endpoint, { method: 'PUT', body: JSON.stringify(body) }),
  delete: <T>(endpoint: string) => request<T>(endpoint, { method: 'DELETE' }),
  download: async (endpoint: string): Promise<Blob> => {
    const response = await fetch(`${BASE_URL}${endpoint}`, {
      method: 'GET',
      credentials: 'include',
    });
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      const errorMsg = errData?.error?.message || errData?.detail || `HTTP Error ${response.status}`;
      throw new ApiError(errorMsg, response.status, errData);
    }
    return response.blob();
  },

  // Cloudflare Status API
  fetchCloudflareStatus: () => request<{ status: string; data: any }>('/cloudflare/status'),
  syncCloudflareStatus: () => request<{ status: string; message: string; data: any }>('/cloudflare/sync', { method: 'POST' }),
};

