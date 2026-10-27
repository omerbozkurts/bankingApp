import { useSyncExternalStore } from 'react';

import type { Customer } from './demo-account';

// In-memory session for the demo. It resets on reload; the backend task will replace it with
// token storage (expo-secure-store on native, httpOnly cookie on web).
let current: Customer | null = null;
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((l) => l());
}

export function signIn(customer: Customer) {
  current = customer;
  emit();
}

export function signOut() {
  current = null;
  emit();
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useSession(): Customer | null {
  return useSyncExternalStore(
    subscribe,
    () => current,
    () => null,
  );
}
