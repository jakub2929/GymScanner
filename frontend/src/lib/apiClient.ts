// Get API URL - must be set via NEXT_PUBLIC_API_URL environment variable
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Warn if API_URL seems incorrect or not set
if (typeof window !== 'undefined') {
  if (!process.env.NEXT_PUBLIC_API_URL) {
    console.error(
      '❌ NEXT_PUBLIC_API_URL is not set! API calls will fail.',
      'Current API_URL:', API_URL,
      'Set NEXT_PUBLIC_API_URL to your public API URL in Coolify and rebuild the frontend.'
    );
  } else if (API_URL.includes('localhost') && window.location.hostname !== 'localhost') {
    console.warn(
      '⚠️ NEXT_PUBLIC_API_URL is set to localhost but app is running on',
      window.location.hostname,
      '- API calls may fail. Set NEXT_PUBLIC_API_URL to your public API URL.'
    );
  } else {
    console.log('✅ API URL configured:', API_URL);
  }
}

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

  const url = `${API_URL}${path}`;
  // Always log API calls in production to help debug
  if (typeof window !== 'undefined') {
    console.log(`[API Client] ${options.method || 'GET'} ${url}`);
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });
  
  // Log response for debugging
  if (typeof window !== 'undefined' && !response.ok) {
    console.error(`[API Client] ${response.status} ${response.statusText} for ${options.method || 'GET'} ${url}`);
  }

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
