import { API_URL } from './config';
import { toCustomer, type ApiAccount, type ApiCustomer, type Customer } from './models';
import { clearToken, getToken, setToken, usesBearerToken } from './token-store';

const TIMEOUT_MS = 15_000;

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

const NETWORK_ERROR = 'Sunucuya bağlanılamadı. İnternet bağlantınızı kontrol edip tekrar deneyin.';

async function request<T>(
  path: string,
  init: { method?: string; body?: unknown; headers?: Record<string, string> } = {},
): Promise<T> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
    // Required by the API for cookie-authenticated (web) requests; harmless with a Bearer token.
    'X-Requested-With': 'abbank',
    ...init.headers,
  };
  if (init.body !== undefined) headers['Content-Type'] = 'application/json';
  if (usesBearerToken) {
    const token = await getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  // The timeout covers the whole exchange, including reading the body.
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    let response: Response;
    let data: unknown = null;
    try {
      response = await fetch(`${API_URL}${path}`, {
        method: init.method ?? 'GET',
        headers,
        body: init.body === undefined ? undefined : JSON.stringify(init.body),
        // Web: send and accept the session cookie across the app/API ports.
        credentials: 'include',
        signal: controller.signal,
      });
      if (response.status !== 204) data = await response.json().catch(() => null);
    } catch {
      throw new ApiError(0, NETWORK_ERROR);
    }

    if (!response.ok) {
      // FastAPI puts a message in `detail`; validation errors (422) carry a list instead.
      const detail = (data as { detail?: unknown } | null)?.detail;
      throw new ApiError(
        response.status,
        typeof detail === 'string' ? detail : 'Beklenmeyen bir hata oluştu.',
      );
    }
    return data as T;
  } finally {
    clearTimeout(timer);
  }
}

export async function login(customerNo: string, password: string): Promise<void> {
  const body = await request<{ access_token?: string }>('/auth/login', {
    method: 'POST',
    body: { customer_no: customerNo, password },
    // Web asks for the httpOnly cookie, so the token never appears in this response.
    headers: usesBearerToken ? undefined : { 'X-Session-Mode': 'cookie' },
  });
  if (body.access_token) await setToken(body.access_token);
}

/** Native: deletes the stored token. Web: asks the API to clear the cookie (can fail offline). */
export async function logout(): Promise<void> {
  if (usesBearerToken) {
    await clearToken();
    return;
  }
  await request<void>('/auth/logout', { method: 'POST' });
}

export async function fetchCustomer(): Promise<Customer> {
  const [me, accounts] = await Promise.all([
    request<ApiCustomer>('/me'),
    request<ApiAccount[]>('/accounts'),
  ]);
  return toCustomer(me, accounts);
}
