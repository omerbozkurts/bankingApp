// Web: the session is an httpOnly cookie set by the API, so JavaScript never holds the token
// (nothing in localStorage for an injected script to steal). Token functions are no-ops.

/** Web clients rely on the cookie instead of a Bearer header. */
export const usesBearerToken = false;

export async function getToken(): Promise<string | null> {
  return null;
}

export async function setToken(_token: string): Promise<void> {}

export async function clearToken(): Promise<void> {}

// JavaScript can't delete an httpOnly cookie; only the API can. If the logout request fails
// (e.g. offline), remember it so the next app start finishes the logout instead of silently
// restoring the session. This flag is not a secret, so localStorage is fine.
const PENDING_LOGOUT_KEY = 'abbank.pendingLogout';

export function hasPendingLogout(): boolean {
  try {
    return localStorage.getItem(PENDING_LOGOUT_KEY) === '1';
  } catch {
    return false;
  }
}

export function setPendingLogout(pending: boolean): void {
  try {
    if (pending) localStorage.setItem(PENDING_LOGOUT_KEY, '1');
    else localStorage.removeItem(PENDING_LOGOUT_KEY);
  } catch {
    // Storage blocked (private mode etc.): nothing more we can do client-side.
  }
}
