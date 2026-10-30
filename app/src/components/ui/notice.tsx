import type { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';

import { Radius, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

/** Callout with a coloured left edge: `error` for failures, `info` for neutral hints. */
export function Notice({ tone, children }: { tone: 'error' | 'info'; children: ReactNode }) {
  const theme = useTheme();
  return (
    <View
      accessibilityLiveRegion={tone === 'error' ? 'polite' : undefined}
      style={[
        styles.notice,
        {
          backgroundColor: theme.backgroundElement,
          borderLeftColor: tone === 'error' ? theme.danger : theme.accent,
        },
      ]}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  notice: {
    borderRadius: Radius.card,
    borderLeftWidth: 4,
    padding: Spacing.three,
    gap: Spacing.one,
  },
});
