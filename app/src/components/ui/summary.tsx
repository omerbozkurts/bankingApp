import { StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Radius, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

/** Label/value rows on a card, for confirming and reporting a transfer. */
export function Summary({ rows }: { rows: [string, string][] }) {
  const theme = useTheme();
  return (
    <View style={[styles.summary, { backgroundColor: theme.backgroundElement }]}>
      {rows.map(([label, value]) => (
        <View key={label} style={styles.row}>
          <ThemedText type="small" themeColor="textSecondary">
            {label}
          </ThemedText>
          <ThemedText type="smallBold" selectable>
            {value}
          </ThemedText>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  summary: {
    borderRadius: Radius.card,
    padding: Spacing.three,
    gap: Spacing.three,
  },
  row: {
    gap: Spacing.half,
  },
});
