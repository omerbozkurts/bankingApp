import { useSyncExternalStore } from 'react';
import { useColorScheme as useRNColorScheme } from 'react-native';

const noopSubscribe = () => () => {};

/**
 * Static rendering has no colour scheme, so render 'light' on the server and on the first
 * client pass, then switch to the real scheme once hydrated.
 */
export function useColorScheme() {
  const hydrated = useSyncExternalStore(
    noopSubscribe,
    () => true,
    () => false,
  );
  const colorScheme = useRNColorScheme();

  return hydrated ? colorScheme : 'light';
}
