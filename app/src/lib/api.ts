import { API_URL } from './config';
import {
  toAccount,
  toCustomer,
  toMovement,
  toTransferResult,
  type Account,
  type AccountKind,
  type ApiAccount,
  type ApiCustomer,
  type ApiTransaction,
  type ApiTransfer,
  type Customer,
  type MovementPage,
  type Recipient,
  type RecipientTarget,
  type TransferResult,
} from './models';
import {
  toAdminAction,
  toAdminCustomer,
  type AdminActionPage,
  type AdminCustomer,
  type AdminCustomerDetail,
  type AdminCustomerPage,
  type ApiAdminAction,
  type ApiAdminCustomer,
} from './admin';
import type { ChatMessage } from './assistant';
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
  init: {
    method?: string;
    body?: unknown;
    headers?: Record<string, string>;
    timeoutMs?: number;
  } = {},
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
  const timer = setTimeout(() => controller.abort(), init.timeoutMs ?? TIMEOUT_MS);
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

export async function register(input: {
  nationalId: string;
  fullName: string;
  birthDate: string; // ISO YYYY-MM-DD
  password: string;
}): Promise<{ customerNo: string; fullName: string }> {
  const out = await request<{ customer_no: string; full_name: string }>('/auth/register', {
    method: 'POST',
    body: {
      national_id: input.nationalId,
      full_name: input.fullName,
      birth_date: input.birthDate,
      password: input.password,
    },
  });
  return { customerNo: out.customer_no, fullName: out.full_name };
}

export async function openAccount(input: {
  kind: AccountKind;
  name: string;
  goalKurus: number | null;
}): Promise<Account> {
  const account = await request<ApiAccount>('/accounts', {
    method: 'POST',
    body: { kind: input.kind, name: input.name, goal_kurus: input.goalKurus },
  });
  return toAccount(account);
}

function pageParams(beforeId: number | null, limit: number, extra: Record<string, string> = {}) {
  const params = new URLSearchParams({ ...extra, limit: String(limit) });
  if (beforeId !== null) params.set('before_id', String(beforeId));
  return params;
}

async function movementPage(path: string, beforeId: number | null, limit: number) {
  const page = await request<{ items: ApiTransaction[]; next_before_id: number | null }>(
    `${path}?${pageParams(beforeId, limit)}`,
  );
  return { items: page.items.map(toMovement), nextBeforeId: page.next_before_id };
}

export function fetchMovements(
  accountId: number,
  beforeId: number | null = null,
  limit = 20,
): Promise<MovementPage> {
  return movementPage(`/accounts/${accountId}/transactions`, beforeId, limit);
}

function recipientFields(to: RecipientTarget) {
  return 'iban' in to ? { to_iban: to.iban } : { to_customer_no: to.customerNo };
}

export async function lookupRecipient(to: RecipientTarget): Promise<Recipient> {
  const params: Record<string, string> =
    'iban' in to ? { iban: to.iban } : { customer_no: to.customerNo };
  const out = await request<{ iban: string; masked_name: string }>(
    `/recipients/lookup?${new URLSearchParams(params)}`,
  );
  return { iban: out.iban, maskedName: out.masked_name };
}

export async function createTransfer(input: {
  fromAccountId: number;
  to: RecipientTarget;
  amountKurus: number;
  description: string;
  idempotencyKey: string;
}): Promise<TransferResult> {
  const out = await request<ApiTransfer>('/transfers', {
    method: 'POST',
    body: {
      from_account_id: input.fromAccountId,
      ...recipientFields(input.to),
      amount_kurus: input.amountKurus,
      description: input.description,
      idempotency_key: input.idempotencyKey,
    },
  });
  return toTransferResult(out);
}

/** The API keeps no conversation: the whole history goes with every message. */
export async function askAssistant(messages: ChatMessage[]): Promise<string> {
  const out = await request<{ reply: string }>('/assistant/chat', {
    method: 'POST',
    body: { messages },
    // The model may read several accounts before answering.
    timeoutMs: 90_000,
  });
  return out.reply;
}

// Admin panel. Every endpoint answers 403 unless the signed-in customer is an admin.

export async function adminSearchCustomers(
  query: string,
  beforeId: number | null = null,
  limit = 20,
): Promise<AdminCustomerPage> {
  const page = await request<{ items: ApiAdminCustomer[]; next_before_id: number | null }>(
    `/admin/customers?${pageParams(beforeId, limit, { q: query })}`,
  );
  return { items: page.items.map(toAdminCustomer), nextBeforeId: page.next_before_id };
}

export async function adminFetchCustomer(id: number): Promise<AdminCustomerDetail> {
  const out = await request<ApiAdminCustomer & { accounts: ApiAccount[] }>(`/admin/customers/${id}`);
  return { ...toAdminCustomer(out), accounts: out.accounts.map(toAccount) };
}

export function adminFetchMovements(
  accountId: number,
  beforeId: number | null = null,
  limit = 20,
): Promise<MovementPage> {
  return movementPage(`/admin/accounts/${accountId}/transactions`, beforeId, limit);
}

/** Freezes or unfreezes an account; the reason goes into the audit log. */
export async function adminSetFrozen(
  accountId: number,
  frozen: boolean,
  reason: string,
): Promise<Account> {
  const out = await request<ApiAccount>(
    `/admin/accounts/${accountId}/${frozen ? 'freeze' : 'unfreeze'}`,
    { method: 'POST', body: { reason } },
  );
  return toAccount(out);
}

export async function adminUnlockCustomer(id: number, reason: string): Promise<AdminCustomer> {
  const out = await request<ApiAdminCustomer>(`/admin/customers/${id}/unlock`, {
    method: 'POST',
    body: { reason },
  });
  return toAdminCustomer(out);
}

export async function adminFetchActions(
  beforeId: number | null = null,
  limit = 20,
): Promise<AdminActionPage> {
  const page = await request<{ items: ApiAdminAction[]; next_before_id: number | null }>(
    `/admin/actions?${pageParams(beforeId, limit)}`,
  );
  return { items: page.items.map(toAdminAction), nextBeforeId: page.next_before_id };
}
