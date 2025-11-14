const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

type ApiClientOptions = RequestInit & { method?: HttpMethod };

export async function apiClient<TResponse>(path: string, options: ApiClientOptions = {}): Promise<TResponse> {
  const headers = new Headers(options.headers);
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json');
  }

  const token = typeof window !== 'undefined' ? sessionStorage.getItem('access_token') : null;
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const detail = await safeParseError(response);
    throw new Error(detail ?? `HTTP ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as TResponse;
  }

  return (await response.json()) as TResponse;
}

async function safeParseError(response: Response): Promise<string | null> {
  try {
    const data = await response.json();
    return data?.detail ?? data?.message ?? null;
  } catch (error) {
    console.error('Failed to parse error response', error);
    return null;
  }
}
