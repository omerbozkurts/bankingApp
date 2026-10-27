import { useSyncExternalStore } from 'react';

import * as api from './api';
import type { Customer } from './models';
import { hasPendingLogout, setPendingLogout } from './token-store';

export type SessionState =
  | { status: 'unknown' }
  | { status: 'signedOut' }
  | { status: 'signedIn'; customer: Customer };

let state: SessionState = { status: 'unknown' };
const listeners = new Set<() => void>();

// Bumped by every sign-in and sign-out. A request that started under an older epoch must not
// overwrite the result of a newer action (e.g. a slow refresh finishing after the user signed out).
let epoch = 0;
// The in-flight logout, so a new sign-in waits for it instead of having its session cleared by it.
let logoutInFlight: Promise<void> = Promise.resolve();
let restoreStarted: Promise<void> | null = null;

function set(next: SessionState) {
  state = next;
  listeners.forEach((l) => l());
}

/** Runs once on app start: reuse a stored token (native) or session cookie (web) if still valid. */
export function restoreSession(): Promise<void> {
  restoreStarted ??= restore();
  return restoreStarted;
}

async function restore(): Promise<void> {
  const started = epoch;
  if (hasPendingLogout()) {
    // A previous sign-out couldn't reach the API; finish it rather than resuming that session.
    await finishLogout();
    if (epoch === started) set({ status: 'signedOut' });
    return;
  }
  try {
    const customer = await api.fetchCustomer();
    if (epoch === started) set({ status: 'signedIn', customer });
  } catch {
    if (epoch === started) set({ status: 'signedOut' });
  }
}

/** Throws ApiError with a user-facing message if the login fails. */
export async function signIn(customerNo: string, password: string): Promise<void> {
  const started = ++epoch;
  await logoutInFlight;
  try {
    await api.login(customerNo, password);
  } catch (error) {
    if (epoch === started) set({ status: 'signedOut' });
    throw error;
  }
  try {
    const customer = await api.fetchCustomer();
    if (epoch === started) set({ status: 'signedIn', customer });
  } catch (error) {
    // Logged in but couldn't load the profile: don't leave a half-open session behind.
    if (epoch === started) await signOut();
    throw error;
  }
}

/** Reloads profile and balances. An expired session signs the user out. */
export async function refreshCustomer(): Promise<void> {
  const started = epoch;
  try {
    const customer = await api.fetchCustomer();
    if (epoch === started) set({ status: 'signedIn', customer });
  } catch (error) {
    if (epoch !== started) return;
    if (error instanceof api.ApiError && error.status === 401) await signOut();
    else throw error;
  }
}

export function signOut(): Promise<void> {
  epoch++;
  // Local state is cleared first; a failed network call must not keep the user signed in.
  set({ status: 'signedOut' });
  logoutInFlight = finishLogout();
  return logoutInFlight;
}

async function finishLogout(): Promise<void> {
  try {
    await api.logout();
    setPendingLogout(false);
  } catch {
    setPendingLogout(true);
  }
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useSession(): SessionState {
  return useSyncExternalStore(
    subscribe,
    () => state,
    () => state,
  );
}
