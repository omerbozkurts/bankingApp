import * as SecureStore from 'expo-secure-store';

// Native: the access token lives in the iOS Keychain / Android Keystore via expo-secure-store.
const KEY = 'abbank.accessToken';

/** Native clients send the token as a Bearer header and never use cookies. */
export const usesBearerToken = true;

export function getToken(): Promise<string | null> {
  return SecureStore.getItemAsync(KEY);
}

export function setToken(token: string): Promise<void> {
  return SecureStore.setItemAsync(KEY, token);
}

export function clearToken(): Promise<void> {
  return SecureStore.deleteItemAsync(KEY);
}

// Signing out on native only deletes the local token, which can't fail on the network,
// so there is never a server-side logout left to finish.
export function hasPendingLogout(): boolean {
  return false;
}

export function setPendingLogout(_pending: boolean): void {}
